from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from audit_memory_store import (
    AuditMemoryStore,
    MemoryRecord,
    MemoryScopedValue,
    canonical_json,
    normalize_text,
    sha256_json,
)


def _make_records() -> tuple[MemoryRecord, MemoryRecord]:
    target = MemoryRecord(
        memory_id="pm3ar-target-v1",
        memory_type="episodic_semantic",
        content="Shared vector helix payload for deterministic ANN collision.",
        provenance={
            "source_episode": "target-scoped-probe",
            "source_type": "constructed/test",
            "created_by": "preempt-3a-r-controller",
        },
        aliases=("cobalt-ledger-memory",),
        retrieval_keys=("cobalt ledger", "shared retrieval"),
        metadata={
            "summary": "cobalt target workflow summary",
            "graph_edges": ["cobalt-target-node"],
            "policy_id": "target_probe_policy_v1",
            "leakage_sentinel": "PM3AR-SENTINEL::TARGET::COBALT",
        },
    )
    distractor = MemoryRecord(
        memory_id="pm3ar-distractor-v1",
        memory_type="episodic_semantic",
        content="Shared vector helix payload for deterministic ANN collision.",
        provenance={
            "source_episode": "distractor-scoped-probe",
            "source_type": "constructed/test",
            "created_by": "preempt-3a-r-controller",
        },
        aliases=("amber-calendar-memory",),
        retrieval_keys=("amber calendar", "shared retrieval"),
        metadata={
            "summary": "amber control workflow summary",
            "graph_edges": ["amber-control-node"],
            "policy_id": "distractor_probe_policy_v1",
            "leakage_sentinel": "PM3AR-SENTINEL::DISTRACTOR::AMBER",
        },
    )
    return target, distractor


def _scoped(store: AuditMemoryStore, memory_id: str, value: Any) -> MemoryScopedValue:
    return store.scoped_value(value, memory_id)


def _populate_all_surfaces(
    store: AuditMemoryStore, target: MemoryRecord, distractor: MemoryRecord
) -> dict[str, dict[str, str]]:
    put_results = {
        "target": store.put(target),
        "distractor": store.put(distractor),
    }

    for record, color in ((target, "cobalt"), (distractor, "amber")):
        memory_id = record.memory_id
        store.near_duplicate_copies[f"{memory_id}:near"] = {
            "memory_id": memory_id,
            "content_sha256": record.content_sha256,
            "copy": _scoped(store, memory_id, f"{color} near duplicate payload"),
        }
        store.tool_cache[memory_id] = _scoped(
            store, memory_id, {"tool_result": f"{color} derived tool result"}
        )
        store.active_prompt.append(
            _scoped(store, memory_id, f"{color} active prompt material")
        )
        store.scratchpad.append(
            _scoped(store, memory_id, f"{color} scratchpad material")
        )
        store.session_context[memory_id] = _scoped(
            store, memory_id, {"session": f"{color} session material"}
        )
        store.kv_context[memory_id] = _scoped(
            store, memory_id, {"kv": f"{color} kv material"}
        )
        store.runtime_variables[memory_id] = _scoped(
            store, memory_id, {"runtime": f"{color} runtime material"}
        )
        for surface_name in store.derived_artifacts:
            store.derived_artifacts[surface_name][memory_id] = _scoped(
                store,
                memory_id,
                {"kind": surface_name, "payload": f"{color} derived material"},
            )
        store.agent_accessible_archives[memory_id] = _scoped(
            store, memory_id, {"archive": f"{color} archived material"}
        )
        store.agent_accessible_logs[memory_id] = _scoped(
            store, memory_id, {"log": f"{color} log material"}
        )
        store.debug_endpoints[memory_id] = _scoped(
            store, memory_id, {"debug": f"{color} debug material"}
        )

    # Legacy/unscoped summaries exercise the conservative textual fallback.
    # Their neutral keys carry no memory ID or other target sentinel.
    store.tool_cache["legacy-summary-target"] = target.metadata["summary"]
    store.tool_cache["legacy-summary-distractor"] = distractor.metadata["summary"]
    # A distractor-owned outer mapping must not make a nested target scope
    # atomic/untraversable.  The outer owner/shared payload must survive while
    # the nested target dependency is removed.
    store.tool_cache["mixed-nested-owner"] = {
        "memory_id": distractor.memory_id,
        "shared_payload": target.content,
        "nested_target": {
            "memory_id": target.memory_id,
            "secret": target.aliases[0],
        },
    }

    store.retrieve("cobalt ledger", limit=2)
    store.retrieve("amber calendar", limit=2)
    store.retrieve("shared retrieval", limit=2)
    return put_results


def _select_scoped(values: list[Any], memory_id: str) -> list[Any]:
    return [
        value
        for value in values
        if isinstance(value, MemoryScopedValue)
        and memory_id in value.depends_on_memory_ids
    ]


def _record_projection(store: AuditMemoryStore, record: MemoryRecord) -> dict[str, Any]:
    memory_id = record.memory_id
    owned_cache_queries = {
        normalize_text(value)
        for value in (*record.retrieval_keys, record.content)
    }
    return {
        "canonical_memory_record": store.canonical_records.get(memory_id),
        "alias_and_near_duplicate_copies": {
            "aliases": {
                key: value
                for key, value in store.alias_to_memory_id.items()
                if value == memory_id
            },
            "near_duplicates": {
                key: value
                for key, value in store.near_duplicate_copies.items()
                if value.get("memory_id") == memory_id
            },
        },
        "embedding_ann_keyword_graph_indexes": {
            "ann": {
                key: {memory_id}
                for key, value in store.ann_index.items()
                if memory_id in value
            },
            "keyword": {
                key: {memory_id}
                for key, value in store.keyword_index.items()
                if memory_id in value
            },
            "graph": (
                {memory_id: store.graph_index[memory_id]}
                if memory_id in store.graph_index
                else {}
            ),
        },
        "reranker_derived_features": (
            {memory_id: store.reranker_features[memory_id]}
            if memory_id in store.reranker_features
            else {}
        ),
        "retrieval_tool_summary_caches": {
            "retrieval": {
                key: [candidate for candidate in value if candidate == memory_id]
                for key, value in store.retrieval_cache.items()
                if memory_id in value and key in owned_cache_queries
            },
            "tool": (
                {
                    key: value
                    for key, value in store.tool_cache.items()
                    if key == memory_id
                    or (
                        not isinstance(value, MemoryScopedValue)
                        and value == record.metadata.get("summary")
                    )
                }
            ),
            "summary": (
                {memory_id: store.summary_cache[memory_id]}
                if memory_id in store.summary_cache
                else {}
            ),
        },
        "active_prompt_scratchpad_session_kv_context": {
            "active_prompt": _select_scoped(store.active_prompt, memory_id),
            "scratchpad": _select_scoped(store.scratchpad, memory_id),
            "session": (
                {memory_id: store.session_context[memory_id]}
                if memory_id in store.session_context
                else {}
            ),
            "kv": (
                {memory_id: store.kv_context[memory_id]}
                if memory_id in store.kv_context
                else {}
            ),
        },
        "runtime_variables": (
            {memory_id: store.runtime_variables[memory_id]}
            if memory_id in store.runtime_variables
            else {}
        ),
        "derived_summary_rule_skill_plan_edge_tag_cached_answer": {
            surface_name: (
                {memory_id: values[memory_id]} if memory_id in values else {}
            )
            for surface_name, values in store.derived_artifacts.items()
        },
        "agent_accessible_archive_logs_debug_endpoints": {
            "archives": (
                {memory_id: store.agent_accessible_archives[memory_id]}
                if memory_id in store.agent_accessible_archives
                else {}
            ),
            "logs": (
                {memory_id: store.agent_accessible_logs[memory_id]}
                if memory_id in store.agent_accessible_logs
                else {}
            ),
            "debug": (
                {memory_id: store.debug_endpoints[memory_id]}
                if memory_id in store.debug_endpoints
                else {}
            ),
        },
    }


def _equivalence_evidence(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    surfaces: dict[str, dict[str, Any]] = {}
    for surface_name in AuditMemoryStore.SURFACE_NAMES:
        before_json = canonical_json(before[surface_name])
        after_json = canonical_json(after[surface_name])
        surfaces[surface_name] = {
            "before_canonical_json": before_json,
            "after_canonical_json": after_json,
            "before_sha256": sha256_json(before[surface_name]),
            "after_sha256": sha256_json(after[surface_name]),
            "equal": before_json == after_json,
        }
    return {
        "surfaces": surfaces,
        "all_surfaces_equal": all(item["equal"] for item in surfaces.values()),
    }


def _has_positive_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, MemoryRecord):
        return True
    if isinstance(value, MemoryScopedValue):
        return _has_positive_payload(value.value)
    if isinstance(value, dict):
        return any(_has_positive_payload(item) for item in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_has_positive_payload(item) for item in value)
    if isinstance(value, str):
        return bool(value)
    return True


def _component_presence(projection: dict[str, Any]) -> dict[str, bool]:
    aliases = projection["alias_and_near_duplicate_copies"]
    indexes = projection["embedding_ann_keyword_graph_indexes"]
    caches = projection["retrieval_tool_summary_caches"]
    context = projection["active_prompt_scratchpad_session_kv_context"]
    derived = projection[
        "derived_summary_rule_skill_plan_edge_tag_cached_answer"
    ]
    endpoints = projection["agent_accessible_archive_logs_debug_endpoints"]
    components = {
        "canonical_record": projection["canonical_memory_record"],
        "aliases": aliases["aliases"],
        "near_duplicates": aliases["near_duplicates"],
        "ann_index": indexes["ann"],
        "keyword_index": indexes["keyword"],
        "graph_index": indexes["graph"],
        "reranker_features": projection["reranker_derived_features"],
        "retrieval_cache": caches["retrieval"],
        "tool_cache": caches["tool"],
        "summary_cache": caches["summary"],
        "active_prompt": context["active_prompt"],
        "scratchpad": context["scratchpad"],
        "session_context": context["session"],
        "kv_context": context["kv"],
        "runtime_variables": projection["runtime_variables"],
        **{f"derived_{name}": value for name, value in derived.items()},
        "agent_accessible_archives": endpoints["archives"],
        "agent_accessible_logs": endpoints["logs"],
        "debug_endpoints": endpoints["debug"],
    }
    return {name: _has_positive_payload(value) for name, value in components.items()}


def run_probe() -> dict[str, Any]:
    target, distractor = _make_records()
    store = AuditMemoryStore()

    canonical_record = canonical_json(target)
    canonical_asdict = canonical_json(asdict(target))
    set_payload = {"members": set(["zeta", "alpha", "middle"])}
    reordered_set_payload = {"members": set(["middle", "zeta", "alpha"])}
    tuple_payload = {"members": ("alpha", "middle", "zeta")}
    decoded_set = json.loads(canonical_json(set_payload))["members"]
    serializer_checks = {
        "non_empty_memory_record": bool(canonical_record),
        "dataclass_matches_field_mapping": canonical_record == canonical_asdict,
        "set_is_stable": canonical_json(set_payload)
        == canonical_json(reordered_set_payload),
        "set_members_sorted": decoded_set
        == {"__canonical_type__": "set", "items": ["alpha", "middle", "zeta"]},
        "set_has_type_domain_separation": canonical_json(set_payload)
        != canonical_json({"members": ["alpha", "middle", "zeta"]}),
        "tuple_is_stable": canonical_json(tuple_payload)
        == canonical_json({"members": ["alpha", "middle", "zeta"]}),
    }
    serializer_checks["all_pass"] = all(serializer_checks.values())

    put_results = _populate_all_surfaces(store, target, distractor)
    shared_query = "shared retrieval"
    shared_query_key = "shared retrieval"
    target_derived_mixed_query = "cobalt ledger shared retrieval"
    target_derived_mixed_query_key = "cobalt ledger shared retrieval"
    shared_before = store.retrieve(shared_query, limit=5, cache_result=True)
    mixed_before = store.retrieve(
        target_derived_mixed_query, limit=5, cache_result=True
    )
    ann_collision_sha256 = target.content_sha256
    collision_before = {
        "shared_query": shared_query,
        "target_derived_mixed_query": target_derived_mixed_query,
        "ann_content_sha256": ann_collision_sha256,
        "target_content_sha256": target.content_sha256,
        "distractor_content_sha256": distractor.content_sha256,
        "same_content_sha256": target.content_sha256 == distractor.content_sha256,
        "ann_members": sorted(store.ann_index.get(ann_collision_sha256, set())),
        "shared_query_result_ids": [item["memory_id"] for item in shared_before],
        "shared_cache_ids": list(store.retrieval_cache.get(shared_query_key, [])),
        "target_derived_mixed_query_result_ids": [
            item["memory_id"] for item in mixed_before
        ],
        "target_derived_mixed_cache_ids": list(
            store.retrieval_cache.get(target_derived_mixed_query_key, [])
        ),
    }
    summary_fallback_before = {
        "target_present": store.tool_cache.get("legacy-summary-target")
        == target.metadata["summary"],
        "distractor_present": store.tool_cache.get("legacy-summary-distractor")
        == distractor.metadata["summary"],
        "distractor_value_sha256": sha256_json(
            store.tool_cache.get("legacy-summary-distractor")
        ),
    }
    mixed_nested_before = copy.deepcopy(
        store.tool_cache["mixed-nested-owner"]
    )
    target_before = _record_projection(store, target)
    distractor_before = _record_projection(store, distractor)
    target_component_presence = _component_presence(target_before)
    distractor_component_presence = _component_presence(distractor_before)
    positive_component_coverage = {
        component: {
            "target_nonempty": target_component_presence[component],
            "distractor_nonempty": distractor_component_presence[component],
        }
        for component in target_component_presence
    }
    positive_component_coverage["all_components_nonempty"] = all(
        item["target_nonempty"] and item["distractor_nonempty"]
        for item in positive_component_coverage.values()
        if isinstance(item, dict)
    )
    positive_surface_coverage = {
        surface_name: {
            "target_nonempty": _has_positive_payload(target_before[surface_name]),
            "distractor_nonempty": _has_positive_payload(
                distractor_before[surface_name]
            ),
            "target_before_sha256": sha256_json(target_before[surface_name]),
            "distractor_before_sha256": sha256_json(
                distractor_before[surface_name]
            ),
        }
        for surface_name in AuditMemoryStore.SURFACE_NAMES
    }
    positive_surface_coverage["all_surfaces_nonempty"] = all(
        item["target_nonempty"] and item["distractor_nonempty"]
        for item in positive_surface_coverage.values()
        if isinstance(item, dict)
    )
    delete_result = store.delete(target.memory_id)
    eviction_manifest = store.effective_eviction_manifest(target)
    shared_after = store.retrieve(shared_query, limit=5, cache_result=True)
    collision_after_delete = {
        "ann_members": sorted(store.ann_index.get(ann_collision_sha256, set())),
        "shared_query_result_ids": [item["memory_id"] for item in shared_after],
        "shared_cache_ids": list(store.retrieval_cache.get(shared_query_key, [])),
        "target_derived_mixed_cache_present": target_derived_mixed_query_key
        in store.retrieval_cache,
    }
    summary_fallback_after = {
        "target_present": "legacy-summary-target" in store.tool_cache,
        "distractor_present": store.tool_cache.get("legacy-summary-distractor")
        == distractor.metadata["summary"],
        "distractor_value_sha256": sha256_json(
            store.tool_cache.get("legacy-summary-distractor")
        ),
    }
    mixed_nested_after = copy.deepcopy(
        store.tool_cache.get("mixed-nested-owner")
    )
    mixed_nested_checks = {
        "outer_distractor_owner_present_before": mixed_nested_before.get(
            "memory_id"
        )
        == distractor.memory_id,
        "nested_target_present_before": isinstance(
            mixed_nested_before.get("nested_target"), dict
        )
        and mixed_nested_before["nested_target"].get("memory_id")
        == target.memory_id,
        "outer_distractor_owner_preserved": isinstance(mixed_nested_after, dict)
        and mixed_nested_after.get("memory_id") == distractor.memory_id,
        "shared_distractor_payload_preserved": isinstance(
            mixed_nested_after, dict
        )
        and mixed_nested_after.get("shared_payload")
        == mixed_nested_before.get("shared_payload"),
        "nested_target_scope_removed": isinstance(mixed_nested_after, dict)
        and "nested_target" not in mixed_nested_after,
    }
    mixed_nested_checks["all_pass"] = all(mixed_nested_checks.values())
    summary_fallback_checks = {
        "target_and_distractor_present_before_delete": summary_fallback_before[
            "target_present"
        ]
        and summary_fallback_before["distractor_present"],
        "target_unique_unscoped_summary_removed": not summary_fallback_after[
            "target_present"
        ],
        "distractor_unscoped_summary_preserved": summary_fallback_after[
            "distractor_present"
        ],
        "distractor_unscoped_summary_hash_equal": summary_fallback_before[
            "distractor_value_sha256"
        ]
        == summary_fallback_after["distractor_value_sha256"],
    }
    summary_fallback_checks["all_pass"] = all(summary_fallback_checks.values())
    shared_collision_checks = {
        "same_content_sha256": collision_before["same_content_sha256"],
        "ann_collision_contains_both_before_delete": collision_before["ann_members"]
        == sorted([target.memory_id, distractor.memory_id]),
        "shared_query_contains_both_before_delete": sorted(
            collision_before["shared_query_result_ids"]
        )
        == sorted([target.memory_id, distractor.memory_id]),
        "shared_cache_contains_both_before_delete": sorted(
            collision_before["shared_cache_ids"]
        )
        == sorted([target.memory_id, distractor.memory_id]),
        "target_derived_mixed_cache_contains_both_before_delete": sorted(
            collision_before["target_derived_mixed_cache_ids"]
        )
        == sorted([target.memory_id, distractor.memory_id]),
        "ann_collision_preserves_only_distractor_after_delete": collision_after_delete[
            "ann_members"
        ]
        == [distractor.memory_id],
        "shared_query_preserves_only_distractor_after_delete": collision_after_delete[
            "shared_query_result_ids"
        ]
        == [distractor.memory_id],
        "shared_cache_preserves_only_distractor_after_delete": collision_after_delete[
            "shared_cache_ids"
        ]
        == [distractor.memory_id],
        "target_derived_mixed_cache_is_fully_invalidated_after_delete": not collision_after_delete[
            "target_derived_mixed_cache_present"
        ],
    }
    shared_collision_checks["all_pass"] = all(shared_collision_checks.values())
    target_after_delete = _record_projection(store, target)
    target_component_absence = {
        component: not present
        for component, present in _component_presence(target_after_delete).items()
    }
    target_component_absence["all_components_absent"] = all(
        target_component_absence.values()
    )
    distractor_after_delete = _record_projection(store, distractor)
    deletion_equivalence = _equivalence_evidence(
        distractor_before, distractor_after_delete
    )
    target_retrieval = store.retrieve("cobalt ledger", limit=2, cache_result=False)
    enforced_needles, _ = store.partition_forbidden_needles(target)
    _, target_retrieval_matches = store.scan_payload_for_needles(
        target_retrieval, enforced_needles
    )
    target_unreachable = {
        "canonical_record_absent": target.memory_id not in store.canonical_records,
        "retrieval_contains_no_target_id": all(
            item.get("memory_id") != target.memory_id
            for item in target_retrieval
            if isinstance(item, dict)
        ),
        "retrieval_contains_no_target_needles": not target_retrieval_matches,
        "effective_eviction_all_pass": eviction_manifest["all_pass"],
        "effective_eviction_check_count": len(eviction_manifest["checks"]),
        "all_store_surface_checks_pass": all(
            check["result"] == "PASS" for check in eviction_manifest["checks"]
        ),
        "all_target_components_absent": target_component_absence[
            "all_components_absent"
        ],
    }
    target_unreachable["all_pass"] = bool(
        target_unreachable["canonical_record_absent"]
        and target_unreachable["retrieval_contains_no_target_id"]
        and target_unreachable["retrieval_contains_no_target_needles"]
        and target_unreachable["effective_eviction_all_pass"]
        and target_unreachable["all_store_surface_checks_pass"]
        and target_unreachable["all_target_components_absent"]
    )

    distractor_before_restore = _record_projection(store, distractor)
    restore_result = store.restore(target.memory_id)
    distractor_after_restore = _record_projection(store, distractor)
    restore_equivalence = _equivalence_evidence(
        distractor_before_restore, distractor_after_restore
    )
    restored_ids = sorted(store.canonical_records)
    restore_identity = {
        "requested_memory_id": target.memory_id,
        "restored_memory_id": restore_result["memory_id"],
        "put_record_sha256": put_results["target"]["record_sha256"],
        "restored_record_sha256": restore_result["record_sha256"],
        "expected_record_ids": sorted([target.memory_id, distractor.memory_id]),
        "actual_record_ids": restored_ids,
        "same_target_item": (
            restore_result["memory_id"] == target.memory_id
            and restore_result["record_sha256"]
            == put_results["target"]["record_sha256"]
        ),
        "no_extra_record": restored_ids == sorted([target.memory_id, distractor.memory_id]),
        "distractor_unchanged_by_restore": restore_equivalence[
            "all_surfaces_equal"
        ],
        "distractor_restore_equivalence": restore_equivalence,
    }
    restore_identity["all_pass"] = bool(
        restore_identity["same_target_item"]
        and restore_identity["no_extra_record"]
        and restore_identity["distractor_unchanged_by_restore"]
    )

    result = {
        "schema_version": "preempt-mem-3a-r-target-distractor-probe-v1",
        "serializer_checks": serializer_checks,
        "positive_surface_coverage": positive_surface_coverage,
        "positive_component_coverage": positive_component_coverage,
        "put_results": put_results,
        "delete_result": delete_result,
        "effective_eviction_manifest": eviction_manifest,
        "shared_keyword_cache_and_ann_collision": {
            "before_delete": collision_before,
            "after_delete": collision_after_delete,
            "checks": shared_collision_checks,
        },
        "unscoped_summary_fallback": {
            "before_delete": summary_fallback_before,
            "after_delete": summary_fallback_after,
            "checks": summary_fallback_checks,
        },
        "mixed_nested_dependency_invalidation": {
            "before_delete": mixed_nested_before,
            "after_delete": mixed_nested_after,
            "checks": mixed_nested_checks,
        },
        "target_unreachable": target_unreachable,
        "target_component_absence_after_delete": target_component_absence,
        "distractor_equivalence_after_target_delete": deletion_equivalence,
        "restore_identity": restore_identity,
    }
    result["all_pass"] = bool(
        serializer_checks["all_pass"]
        and positive_surface_coverage["all_surfaces_nonempty"]
        and positive_component_coverage["all_components_nonempty"]
        and shared_collision_checks["all_pass"]
        and summary_fallback_checks["all_pass"]
        and mixed_nested_checks["all_pass"]
        and target_unreachable["all_pass"]
        and deletion_equivalence["all_surfaces_equal"]
        and restore_identity["all_pass"]
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output_path = Path(args.output).resolve()
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing probe: {output_path}")
    result = run_probe()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
