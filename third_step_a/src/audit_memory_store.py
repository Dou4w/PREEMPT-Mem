from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import Any


def _canonicalize(value: Any) -> Any:
    """Convert supported Python values into a deterministic JSON value.

    JSON-native values retain their historical encoding.  Dataclasses are
    encoded as ordinary field mappings, tuples as arrays, and sets as tagged,
    canonically sorted arrays.  The tagged set representation avoids treating
    a set and a list with the same members as the same logical value.
    """

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonicalize(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            invalid = sorted(type(key).__name__ for key in value if not isinstance(key, str))
            raise TypeError(
                "canonical_json requires string mapping keys; got " + ", ".join(invalid)
            )
        if "__canonical_type__" in value:
            raise ValueError("__canonical_type__ is reserved for canonical type tags")
        return {key: _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonicalize(item) for item in value]
        items.sort(
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        return {
            "__canonical_type__": "frozenset" if isinstance(value, frozenset) else "set",
            "items": items,
        }
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical_json value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9_./$~-]+", text.lower()))


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) >= 3}


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    memory_type: str
    content: str
    provenance: dict[str, Any]
    aliases: tuple[str, ...]
    retrieval_keys: tuple[str, ...]
    metadata: dict[str, Any]

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def record_sha256(self) -> str:
        return sha256_json(asdict(self))


@dataclass(frozen=True)
class MemoryScopedValue:
    """A derived surface value with explicit memory dependency provenance."""

    depends_on_memory_ids: tuple[str, ...]
    value: Any

    def __post_init__(self) -> None:
        if any(not isinstance(memory_id, str) for memory_id in self.depends_on_memory_ids):
            raise TypeError("depends_on_memory_ids must contain only strings")
        normalized = tuple(sorted(set(self.depends_on_memory_ids)))
        if not normalized or any(not memory_id for memory_id in normalized):
            raise ValueError("depends_on_memory_ids must contain non-empty memory IDs")
        object.__setattr__(self, "depends_on_memory_ids", normalized)


class AgentMemoryView:
    """Narrow capability passed to the agent; the controller vault is unreachable."""

    def __init__(self, store: "AuditMemoryStore") -> None:
        self.__retrieve = store.retrieve

    def retrieve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.__retrieve(query=query, limit=limit, cache_result=True)


class AuditMemoryStore:
    """Small external store with explicit, auditable deletion surfaces.

    The full restore payload is held in a controller-only vault. The agent is
    only given AgentMemoryView, which exposes retrieval and nothing else.
    """

    SURFACE_NAMES = (
        "canonical_memory_record",
        "alias_and_near_duplicate_copies",
        "embedding_ann_keyword_graph_indexes",
        "reranker_derived_features",
        "retrieval_tool_summary_caches",
        "active_prompt_scratchpad_session_kv_context",
        "runtime_variables",
        "derived_summary_rule_skill_plan_edge_tag_cached_answer",
        "agent_accessible_archive_logs_debug_endpoints",
    )

    def __init__(self) -> None:
        self.canonical_records: dict[str, MemoryRecord] = {}
        self.alias_to_memory_id: dict[str, str] = {}
        self.near_duplicate_copies: dict[str, dict[str, Any]] = {}
        self.keyword_index: dict[str, set[str]] = {}
        self.ann_index: dict[str, set[str]] = {}
        self.graph_index: dict[str, set[str]] = {}
        self.reranker_features: dict[str, dict[str, Any]] = {}
        self.retrieval_cache: dict[str, list[str]] = {}
        self.tool_cache: dict[str, Any] = {}
        self.summary_cache: dict[str, str] = {}
        self.active_prompt: list[str] = []
        self.scratchpad: list[str] = []
        self.session_context: dict[str, Any] = {}
        self.kv_context: dict[str, Any] = {}
        self.runtime_variables: dict[str, Any] = {}
        self.derived_artifacts: dict[str, dict[str, Any]] = {
            name: {}
            for name in (
                "summary",
                "rule",
                "skill",
                "plan",
                "edge",
                "tag",
                "cached_answer",
            )
        }
        self.agent_accessible_archives: dict[str, Any] = {}
        self.agent_accessible_logs: dict[str, Any] = {}
        self.debug_endpoints: dict[str, Any] = {}
        self.__controller_restore_vault: dict[str, MemoryRecord] = {}
        # Retrieval cache entries need dependency provenance so deletion can
        # invalidate only queries whose candidate set depended on the target.
        # This index lives beside the controller-only restore vault and is not
        # part of the AgentMemoryView or any agent-visible surface payload.
        self.__controller_retrieval_cache_dependencies: dict[str, set[str]] = {}
        self.public_audit_records: dict[str, dict[str, str]] = {}

    def agent_view(self) -> AgentMemoryView:
        return AgentMemoryView(self)

    @staticmethod
    def scoped_value(value: Any, *memory_ids: str) -> MemoryScopedValue:
        """Wrap derived state with explicit dependency provenance.

        Callers that populate tool/context/runtime/archive surfaces should use
        this helper.  It makes target-scoped invalidation exact even when the
        derived value itself no longer contains a literal memory identifier.
        """

        return MemoryScopedValue(tuple(memory_ids), copy.deepcopy(value))

    @staticmethod
    def _mapping_declares_dependency(value: dict[str, Any], memory_id: str) -> bool:
        dependency_fields = (
            "depends_on_memory_ids",
            "memory_ids",
            "memory_id",
            "source_memory_id",
            "target_memory_id",
            "parent_memory_id",
        )
        for field_name in dependency_fields:
            if field_name not in value:
                continue
            field_value = value[field_name]
            if isinstance(field_value, str) and field_value == memory_id:
                return True
            if isinstance(field_value, (list, tuple, set, frozenset)) and memory_id in field_value:
                return True
        return False

    @staticmethod
    def _mapping_has_dependency_declaration(value: dict[str, Any]) -> bool:
        return any(
            field_name in value
            for field_name in (
                "depends_on_memory_ids",
                "memory_ids",
                "memory_id",
                "source_memory_id",
                "target_memory_id",
                "parent_memory_id",
            )
        )

    @staticmethod
    def _recursive_string_values(value: Any, path: str = "") -> list[tuple[str, str]]:
        """Collect stable paths and non-empty strings from structured metadata."""

        values: list[tuple[str, str]] = []
        if isinstance(value, str):
            if value.strip():
                values.append((path or "$", value))
            return values
        if isinstance(value, dict):
            for key in sorted(value):
                child_path = f"{path}.{key}" if path else str(key)
                values.extend(
                    AuditMemoryStore._recursive_string_values(value[key], child_path)
                )
            return values
        if isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]" if path else f"[{index}]"
                values.extend(
                    AuditMemoryStore._recursive_string_values(item, child_path)
                )
            return values
        if isinstance(value, (set, frozenset)):
            for index, item in enumerate(sorted(value, key=canonical_json)):
                child_path = f"{path}{{{index}}}" if path else f"{{{index}}}"
                values.extend(
                    AuditMemoryStore._recursive_string_values(item, child_path)
                )
        return values

    @classmethod
    def _scalar_depends_on_record(
        cls,
        value: Any,
        record: MemoryRecord,
        target_unique_needles: list[dict[str, str]] | None = None,
    ) -> bool:
        if not isinstance(value, str):
            return False
        lowered = value.lower()
        normalized = normalize_text(value)
        substring_kinds = {
            "memory_id",
            "exact_content",
            "content_sha256",
            "record_sha256",
            "provenance",
            "leakage_sentinel",
            "metadata_summary",
            "graph_edge",
        }
        needles = (
            cls.forbidden_needles(record)
            if target_unique_needles is None
            else target_unique_needles
        )
        for needle in needles:
            needle_value = needle["value"]
            if needle["kind"] == "derived_content_fragment_8gram":
                if normalize_text(needle_value) in normalized:
                    return True
            elif (
                needle["kind"] in substring_kinds
                or needle["kind"].startswith("metadata_scalar::")
                or needle["kind"].startswith("provenance_scalar::")
            ):
                if needle_value.lower() in lowered:
                    return True
            elif lowered == needle_value.lower():
                return True
        return False

    @classmethod
    def _prune_record_dependency(
        cls,
        value: Any,
        record: MemoryRecord,
        target_unique_needles: list[dict[str, str]] | None = None,
        *,
        legacy_fallback: bool = True,
    ) -> tuple[Any, bool]:
        """Return ``(pruned_value, remove_entire_value)`` for one target.

        Container shape and all unrelated members are preserved.  Explicit
        MemoryScopedValue provenance takes precedence; frozen exact/derived
        needles are a conservative fallback for legacy unscoped values.
        """

        if isinstance(value, MemoryScopedValue):
            if record.memory_id in value.depends_on_memory_ids:
                return None, True
            # Explicit provenance is authoritative.  A distractor payload may
            # legitimately share words/content with the target and must remain.
            return value, False

        if isinstance(value, MemoryRecord):
            return (None, True) if value.memory_id == record.memory_id else (value, False)

        if is_dataclass(value) and not isinstance(value, type):
            return (
                (None, True)
                if legacy_fallback and cls._scalar_depends_on_record(
                    canonical_json(value), record, target_unique_needles
                )
                else (value, False)
            )

        if isinstance(value, dict):
            if cls._mapping_declares_dependency(value, record.memory_id):
                return None, True
            # A non-target declaration owns ordinary scalar payloads, but is
            # not an atomic escape hatch: nested containers may introduce a
            # new target dependency declaration and must still be traversed.
            child_legacy_fallback = (
                legacy_fallback
                and not cls._mapping_has_dependency_declaration(value)
            )
            changed = False
            result: dict[str, Any] = {}
            for key, item in value.items():
                if key == record.memory_id or (
                    child_legacy_fallback
                    and cls._scalar_depends_on_record(
                        key, record, target_unique_needles
                    )
                ):
                    changed = True
                    continue
                pruned, remove = cls._prune_record_dependency(
                    item,
                    record,
                    target_unique_needles,
                    legacy_fallback=child_legacy_fallback,
                )
                if remove:
                    changed = True
                    continue
                result[key] = pruned
                changed = changed or pruned is not item
            return (result if changed else value), False

        if isinstance(value, list):
            result_list: list[Any] = []
            changed = False
            for item in value:
                pruned, remove = cls._prune_record_dependency(
                    item,
                    record,
                    target_unique_needles,
                    legacy_fallback=legacy_fallback,
                )
                if remove:
                    changed = True
                    continue
                result_list.append(pruned)
                changed = changed or pruned is not item
            return (result_list if changed else value), False

        if isinstance(value, tuple):
            result_items: list[Any] = []
            changed = False
            for item in value:
                pruned, remove = cls._prune_record_dependency(
                    item,
                    record,
                    target_unique_needles,
                    legacy_fallback=legacy_fallback,
                )
                if remove:
                    changed = True
                    continue
                result_items.append(pruned)
                changed = changed or pruned is not item
            return (tuple(result_items) if changed else value), False

        if isinstance(value, (set, frozenset)):
            result_set: set[Any] = set()
            changed = False
            for item in value:
                pruned, remove = cls._prune_record_dependency(
                    item,
                    record,
                    target_unique_needles,
                    legacy_fallback=legacy_fallback,
                )
                if remove:
                    changed = True
                    continue
                result_set.add(pruned)
                changed = changed or pruned is not item
            if not changed:
                return value, False
            return (frozenset(result_set) if isinstance(value, frozenset) else result_set), False

        if legacy_fallback and cls._scalar_depends_on_record(
            value, record, target_unique_needles
        ):
            return None, True
        return value, False

    @classmethod
    def _prune_surface(
        cls,
        value: Any,
        record: MemoryRecord,
        target_unique_needles: list[dict[str, str]] | None = None,
    ) -> Any:
        pruned, remove = cls._prune_record_dependency(
            value, record, target_unique_needles
        )
        if not remove:
            return pruned
        if isinstance(value, dict):
            return {}
        if isinstance(value, list):
            return []
        if isinstance(value, tuple):
            return ()
        if isinstance(value, set):
            return set()
        if isinstance(value, frozenset):
            return frozenset()
        return None

    def _rank_query(self, query: str) -> tuple[list[str], set[str]]:
        scores: dict[str, int] = {}
        for token in tokenize(normalize_text(query)):
            for memory_id in self.keyword_index.get(token, set()):
                scores[memory_id] = scores.get(memory_id, 0) + 1
        ranked = [
            memory_id
            for memory_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        ]
        return ranked, set(scores)

    def _invalidate_retrieval_cache_for_delete(
        self,
        record: MemoryRecord,
        target_unique_needles: list[dict[str, str]] | None = None,
    ) -> None:
        """Remove only the target candidate from caches that depended on it.

        The controller dependency index is authoritative.  A shared query is
        retained with its distractor candidates; a target-only query is
        removed entirely so no target-derived query string remains reachable.
        """

        if target_unique_needles is None:
            target_unique_needles, _ = self.partition_forbidden_needles(record)
        for query, memory_ids in list(self.retrieval_cache.items()):
            dependencies = set(
                self.__controller_retrieval_cache_dependencies.get(query, set())
            )
            if record.memory_id not in dependencies and record.memory_id not in memory_ids:
                continue
            # A query string can itself be target-derived even when its cached
            # candidates also include a distractor through shared terms.  Such
            # a joint cache must disappear as a unit; retaining only the
            # distractor ID would leave the target's unique query/key reachable.
            _, query_matches = self.scan_payload_for_needles(
                query, target_unique_needles
            )
            if query_matches:
                self.retrieval_cache.pop(query, None)
                self.__controller_retrieval_cache_dependencies.pop(query, None)
                continue
            remaining_ids = [
                candidate for candidate in memory_ids if candidate != record.memory_id
            ]
            remaining_dependencies = dependencies - {record.memory_id}
            if remaining_ids or remaining_dependencies:
                self.retrieval_cache[query] = remaining_ids
                self.__controller_retrieval_cache_dependencies[query] = (
                    remaining_dependencies or set(remaining_ids)
                )
            else:
                self.retrieval_cache.pop(query, None)
                self.__controller_retrieval_cache_dependencies.pop(query, None)

    def _refresh_retrieval_cache_for_put(self, record: MemoryRecord) -> None:
        """Refresh pre-existing queries whose candidates can change on put/restore."""

        record_tokens = tokenize(" ".join(record.retrieval_keys) + " " + record.content)
        for query in list(self.retrieval_cache):
            dependencies = self.__controller_retrieval_cache_dependencies.get(query, set())
            if (
                record.memory_id not in dependencies
                and not (tokenize(query) & record_tokens)
            ):
                continue
            ranked, refreshed_dependencies = self._rank_query(query)
            self.retrieval_cache[query] = ranked
            self.__controller_retrieval_cache_dependencies[query] = refreshed_dependencies

    def put(self, record: MemoryRecord) -> dict[str, str]:
        if not record.memory_id or record.memory_id in self.canonical_records:
            raise ValueError("memory_id must be non-empty and unique")
        if not record.provenance:
            raise ValueError("provenance is required")
        duplicate_aliases = [
            alias for alias in record.aliases if alias in self.alias_to_memory_id
        ]
        if duplicate_aliases:
            raise ValueError(f"duplicate alias: {duplicate_aliases[0]}")
        self.canonical_records[record.memory_id] = copy.deepcopy(record)
        for alias in record.aliases:
            self.alias_to_memory_id[alias] = record.memory_id
        for token in tokenize(" ".join(record.retrieval_keys) + " " + record.content):
            self.keyword_index.setdefault(token, set()).add(record.memory_id)
        self.ann_index.setdefault(record.content_sha256, set()).add(record.memory_id)
        self.graph_index[record.memory_id] = set(record.metadata.get("graph_edges", []))
        self.reranker_features[record.memory_id] = {
            "retrieval_key_count": len(record.retrieval_keys),
            "content_length": len(record.content),
        }
        self.summary_cache[record.memory_id] = record.metadata.get("summary", "")
        self.derived_artifacts["tag"][record.memory_id] = list(record.retrieval_keys)
        self._refresh_retrieval_cache_for_put(record)
        return {"memory_id": record.memory_id, "record_sha256": record.record_sha256}

    def retrieve(
        self, query: str, limit: int = 5, *, cache_result: bool = True
    ) -> list[dict[str, Any]]:
        normalized_query = normalize_text(query)
        if normalized_query in self.retrieval_cache:
            memory_ids = self.retrieval_cache[normalized_query][:limit]
        else:
            memory_ids, dependency_ids = self._rank_query(normalized_query)
            query_tokens = tokenize(normalized_query)
            for memory_id, record in self.__controller_restore_vault.items():
                record_tokens = tokenize(
                    " ".join(record.retrieval_keys) + " " + record.content
                )
                if query_tokens & record_tokens:
                    dependency_ids.add(memory_id)
            if cache_result:
                self.retrieval_cache[normalized_query] = list(memory_ids)
                self.__controller_retrieval_cache_dependencies[normalized_query] = dependency_ids
        return [
            asdict(copy.deepcopy(self.canonical_records[memory_id]))
            for memory_id in memory_ids[:limit]
        ]

    def delete(self, memory_id: str) -> dict[str, str]:
        if memory_id not in self.canonical_records:
            raise KeyError(memory_id)
        record = self.canonical_records[memory_id]
        self.__controller_restore_vault[memory_id] = copy.deepcopy(record)
        self.public_audit_records[memory_id] = {
            "memory_id": memory_id,
            "content_sha256": record.content_sha256,
            "record_sha256": record.record_sha256,
        }

        del self.canonical_records[memory_id]
        aliases_to_delete = [
            alias for alias, target in self.alias_to_memory_id.items() if target == memory_id
        ]
        for alias in aliases_to_delete:
            del self.alias_to_memory_id[alias]
        duplicate_keys = [
            key
            for key, value in self.near_duplicate_copies.items()
            if value.get("memory_id") == memory_id
        ]
        for key in duplicate_keys:
            del self.near_duplicate_copies[key]
        for token in list(self.keyword_index):
            self.keyword_index[token].discard(memory_id)
            if not self.keyword_index[token]:
                del self.keyword_index[token]
        for content_sha256 in list(self.ann_index):
            self.ann_index[content_sha256].discard(memory_id)
            if not self.ann_index[content_sha256]:
                del self.ann_index[content_sha256]
        self.graph_index.pop(memory_id, None)
        for edges in self.graph_index.values():
            edges.discard(memory_id)
        self.reranker_features.pop(memory_id, None)
        target_unique_needles, _ = self.partition_forbidden_needles(record)
        # Invalidate the target's dependency closure while retaining every
        # unrelated item.  Explicit MemoryScopedValue provenance handles
        # paraphrased derived state; frozen needles conservatively clean up
        # legacy values that still contain target identifiers or content.
        self._invalidate_retrieval_cache_for_delete(record, target_unique_needles)
        self.tool_cache = self._prune_surface(
            self.tool_cache, record, target_unique_needles
        )
        self.summary_cache.pop(memory_id, None)
        for derived_values in self.derived_artifacts.values():
            derived_values.pop(memory_id, None)
        self.active_prompt = self._prune_surface(
            self.active_prompt, record, target_unique_needles
        )
        self.scratchpad = self._prune_surface(
            self.scratchpad, record, target_unique_needles
        )
        self.session_context = self._prune_surface(
            self.session_context, record, target_unique_needles
        )
        self.kv_context = self._prune_surface(
            self.kv_context, record, target_unique_needles
        )
        self.runtime_variables = self._prune_surface(
            self.runtime_variables, record, target_unique_needles
        )
        self.derived_artifacts = self._prune_surface(
            self.derived_artifacts, record, target_unique_needles
        )
        self.agent_accessible_archives = self._prune_surface(
            self.agent_accessible_archives, record, target_unique_needles
        )
        self.agent_accessible_logs = self._prune_surface(
            self.agent_accessible_logs, record, target_unique_needles
        )
        self.debug_endpoints = self._prune_surface(
            self.debug_endpoints, record, target_unique_needles
        )
        return copy.deepcopy(self.public_audit_records[memory_id])

    def restore(self, memory_id: str) -> dict[str, str]:
        if memory_id in self.canonical_records:
            raise ValueError(f"memory {memory_id} is already present")
        if memory_id not in self.__controller_restore_vault:
            raise KeyError(memory_id)
        record = copy.deepcopy(self.__controller_restore_vault[memory_id])
        result = self.put(record)
        if result["record_sha256"] != self.public_audit_records[memory_id]["record_sha256"]:
            raise RuntimeError("restore changed the memory record")
        return result

    def _surface_payloads(self) -> dict[str, Any]:
        return {
            "canonical_memory_record": self.canonical_records,
            "alias_and_near_duplicate_copies": {
                "aliases": self.alias_to_memory_id,
                "near_duplicates": self.near_duplicate_copies,
            },
            "embedding_ann_keyword_graph_indexes": {
                "ann": self.ann_index,
                "keyword": self.keyword_index,
                "graph": self.graph_index,
            },
            "reranker_derived_features": self.reranker_features,
            "retrieval_tool_summary_caches": {
                "retrieval": self.retrieval_cache,
                "tool": self.tool_cache,
                "summary": self.summary_cache,
            },
            "active_prompt_scratchpad_session_kv_context": {
                "active_prompt": self.active_prompt,
                "scratchpad": self.scratchpad,
                "session": self.session_context,
                "kv": self.kv_context,
            },
            "runtime_variables": self.runtime_variables,
            "derived_summary_rule_skill_plan_edge_tag_cached_answer": self.derived_artifacts,
            "agent_accessible_archive_logs_debug_endpoints": {
                "archives": self.agent_accessible_archives,
                "logs": self.agent_accessible_logs,
                "debug": self.debug_endpoints,
            },
        }

    def _component_payloads(self) -> dict[str, Any]:
        """Expose each concrete agent-reachable component for non-vacuous eviction checks."""

        return {
            "canonical_record": self.canonical_records,
            "aliases": self.alias_to_memory_id,
            "near_duplicates": self.near_duplicate_copies,
            "ann_index": self.ann_index,
            "keyword_index": self.keyword_index,
            "graph_index": self.graph_index,
            "reranker_features": self.reranker_features,
            "retrieval_cache": self.retrieval_cache,
            "tool_cache": self.tool_cache,
            "summary_cache": self.summary_cache,
            "active_prompt": self.active_prompt,
            "scratchpad": self.scratchpad,
            "session_context": self.session_context,
            "kv_context": self.kv_context,
            "runtime_variables": self.runtime_variables,
            **{
                f"derived_{name}": self.derived_artifacts[name]
                for name in (
                    "summary",
                    "rule",
                    "skill",
                    "plan",
                    "edge",
                    "tag",
                    "cached_answer",
                )
            },
            "agent_accessible_archives": self.agent_accessible_archives,
            "agent_accessible_logs": self.agent_accessible_logs,
            "debug_endpoints": self.debug_endpoints,
        }

    @staticmethod
    def forbidden_needles(original: MemoryRecord) -> list[dict[str, str]]:
        """Return the frozen exact and derived sentinels used by leak scans."""

        content_tokens = normalize_text(original.content).split()
        fragment_size = 8
        fragments = {
            " ".join(content_tokens[index : index + fragment_size])
            for index in range(max(0, len(content_tokens) - fragment_size + 1))
        }
        provenance_json = canonical_json(original.provenance)
        metadata_summary = str(original.metadata.get("summary", ""))
        values: list[tuple[str, str]] = [
            ("memory_id", original.memory_id),
            ("exact_content", original.content),
            ("content_sha256", original.content_sha256),
            ("record_sha256", original.record_sha256),
            ("policy_id", str(original.metadata.get("policy_id", ""))),
            ("provenance", provenance_json),
            ("leakage_sentinel", str(original.metadata.get("leakage_sentinel", ""))),
            ("metadata_summary", metadata_summary),
        ]
        values.extend(("alias", value) for value in original.aliases)
        values.extend(("retrieval_key", value) for value in original.retrieval_keys)
        values.extend(
            ("graph_edge", str(value))
            for value in original.metadata.get("graph_edges", [])
            if str(value).strip()
        )
        values.extend(
            (f"metadata_scalar::{path}", value)
            for path, value in AuditMemoryStore._recursive_string_values(
                original.metadata
            )
        )
        values.extend(
            (f"provenance_scalar::{path}", value)
            for path, value in AuditMemoryStore._recursive_string_values(
                original.provenance
            )
        )
        values.extend(("derived_content_fragment_8gram", value) for value in sorted(fragments))
        unique_values = dict.fromkeys(
            (kind, value) for kind, value in values if value.strip()
        )
        return [{"kind": kind, "value": value} for kind, value in unique_values]

    @staticmethod
    def _needle_is_owned_by_record(
        needle: dict[str, str], record: MemoryRecord
    ) -> bool:
        """Whether a non-target record legitimately owns the same semantic value."""

        kind = needle["kind"]
        value = needle["value"]
        if kind == "exact_content":
            return record.content == value
        if kind == "content_sha256":
            return record.content_sha256 == value
        if kind == "policy_id":
            return str(record.metadata.get("policy_id", "")) == value
        if kind == "metadata_summary":
            return str(record.metadata.get("summary", "")) == value
        if kind == "graph_edge":
            return value in {
                str(edge) for edge in record.metadata.get("graph_edges", [])
            }
        if kind == "provenance":
            return canonical_json(record.provenance) == value
        if kind == "retrieval_key":
            return value in record.retrieval_keys
        if kind == "derived_content_fragment_8gram":
            return normalize_text(value) in normalize_text(record.content)
        if kind.startswith("metadata_scalar::"):
            return value in {
                other_value
                for _, other_value in AuditMemoryStore._recursive_string_values(
                    record.metadata
                )
            }
        if kind.startswith("provenance_scalar::"):
            return value in {
                other_value
                for _, other_value in AuditMemoryStore._recursive_string_values(
                    record.provenance
                )
            }
        return False

    def partition_forbidden_needles(
        self, original: MemoryRecord
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Split leak sentinels into target-unique and legitimately shared values.

        Stable identity, record hash, aliases and leakage sentinel are always
        target-specific.  Semantic content/key/provenance values are not leak
        evidence when an extant distractor independently owns the same value.
        """

        enforced: list[dict[str, str]] = []
        shared: list[dict[str, str]] = []
        remaining_records = tuple(self.canonical_records.values())
        for needle in self.forbidden_needles(original):
            if any(
                self._needle_is_owned_by_record(needle, record)
                for record in remaining_records
            ):
                shared.append(needle)
            else:
                enforced.append(needle)
        return enforced, shared

    @staticmethod
    def scan_payload_for_needles(
        payload: Any, needles: list[dict[str, str]]
    ) -> tuple[str, list[dict[str, str]]]:
        serialized = payload if isinstance(payload, str) else canonical_json(payload)
        normalized_serialized = normalize_text(serialized)
        lowered_serialized = serialized.lower()
        matches: list[dict[str, str]] = []
        for needle in needles:
            value = needle["value"]
            if needle["kind"] == "derived_content_fragment_8gram":
                found = normalize_text(value) in normalized_serialized
            else:
                found = value.lower() in lowered_serialized
            if found:
                matches.append({"kind": needle["kind"], "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()})
        return serialized, matches

    def effective_eviction_manifest(self, original: MemoryRecord) -> dict[str, Any]:
        needles, shared_needles = self.partition_forbidden_needles(original)
        before_probe_payloads = self._surface_payloads()
        before_probe_sha256 = sha256_json(before_probe_payloads)
        retrieval_after_delete = self.retrieve(
            " ".join(original.retrieval_keys) + " " + original.content,
            cache_result=False,
        )
        _, retrieval_matches = self.scan_payload_for_needles(
            retrieval_after_delete, needles
        )
        retrieval_contains_target = any(
            item.get("memory_id") == original.memory_id
            for item in retrieval_after_delete
            if isinstance(item, dict)
        )
        retrieval_leaked_target = retrieval_contains_target or bool(retrieval_matches)
        after_probe_payloads = self._surface_payloads()
        after_probe_sha256 = sha256_json(after_probe_payloads)
        checks: list[dict[str, Any]] = []
        checks.append(
            {
                "surface": "negative_probe_side_effect_free",
                "result": "PASS" if before_probe_sha256 == after_probe_sha256 else "FAIL",
                "evidence_sha256": after_probe_sha256,
                "detail": "all store surfaces are byte-canonically unchanged by the negative probe"
                if before_probe_sha256 == after_probe_sha256
                else "negative probe mutated at least one store surface",
            }
        )
        checks.append(
            {
                "surface": "retrieval_interface_negative_probe",
                "result": "PASS" if not retrieval_leaked_target else "FAIL",
                "evidence_sha256": sha256_json(retrieval_after_delete),
                "matched_forbidden_needles": retrieval_matches,
                "detail": "non-caching retrieval returns no target or target-derived candidate"
                if not retrieval_leaked_target
                else "retrieval leaked the target or target-derived information",
            }
        )
        final_surface_hashes: dict[str, str] = {}
        for surface_name, payload in after_probe_payloads.items():
            serialized, matches = self.scan_payload_for_needles(payload, needles)
            pass_ = not matches
            surface_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            final_surface_hashes[surface_name] = surface_sha256
            checks.append(
                {
                    "surface": surface_name,
                    "result": "PASS" if pass_ else "FAIL",
                    "evidence_sha256": surface_sha256,
                    "matched_forbidden_needles": matches,
                    "detail": "no frozen exact identifier, hash, alias, key, policy, provenance, fragment, or sentinel is reachable"
                    if pass_
                    else "one or more frozen forbidden needles remain reachable",
                }
            )
        component_hashes: dict[str, str] = {}
        for component_name, payload in self._component_payloads().items():
            serialized, matches = self.scan_payload_for_needles(payload, needles)
            pass_ = not matches
            component_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            component_hashes[component_name] = component_sha256
            checks.append(
                {
                    "surface": f"component::{component_name}",
                    "result": "PASS" if pass_ else "FAIL",
                    "evidence_sha256": component_sha256,
                    "matched_forbidden_needles": matches,
                    "detail": "concrete component contains no target or target-derived frozen needle"
                    if pass_
                    else "concrete component retains target or target-derived information",
                }
            )
        return {
            "memory_id": original.memory_id,
            "public_audit_record": copy.deepcopy(self.public_audit_records.get(original.memory_id)),
            "controller_vault_disclosed_to_agent": False,
            "controller_only_audit_surfaces_excluded_from_leak_scan": [
                "controller_restore_vault",
                "controller_retrieval_cache_dependency_index",
                "public_audit_records",
            ],
            "dependency_invalidation_scope": "target_only",
            "forbidden_needle_manifest": [
                {
                    "kind": needle["kind"],
                    "value_sha256": hashlib.sha256(needle["value"].encode("utf-8")).hexdigest(),
                    "scope": "target_unique_enforced",
                }
                for needle in needles
            ],
            "shared_needle_manifest": [
                {
                    "kind": needle["kind"],
                    "value_sha256": hashlib.sha256(needle["value"].encode("utf-8")).hexdigest(),
                    "scope": "legitimately_owned_by_remaining_memory",
                }
                for needle in shared_needles
            ],
            "negative_probe_cache_result": False,
            "surface_state_sha256_before_probe": before_probe_sha256,
            "final_surface_state_sha256": after_probe_sha256,
            "final_surface_hashes": final_surface_hashes,
            "final_component_hashes": component_hashes,
            "checks": checks,
            "all_pass": all(check["result"] == "PASS" for check in checks),
        }

    def interface_manifest(self, memory_id: str, query: str) -> dict[str, Any]:
        record = self.canonical_records[memory_id]
        retrieved = self.agent_view().retrieve(query)
        return {
            "stable_memory_id": record.memory_id == memory_id,
            "provenance_present": bool(record.provenance),
            "retrieval_returns_exact_id": bool(
                retrieved and retrieved[0]["memory_id"] == memory_id
            ),
            "delete_interface": callable(self.delete),
            "restore_interface": callable(self.restore),
            "retrieval_interface": callable(self.retrieve),
            "record_sha256": record.record_sha256,
        }
