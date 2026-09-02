from __future__ import annotations

"""Run one PREEMPT-Mem 3A-R AppWorld case across isolated branches.

The trusted controller in this module owns the memory store and an AppWorld
instance that is explicitly initialized without ground truth.  The Agent is a
separate, copied, ``python -I`` structured-tool worker.  Official evaluation is
deferred until all three Agent processes for the case have exited and their DB
states have been frozen, then is performed twice in separate processes.

This entry point is deliberately non-overwriting.  It never calls
``AppWorld.execute`` or ``AppWorld.evaluate`` and never places raw API/RPC
payloads in the shareable run directory.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from audit_memory_store import AuditMemoryStore, MemoryRecord, canonical_json
from evidence_integrity import (
    REDACTION_SCHEMA,
    assert_redacted_jsonl,
    logical_lf_sha256,
    manifest_root_sha256,
    nonce_commitment,
    read_json,
    redact_sensitive,
    sha256_bytes,
    sha256_file,
    sha256_json,
    tree_entries,
    validate_run_attestation,
    write_json_new,
)
from isolated_rpc import (
    PROTOCOL_VERSION,
    PublicAppWorldGateway,
    run_capability_probes,
    run_structured_agent,
)


BRANCHES = ("Full", "Evicted", "Restore")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
AGENT_REQUEST_SCHEMA = "preempt-mem-3a-r-agent-request-v1"
PLAN_SCHEMA = "preempt-mem-3a-r-structured-agent-plan-v1"
BRANCH_RESULT_SCHEMA = "preempt-mem-3a-r-branch-result-v1"


class RunnerEvidenceError(RuntimeError):
    """Raised before or during a run when its frozen evidence contract fails."""


def resolve_project_path(project_root: Path, relative_path: str) -> Path:
    path = (project_root / relative_path).resolve()
    if path != project_root and project_root not in path.parents:
        raise RunnerEvidenceError(f"Path escapes project root: {relative_path}")
    return path


def write_text_new(path: Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _jsonl_bytes(rows: Iterable[Any]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def write_jsonl_new(path: Path, rows: Iterable[Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_jsonl_bytes(rows))


def tree_attestation(path: Path) -> dict[str, Any]:
    entries = tree_entries(path)
    return {
        "directory": path.name,
        "file_count": len(entries),
        "total_bytes": sum(item["size"] for item in entries),
        "tree_manifest_root_sha256": manifest_root_sha256(entries),
        "entries": entries,
    }


def load_isolated_config(project_root: Path, overlay_path: Path) -> dict[str, Any]:
    overlay = read_json(overlay_path)
    if not isinstance(overlay, Mapping):
        raise RunnerEvidenceError("Isolated config must be a JSON object")
    base_relative = overlay.get("base_config_path")
    if not isinstance(base_relative, str) or not base_relative:
        raise RunnerEvidenceError("Isolated config has no base_config_path")
    base_path = resolve_project_path(project_root, base_relative)
    base = read_json(base_path)
    if not isinstance(base, Mapping):
        raise RunnerEvidenceError("Base case config must be a JSON object")
    global_config = dict(base.get("global", {}))
    overrides = overlay.get("global_overrides", {})
    if not isinstance(overrides, Mapping):
        raise RunnerEvidenceError("global_overrides must be an object")
    global_config.update(overrides)
    merged = dict(base)
    for key, value in overlay.items():
        if key not in {"base_config_path", "global_overrides"}:
            merged[key] = value
    merged["global"] = global_config
    merged["base_config_path"] = base_relative
    merged["base_config_sha256"] = sha256_file(base_path)
    merged["overlay_config_sha256"] = sha256_file(overlay_path)
    return merged


def validate_execution_freeze(
    *,
    project_root: Path,
    freeze_path: Path,
    freeze: Mapping[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    if (
        freeze.get("schema_version")
        != "preempt-mem-3a-r-execution-freeze-v1"
        or freeze.get("status") != "FROZEN_BEFORE_RUN_ISOLATED"
        or freeze.get("claim_scope")
        != "constructed deterministic selector-channel mechanism smoke"
        or freeze.get("pilot_started") is not False
    ):
        raise RunnerEvidenceError("Execution freeze schema/status/claim/Pilot mismatch")
    if freeze.get("primary_evidence_run") != run_root.name:
        raise RunnerEvidenceError("Execution freeze binds a different run id")
    frozen_run = resolve_project_path(project_root, str(freeze.get("must_precede_run", "")))
    if frozen_run != run_root:
        raise RunnerEvidenceError("Execution freeze binds a different run root")
    if not str(freeze.get("status", "")).startswith("FROZEN_BEFORE_"):
        raise RunnerEvidenceError("Execution freeze is not marked as pre-run")
    files = freeze.get("files")
    if not isinstance(files, Mapping) or not files:
        raise RunnerEvidenceError("Execution freeze contains no frozen files")
    config_relative = freeze.get("case_config")
    base_relative = freeze.get("base_config")
    environment_relative = freeze.get("environment_spec")
    if not all(
        isinstance(value, str) and value
        for value in (config_relative, base_relative, environment_relative)
    ):
        raise RunnerEvidenceError("Execution freeze omits config/base/environment paths")
    config_path = resolve_project_path(project_root, str(config_relative))
    overlay = read_json(config_path)
    if not isinstance(overlay, Mapping) or overlay.get("base_config_path") != base_relative:
        raise RunnerEvidenceError("Execution freeze base config differs from config overlay")
    required_paths = {
        config_path,
        resolve_project_path(project_root, str(base_relative)),
        resolve_project_path(project_root, str(environment_relative)),
        project_root / "third_step_a/README.md",
        project_root / "third_step_a/artifacts/witnesses.json",
        *(project_root / "third_step_a/src").glob("*.py"),
        *(project_root / "third_step_a/tests").glob("*.py"),
        *(project_root / "third_step_a/prompts").glob("*.txt"),
    }
    required_relatives = {
        path.resolve().relative_to(project_root).as_posix()
        for path in required_paths
        if path.is_file()
    }
    if set(str(key).replace("\\", "/") for key in files) != required_relatives:
        raise RunnerEvidenceError("Execution freeze file set is under/over-inclusive")
    if freeze.get("file_count") != len(required_relatives):
        raise RunnerEvidenceError("Execution freeze file_count mismatch")
    checks: list[dict[str, Any]] = []
    for relative, expected_sha256 in sorted(files.items()):
        path = resolve_project_path(project_root, str(relative))
        actual_sha256 = sha256_file(path) if path.is_file() else None
        checks.append(
            {
                "path": str(relative).replace("\\", "/"),
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "equal": expected_sha256 == actual_sha256,
            }
        )
    failed = [item["path"] for item in checks if not item["equal"]]
    if failed:
        raise RunnerEvidenceError(f"Execution freeze mismatch: {failed}")
    return {
        "freeze_id": freeze.get("execution_freeze_id"),
        "freeze_path": freeze_path.relative_to(project_root).as_posix(),
        "freeze_sha256": sha256_file(freeze_path),
        "file_count": len(checks),
        "all_files_equal": True,
        "checks": checks,
    }


def make_record(case: Mapping[str, Any]) -> MemoryRecord:
    item = case["candidate_memory"]
    source = case["source_episode"]
    content_sha256 = hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
    return MemoryRecord(
        memory_id=item["memory_id"],
        memory_type=item["memory_type"],
        content=item["content"],
        provenance={
            "dataset": source["dataset"],
            "source_task_id": source["task_id"],
            "generator_or_scenario_id": source["generator_or_scenario_id"],
            "source_variation": source["variation"],
            "source_specs_sha256": source["specs_sha256"],
            "source_solution_sha256": source["source_solution_sha256"],
            "derivation": item["provenance"],
        },
        aliases=tuple(item["aliases"]),
        retrieval_keys=tuple(item["retrieval_keys"]),
        metadata={
            "policy_id": item["policy_id"],
            "summary": item["content"],
            "graph_edges": [],
            "leakage_sentinel": (
                f"PM3A-SENTINEL::{item['memory_id']}::{content_sha256[:16]}"
            ),
        },
    )


def public_retrieval_projection(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project store records to the frozen Agent-visible retrieval schema.

    Provenance, controller audit hashes, summaries, graph state and leakage
    sentinels are controller-only.  The selector-channel Agent needs only the
    external item fields and the single public policy selector.
    """

    projected: list[dict[str, Any]] = []
    for record in records:
        metadata = record.get("metadata")
        if not isinstance(metadata, Mapping) or not isinstance(
            metadata.get("policy_id"), str
        ):
            raise RunnerEvidenceError("Retrieved record has no public policy_id")
        projected.append(
            {
                "memory_id": record["memory_id"],
                "memory_type": record["memory_type"],
                "content": record["content"],
                "aliases": list(record["aliases"]),
                "retrieval_keys": list(record["retrieval_keys"]),
                "metadata": {"policy_id": metadata["policy_id"]},
            }
        )
    return projected


def compose_treatment_blind_prompt(template: str, target_instruction: str) -> str:
    return template.format(
        target_instruction=target_instruction,
        retrieval_query=target_instruction,
    )


def build_agent_request(
    *,
    target_instruction: str,
    prompt: str,
    retrieval_results: list[dict[str, Any]],
    allowed_tools: list[str],
    nonce_commitment_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": AGENT_REQUEST_SCHEMA,
        "target_instruction": target_instruction,
        "target_instruction_sha256": sha256_bytes(target_instruction.encode("utf-8")),
        "prompt_logical_lf_sha256": logical_lf_sha256(prompt),
        "retrieval_results": retrieval_results,
        "retrieval_results_sha256": sha256_json(retrieval_results),
        "allowed_tools": list(allowed_tools),
        "tool_protocol": PROTOCOL_VERSION,
        "run_nonce_commitment_sha256": nonce_commitment_sha256,
    }


def build_agent_initialize(
    *, target_instruction: str, retrieval_results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Reconstruct the exact four-key JSON object sent on the Agent wire."""

    return {
        "type": "initialize",
        "protocol_version": PROTOCOL_VERSION,
        "target_instruction": target_instruction,
        "retrieval_results": retrieval_results,
    }


def _iter_nontrivial_strings(value: Any, *, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _iter_nontrivial_strings(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_nontrivial_strings(child, path=f"{path}[{index}]")
    elif isinstance(value, str) and len(value.strip()) >= 12:
        yield path, value


_FORBIDDEN_AGENT_KEY_PARTS = (
    "branch",
    "caller_secret",
    "controller",
    "dependency",
    "evaluation",
    "evaluator",
    "eviction",
    "gold",
    "ground_truth",
    "groundtruth",
    "manifest",
    "memory_store",
    "need",
    "project",
    "relationship",
    "severity",
    "vault",
    "witness",
    "world",
    "inspect_stack",
)
_FORBIDDEN_AGENT_EXACT_KEYS = frozenset({"gt", "stack", "store"})


def _initial_firewall_path_components(path: str) -> tuple[str, ...]:
    """Map only trusted scan roots to structural path components.

    The human-readable ``path`` is evidence only.  It must never be parsed for
    authorization because an Agent-controlled mapping key can contain dots and
    bracket text that imitate such a path.
    """

    if path == "$raw":
        return ("raw",)
    if path == "$agent_rpc_transcript.jsonl":
        return ("surface", "agent_rpc_transcript.jsonl")
    return ("untrusted_surface", path)


def _allowed_public_api_schema_key(
    normalized: str, components: tuple[str | int, ...]
) -> bool:
    """Allow relationship fields only beneath an actual public RPC result."""

    if normalized not in {"relationship", "relationships"}:
        return False
    raw_prefix: tuple[str | int, ...] = ("raw", "agent_rpc_transcript")
    persisted_prefix: tuple[str | int, ...] = (
        "surface",
        "agent_rpc_transcript.jsonl",
    )
    if components[:2] == raw_prefix:
        suffix = components[2:]
    elif components[:2] == persisted_prefix:
        suffix = components[2:]
    else:
        return False
    return (
        len(suffix) >= 3
        and isinstance(suffix[0], int)
        and suffix[1:3] == ("response", "result")
    )


def _forbidden_agent_key_findings(
    value: Any,
    *,
    path: str,
    _components: tuple[str | int, ...] | None = None,
) -> list[dict[str, str]]:
    """Find controller-private capabilities encoded as keys, regardless of value type.

    Exact private values remain covered by the needle scan below.  This second,
    structural scan closes the integer/bool/short-string gap (for example
    ``{"Need": 1}`` or ``{"severity": 3}``).  The returned evidence is safe to
    persist because it is only ever persisted when empty; callers fail closed
    before writing a positive finding.
    """

    findings: list[dict[str, str]] = []
    components = (
        _initial_firewall_path_components(path)
        if _components is None
        else _components
    )
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            normalized = re.sub(r"[^a-z0-9]+", "_", key_text.casefold()).strip("_")
            forbidden = normalized in _FORBIDDEN_AGENT_EXACT_KEYS or any(
                part in normalized for part in _FORBIDDEN_AGENT_KEY_PARTS
            )
            if forbidden and not _allowed_public_api_schema_key(normalized, components):
                findings.append(
                    {
                        "path": f"{path}.{key_text}",
                        "key_sha256": sha256_bytes(key_text.encode("utf-8")),
                    }
                )
            findings.extend(
                _forbidden_agent_key_findings(
                    child,
                    path=f"{path}.{key_text}",
                    _components=components + (key_text,),
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(
                _forbidden_agent_key_findings(
                    child,
                    path=f"{path}[{index}]",
                    _components=components + (index,),
                )
            )
    return findings


def _private_partition_for_public(
    *, public: Any, private_sources: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public_values = {
        value for _, value in _iter_nontrivial_strings(public, path="$public")
    }
    private_values: dict[str, set[str]] = {}
    exclusions: dict[str, set[str]] = {}
    for source_name, source in private_sources.items():
        for source_path, value in _iter_nontrivial_strings(
            source, path=f"${source_name}"
        ):
            destination = exclusions if value in public_values else private_values
            destination.setdefault(value, set()).add(source_path)
    needles = [
        {
            "value": value,
            "value_sha256": sha256_bytes(value.encode("utf-8")),
            "length": len(value),
            "source_paths": sorted(paths),
        }
        for value, paths in sorted(private_values.items())
    ]
    excluded = [
        {
            "value": value,
            "value_sha256": sha256_bytes(value.encode("utf-8")),
            "length": len(value),
            "source_paths": sorted(paths),
        }
        for value, paths in sorted(exclusions.items())
    ]
    return needles, excluded


def build_firewall_leakage_manifest(
    *,
    case_root: Path,
    target_instruction: str,
    public_retrieval_records_by_branch: Mapping[str, list[dict[str, Any]]],
    target_relationship: Mapping[str, Any],
    witness: Mapping[str, Any],
    branch_results: Mapping[str, Mapping[str, Any]],
    branch_canaries: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Independently scan every Agent-visible artifact for private values/keys."""
    private_sources: dict[str, Any] = {
        "target_relationship": target_relationship,
        "witness": witness,
        "severity": {
            branch: {
                "severity": result.get("severity"),
                "severity_reason": result.get("severity_reason"),
            }
            for branch, result in branch_results.items()
        },
        "controller_canaries": branch_canaries,
    }
    surface_names = (
        "agent_initialize.json",
        "agent_request.json",
        "agent_final.redacted.json",
        "retrieval_results.json",
        "prompt.txt",
        "agent_rpc_transcript.jsonl",
        "structured_agent_plan.json",
    )
    scans: list[dict[str, Any]] = []
    branch_partitions: list[dict[str, Any]] = []
    total_matches = 0
    total_forbidden_keys = 0
    for branch in BRANCHES:
        public = {
            "target_instruction": target_instruction,
            "public_retrieval_records": public_retrieval_records_by_branch[branch],
        }
        needles, exclusions = _private_partition_for_public(
            public=public, private_sources=private_sources
        )
        branch_partitions.append(
            {
                "branch": branch,
                "private_needle_count": len(needles),
                "private_needles": [
                    {key: value for key, value in needle.items() if key != "value"}
                    for needle in needles
                ],
                "public_overlap_exclusion_count": len(exclusions),
                "public_overlap_exclusions": [
                    {
                        key: value
                        for key, value in exclusion.items()
                        if key != "value"
                    }
                    | {
                        "reason": (
                            "exact value is legitimate in this branch's frozen target "
                            "instruction/retrieval input"
                        )
                    }
                    for exclusion in exclusions
                ],
            }
        )
        for name in surface_names:
            path = case_root / branch.lower() / name
            text = path.read_text(encoding="utf-8")
            matches = [
                {
                    "value_sha256": needle["value_sha256"],
                    "source_paths": needle["source_paths"],
                }
                for needle in needles
                if needle["value"] in text
            ]
            if name.endswith(".json"):
                structured = json.loads(text)
            elif name.endswith(".jsonl"):
                structured = [
                    json.loads(line)
                    for line in text.splitlines()
                    if line.strip()
                ]
            else:
                structured = None
            key_findings = (
                _forbidden_agent_key_findings(structured, path=f"${name}")
                if structured is not None
                else []
            )
            total_matches += len(matches)
            total_forbidden_keys += len(key_findings)
            scans.append(
                {
                    "branch": branch,
                    "surface": name,
                    "surface_file_sha256": sha256_file(path),
                    "private_exact_match_count": len(matches),
                    "matches": matches,
                    "forbidden_private_key_count": len(key_findings),
                    "forbidden_private_key_findings": key_findings,
                }
            )
    if total_matches or total_forbidden_keys:
        raise RunnerEvidenceError(
            "Agent-visible firewall leakage scan found "
            f"{total_matches} private exact matches and {total_forbidden_keys} forbidden keys"
        )
    return {
        "schema_version": "preempt-mem-3a-r-firewall-leakage-v2",
        "needle_rule": (
            "exact case-sensitive strings length>=12 from target_relationship/Need/severity/"
            "witness/gold/canaries, excluding exact values independently present in frozen "
            "that branch's target instruction or public retrieval projection"
        ),
        "forbidden_key_rule": (
            "recursive case-insensitive normalized-key rejection for controller/private "
            "capability parts, independent of value type or length"
        ),
        "branch_partitions": branch_partitions,
        "surface_scan_count": len(scans),
        "surface_scans": scans,
        "capability_probe_transcript_excluded": True,
        "capability_probe_exclusion_reason": (
            "negative probes intentionally name forbidden capabilities such as branch"
        ),
        "total_private_exact_match_count": 0,
        "total_forbidden_private_key_count": 0,
        "all_pass": True,
    }


def build_raw_controller_firewall_scan(
    *,
    target_instruction: str,
    public_retrieval_records_by_branch: Mapping[str, list[dict[str, Any]]],
    target_relationship: Mapping[str, Any],
    witness: Mapping[str, Any],
    branch_canaries: Mapping[str, Mapping[str, str]],
    branch_contexts: Mapping[str, Mapping[str, Any]],
    failure_output: Path | None = None,
) -> dict[str, Any]:
    """Scan raw in-memory Agent wire evidence before it is irreversibly dropped."""

    private_sources = {
        "target_relationship": target_relationship,
        "witness": witness,
        "controller_canaries": branch_canaries,
    }
    scans: list[dict[str, Any]] = []
    total_matches = 0
    total_forbidden_keys = 0
    for branch in BRANCHES:
        public = {
            "target_instruction": target_instruction,
            "public_retrieval_records": public_retrieval_records_by_branch[branch],
        }
        needles, exclusions = _private_partition_for_public(
            public=public, private_sources=private_sources
        )
        context = branch_contexts[branch]
        raw_payload = {
            "agent_initialize": context["initialize_wire"],
            "agent_rpc_transcript": context["raw_transcript_controller_only"],
            "agent_final_result": context["raw_agent_result_controller_only"],
        }
        serialized = canonical_json(raw_payload)
        matches = [
            {
                "value_sha256": needle["value_sha256"],
                "source_paths": needle["source_paths"],
            }
            for needle in needles
            if needle["value"] in serialized
        ]
        total_matches += len(matches)
        key_findings = _forbidden_agent_key_findings(raw_payload, path="$raw")
        total_forbidden_keys += len(key_findings)
        scans.append(
            {
                "branch": branch,
                "raw_virtual_payload_sha256": sha256_bytes(
                    serialized.encode("utf-8")
                ),
                "raw_transcript_virtual_sha256": context[
                    "raw_transcript_virtual_sha256"
                ],
                "private_exact_match_count": len(matches),
                "matches": matches,
                "forbidden_private_key_count": len(key_findings),
                "forbidden_private_key_findings": key_findings,
                "private_needle_count": len(needles),
                "private_needles": [
                    {
                        "value_sha256": needle["value_sha256"],
                        "source_paths": needle["source_paths"],
                    }
                    for needle in needles
                ],
                "public_overlap_exclusion_count": len(exclusions),
                "public_overlap_exclusion_sha256s": sorted(
                    exclusion["value_sha256"] for exclusion in exclusions
                ),
            }
        )
    if total_matches or total_forbidden_keys:
        if failure_output is not None:
            write_json_new(
                failure_output,
                {
                    "schema_version": "preempt-mem-3a-r-raw-firewall-failure-v1",
                    "raw_values_persisted": False,
                    "total_private_exact_match_count": total_matches,
                    "total_forbidden_private_key_count": total_forbidden_keys,
                    "branch_scans_hash_and_key_paths_only": scans,
                },
            )
        raise RunnerEvidenceError(
            "Raw pre-redaction Agent evidence contains "
            f"{total_matches} private exact strings and {total_forbidden_keys} forbidden keys"
        )
    return {
        "schema_version": "preempt-mem-3a-r-raw-controller-firewall-scan-v2",
        "scan_timing": (
            "after all three Agents exited, witness evidence was first read, and frozen "
            "private case fields were first materialized into controller-only scan inputs; "
            "before raw controller-only payloads were discarded"
        ),
        "branch_scans": scans,
        "total_private_exact_match_count": 0,
        "total_forbidden_private_key_count": 0,
        "raw_payloads_written_to_disk": False,
        "raw_payloads_discarded_after_scan": True,
        "all_pass": True,
    }


def _fresh_sandbox_path(kind: str) -> Path:
    # Return a non-existent leaf.  isolated_rpc creates it with exist_ok=False,
    # copies the trusted worker into it, and launches only the copied basename.
    base = Path(tempfile.gettempdir()).resolve()
    return base / f"preempt3a-{kind}-{secrets.token_hex(16)}"


def _remove_fresh_sandbox(path: Path) -> None:
    resolved = path.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if resolved.parent != temp_root or not resolved.name.startswith("preempt3a-"):
        raise RunnerEvidenceError(f"Refusing to remove unexpected sandbox path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _redact_controller_transcript(
    *,
    raw_rows: list[Any],
    rpc_redacted_rows: list[Any],
    nonce: str,
) -> tuple[list[Any], int, str]:
    # Start from the RPC layer's literal-aware redaction (which also removes
    # sensitive values echoed under otherwise innocuous keys), then apply the
    # evidence layer's broader key policy for paths/query/description fields.
    expected_rows: list[Any] = []
    additional_redaction_count = 0
    for row in rpc_redacted_rows:
        redacted, count = redact_sensitive(row, nonce=nonce)
        expected_rows.append(redacted)
        additional_redaction_count += count
    if len(expected_rows) != len(rpc_redacted_rows):
        raise RunnerEvidenceError("RPC redaction changed transcript row cardinality")
    raw_virtual_bytes = _jsonl_bytes(raw_rows)
    return expected_rows, additional_redaction_count, sha256_bytes(raw_virtual_bytes)


def _write_redacted_tool_evidence(
    *,
    branch_root: Path,
    redacted_rows: list[Any],
    raw_virtual_sha256: str,
    rpc_redaction_count: int,
    evidence_additional_redaction_count: int,
    nonce_commitment_sha256: str,
) -> dict[str, Any]:
    transcript_path = branch_root / "agent_rpc_transcript.jsonl"
    api_log_path = branch_root / "api_calls.redacted.jsonl"
    write_jsonl_new(transcript_path, redacted_rows)
    write_jsonl_new(api_log_path, redacted_rows)
    assert_redacted_jsonl(transcript_path)
    api_check = assert_redacted_jsonl(api_log_path)
    attestation = {
        "schema_version": REDACTION_SCHEMA,
        "raw_file_sha256": raw_virtual_sha256,
        "raw_row_count": len(redacted_rows),
        "raw_source": "controller-memory-only canonical JSONL; never written to run artifacts",
        "raw_file_retained_in_shareable_artifacts": False,
        "redacted_file": api_log_path.name,
        "redacted_file_sha256": api_check["file_sha256"],
        "redacted_row_count": api_check["row_count"],
        "rpc_redaction_count": rpc_redaction_count,
        "evidence_additional_redaction_count": evidence_additional_redaction_count,
        "total_redaction_count": (
            rpc_redaction_count + evidence_additional_redaction_count
        ),
        "redaction_count": rpc_redaction_count + evidence_additional_redaction_count,
        "nonce_commitment_sha256": nonce_commitment_sha256,
    }
    write_json_new(branch_root / "api_log_redaction_attestation.json", attestation)
    return attestation


def _sanitize_appworld_internal_log(log_path: Path) -> dict[str, Any]:
    """Remove AppWorld's initialization log from this new experiment.

    We intentionally never call ``world.save_logs`` after the Agent.  All
    actual tool evidence comes from the controller's in-memory RPC transcript.
    AppWorld nevertheless creates an empty initialization file; it is removed
    so no raw log can accidentally become part of later copied evidence.
    """

    if not log_path.exists():
        return {
            "path": log_path.name,
            "existed": False,
            "row_count": 0,
            "file_sha256_before_removal": None,
            "removed": False,
        }
    data = log_path.read_bytes()
    row_count = len([line for line in data.splitlines() if line])
    if row_count:
        raise RunnerEvidenceError(
            "AppWorld persisted raw post-initialization API calls; refusing to retain or copy them"
        )
    digest = sha256_bytes(data)
    log_path.unlink()
    return {
        "path": log_path.name,
        "existed": True,
        "row_count": 0,
        "file_sha256_before_removal": digest,
        "removed": True,
    }


def _minimal_evaluator_environment() -> dict[str, str]:
    keys = (
        "COMSPEC",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "WINDIR",
    )
    environment = {key: os.environ[key] for key in keys if key in os.environ}
    environment.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONWARNINGS": "ignore",
        }
    )
    return environment


def evaluator_semantic_vector(value: Any) -> dict[str, Any]:
    """Project an official vector onto outcome/test-contract semantics.

    AppWorld failure ``trace`` strings contain Python ``set`` reprs whose item
    order is nondeterministic even under a fixed hash seed.  They are retained
    verbatim in both raw vectors and worker envelopes, but excluded from the
    repeatability decision.  No outcome, label, requirement, count, or
    difficulty field is excluded.
    """

    if not isinstance(value, Mapping) or set(value) != {
        "difficulty",
        "failures",
        "num_tests",
        "passes",
        "success",
    }:
        raise RunnerEvidenceError("Official evaluator vector schema is not exact")
    passes = value.get("passes")
    failures = value.get("failures")
    if not isinstance(passes, list) or not isinstance(failures, list):
        raise RunnerEvidenceError("Official evaluator pass/failure vectors are malformed")
    projected_passes: list[dict[str, Any]] = []
    projected_failures: list[dict[str, Any]] = []
    for row in passes:
        if not isinstance(row, Mapping) or set(row) != {"label", "requirement"}:
            raise RunnerEvidenceError("Official evaluator pass row schema is not exact")
        projected_passes.append(dict(row))
    for row in failures:
        if not isinstance(row, Mapping) or set(row) != {
            "label",
            "requirement",
            "trace",
        }:
            raise RunnerEvidenceError("Official evaluator failure row schema is not exact")
        projected_failures.append(
            {"label": row["label"], "requirement": row["requirement"]}
        )
    return {
        "difficulty": value["difficulty"],
        "success": value["success"],
        "num_tests": value["num_tests"],
        "passes": sorted(projected_passes, key=canonical_json),
        "failures": sorted(projected_failures, key=canonical_json),
    }


def run_official_evaluator_process(
    *,
    worker_path: Path,
    appworld_root: Path,
    task_id: str,
    experiment_name: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    command = [
        sys.executable,
        "-I",
        str(worker_path.resolve()),
        "--appworld-root",
        str(appworld_root.resolve()),
        "--task-id",
        task_id,
        "--experiment-name",
        experiment_name,
    ]
    completed = subprocess.run(
        command,
        cwd=Path(tempfile.gettempdir()).resolve(),
        env=_minimal_evaluator_environment(),
        capture_output=True,
        timeout=300,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    stdout_bytes = completed.stdout or b""
    stderr_bytes = completed.stderr or b""
    if completed.returncode != 0:
        raise RunnerEvidenceError(
            "Official evaluator process failed: "
            + json.dumps(
                {
                    "return_code": completed.returncode,
                    "stderr": stderr_bytes[-4000:].decode(
                        "utf-8", errors="backslashreplace"
                    ),
                    "stdout": stdout_bytes[-2000:].decode(
                        "ascii", errors="backslashreplace"
                    ),
                },
                ensure_ascii=False,
            )
        )
    protocol_prefix = b"PREEMPT_MEM_EVALUATOR_RESULT\t"
    protocol_lines = [
        line[len(protocol_prefix) :]
        for line in stdout_bytes.splitlines()
        if line.startswith(protocol_prefix)
    ]
    if len(protocol_lines) != 1:
        raise RunnerEvidenceError(
            f"Evaluator emitted {len(protocol_lines)} framed result lines instead of one"
        )
    try:
        protocol_json = protocol_lines[0].decode("ascii", errors="strict")
    except UnicodeDecodeError as error:
        raise RunnerEvidenceError("Evaluator protocol frame was not ASCII") from error
    wrapper = json.loads(protocol_json)
    result = wrapper.get("result")
    if not isinstance(result, dict):
        raise RunnerEvidenceError("Evaluator worker returned no official result vector")
    process = {
        "pid": wrapper.get("pid"),
        "exit_code": completed.returncode,
        "worker_protocol": wrapper.get("worker_protocol"),
        "worker_sha256": wrapper.get("worker_sha256"),
        "evaluation_entrypoint": wrapper.get("evaluation_entrypoint"),
        "ground_truth_loaded": wrapper.get("ground_truth_loaded_only_in_evaluator"),
        "save_report": wrapper.get("save_report"),
        "task_id": wrapper.get("task_id"),
        "experiment_name": wrapper.get("experiment_name"),
        "appworld_version": wrapper.get("appworld_version"),
        "appworld_module_file": wrapper.get("appworld_module_file"),
        "appworld_module_file_sha256": wrapper.get("appworld_module_file_sha256"),
        "appworld_distribution_direct_url_sha256": wrapper.get(
            "appworld_distribution_direct_url_sha256"
        ),
        "input_db_tree_before": wrapper.get("input_db_tree_before"),
        "input_db_tree_after": wrapper.get("input_db_tree_after"),
        "input_db_unchanged": wrapper.get("input_db_unchanged"),
        "environment_key_names": wrapper.get("environment_key_names"),
        "python_hash_seed": wrapper.get("python_hash_seed"),
        "deterministic_environment": wrapper.get("deterministic_environment"),
        "stderr_sha256": sha256_bytes(stderr_bytes),
        "stdout_sha256": sha256_bytes(stdout_bytes),
        "argv_attested": [
            Path(sys.executable).name,
            "-I",
            worker_path.name,
            "--appworld-root",
            "<ATTESTED_APPWORLD_ROOT>",
            "--task-id",
            task_id,
            "--experiment-name",
            experiment_name,
        ],
    }
    if (
        process["ground_truth_loaded"] is not True
        or process["evaluation_entrypoint"] != "appworld.evaluator.evaluate_task"
        or process["save_report"] is not False
        or process["input_db_unchanged"] is not True
        or process["input_db_tree_before"] != process["input_db_tree_after"]
        or process["python_hash_seed"] != "0"
        or process["deterministic_environment"]
        != {
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONWARNINGS": "ignore",
        }
    ):
        raise RunnerEvidenceError("Evaluator boundary attestation is incomplete")
    return result, process, wrapper


def _line_counter(path: Path) -> dict[bytes, int]:
    if not path.is_file():
        return {}
    counts: dict[bytes, int] = {}
    for line in path.read_bytes().splitlines():
        if line:
            counts[line] = counts.get(line, 0) + 1
    return counts


def recompute_database_diff(left: Path, right: Path) -> dict[str, Any]:
    left_files = {
        path.relative_to(left).as_posix(): path
        for path in left.rglob("*")
        if path.is_file()
    }
    right_files = {
        path.relative_to(right).as_posix(): path
        for path in right.rglob("*")
        if path.is_file()
    }
    names = sorted(set(left_files) | set(right_files))
    files: list[dict[str, Any]] = []
    for name in names:
        left_path, right_path = left_files.get(name), right_files.get(name)
        left_sha = sha256_file(left_path) if left_path is not None else None
        right_sha = sha256_file(right_path) if right_path is not None else None
        row: dict[str, Any] = {
            "file": name,
            "left_sha256": left_sha,
            "right_sha256": right_sha,
            "byte_equal": left_sha == right_sha,
        }
        if name.endswith(".jsonl"):
            left_rows = _line_counter(left_path) if left_path is not None else {}
            right_rows = _line_counter(right_path) if right_path is not None else {}
            row["removed_count"] = sum(
                max(0, count - right_rows.get(line, 0))
                for line, count in left_rows.items()
            )
            row["added_count"] = sum(
                max(0, count - left_rows.get(line, 0))
                for line, count in right_rows.items()
            )
        files.append(row)
    left_tree_root = tree_attestation(left)["tree_manifest_root_sha256"]
    right_tree_root = tree_attestation(right)["tree_manifest_root_sha256"]
    return {
        "left_tree_manifest_root_sha256": left_tree_root,
        "right_tree_manifest_root_sha256": right_tree_root,
        "all_files_byte_equal": left_tree_root == right_tree_root
        and all(item["byte_equal"] for item in files),
        "files": files,
    }


def dependency_versions() -> dict[str, str]:
    records: dict[str, str] = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            records[name] = distribution.version
    return {name: records[name] for name in sorted(records, key=str.casefold)}


def _prepare_run_root(
    *,
    project_root: Path,
    run_root: Path,
    precommit_path: Path,
    freeze_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    precommit = read_json(precommit_path)
    if not isinstance(precommit, Mapping):
        raise RunnerEvidenceError("Precommit attestation must be a JSON object")
    attestation_result = validate_run_attestation(
        precommit,
        project_root=project_root,
        run_root=run_root,
        freeze_path=freeze_path,
    )
    run_root.mkdir(parents=True, exist_ok=True)
    copied_path = run_root / "attestation/precommit_attestation.json"
    if copied_path.exists():
        if copied_path.read_bytes() != precommit_path.read_bytes():
            raise RunnerEvidenceError("Run contains a different precommit attestation")
    else:
        copied_path.parent.mkdir(parents=True, exist_ok=True)
        copied_path.write_bytes(precommit_path.read_bytes())
    return dict(precommit), attestation_result


def _assert_new_appworld_experiment(appworld_root: Path, experiment_name: str) -> None:
    experiment_root = appworld_root / "experiments/outputs" / experiment_name
    if experiment_root.exists():
        raise FileExistsError(
            f"Refusing AppWorld's destructive experiment initialization: {experiment_root} exists"
        )


def _copytree_new(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite evidence tree: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one 3A-R case with process/RPC Agent and evaluator boundaries."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--witnesses", required=True)
    parser.add_argument("--execution-freeze", required=True)
    parser.add_argument("--precommit-attestation", required=True)
    args = parser.parse_args()

    if not RUN_ID_RE.fullmatch(args.run_id):
        raise RunnerEvidenceError("run-id contains unsafe path or experiment characters")
    if args.run_id == "run_reproduction_001":
        raise RunnerEvidenceError("The immutable reproduction run cannot be targeted")

    project_root = Path(__file__).resolve().parents[2]
    config_path = resolve_project_path(project_root, args.config)
    witness_path = resolve_project_path(project_root, args.witnesses)
    freeze_path = resolve_project_path(project_root, args.execution_freeze)
    precommit_path = resolve_project_path(project_root, args.precommit_attestation)
    config = load_isolated_config(project_root, config_path)
    cases = config.get("cases")
    if not isinstance(cases, list):
        raise RunnerEvidenceError("Merged config has no cases")
    matches = [item for item in cases if item.get("case_id") == args.case]
    if len(matches) != 1:
        raise RunnerEvidenceError(f"Expected exactly one case named {args.case}")
    case = matches[0]
    global_config = config["global"]
    isolation = config.get("isolation")
    if not isinstance(isolation, Mapping):
        raise RunnerEvidenceError("Isolated config has no isolation contract")
    if tuple(global_config.get("branch_order", [])) != BRANCHES:
        raise RunnerEvidenceError(f"Branch order must be exactly {BRANCHES}")
    allowed_tools_by_case = isolation.get("allowed_tools_by_case")
    if not isinstance(allowed_tools_by_case, Mapping):
        raise RunnerEvidenceError("isolation.allowed_tools_by_case must be an object")
    allowed_tools = allowed_tools_by_case.get(args.case)
    if not isinstance(allowed_tools, list) or not all(
        isinstance(item, str) and item.count(".") == 1 for item in allowed_tools
    ):
        raise RunnerEvidenceError("allowed_tools must be an exact list of app.api names")
    allowed_tools = sorted(set(allowed_tools))

    run_root = project_root / "third_step_a/artifacts/smoke" / args.run_id
    case_root = run_root / "cases" / args.case
    if case_root.exists():
        raise FileExistsError(f"Refusing to overwrite existing case evidence: {case_root}")
    freeze = read_json(freeze_path)
    if not isinstance(freeze, Mapping):
        raise RunnerEvidenceError("Execution freeze must be a JSON object")
    freeze_validation = validate_execution_freeze(
        project_root=project_root,
        freeze_path=freeze_path,
        freeze=freeze,
        run_root=run_root,
    )
    precommit, precommit_result = _prepare_run_root(
        project_root=project_root,
        run_root=run_root,
        precommit_path=precommit_path,
        freeze_path=freeze_path,
    )
    nonce = precommit["nonce"]
    expected_commitment = nonce_commitment(args.run_id, nonce)
    if precommit_result["nonce_commitment_sha256"] != expected_commitment:
        raise RunnerEvidenceError("Precommit nonce commitment mismatch")

    # No case-private artifact exists before this point, and case_root itself is
    # created only after every frozen input/attestation check has succeeded.
    case_root.mkdir(parents=True)

    appworld_root = (project_root / "third_step_a/appworld_root").resolve()
    os.environ["APPWORLD_ROOT"] = str(appworld_root)
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONWARNINGS"] = "ignore"

    import appworld
    from appworld import AppWorld, update_root

    update_root(str(appworld_root))
    prompt_path = resolve_project_path(project_root, str(global_config["prompt_path"]))
    prompt_template = prompt_path.read_text(encoding="utf-8")
    worker_path = project_root / "third_step_a/src/isolated_agent_worker.py"
    capability_worker_path = (
        project_root / "third_step_a/src/isolated_capability_probe_worker.py"
    )
    evaluator_worker_path = (
        project_root / "third_step_a/src/isolated_evaluator_worker.py"
    )
    for required_worker in (worker_path, capability_worker_path, evaluator_worker_path):
        if not required_worker.is_file():
            raise FileNotFoundError(required_worker)

    task_id = case["target_task"]["task_id"]
    common_world_args = {
        "load_ground_truth": False,
        "random_seed": global_config["seed"],
        "max_interactions": global_config["max_interactions"],
        "max_api_calls_per_interaction": global_config[
            "max_api_calls_per_interaction"
        ],
        "timeout_seconds": global_config["timeout_seconds"],
    }

    checkpoint_experiment = f"preempt3ar_{args.run_id}_{args.case}_checkpoint"
    _assert_new_appworld_experiment(appworld_root, checkpoint_experiment)
    checkpoint_world = AppWorld(
        task_id=task_id,
        experiment_name=checkpoint_experiment,
        **common_world_args,
    )
    if checkpoint_world.task.ground_truth is not None:
        checkpoint_world.close()
        raise RunnerEvidenceError("Checkpoint Agent world unexpectedly loaded ground truth")
    target_instruction = checkpoint_world.task.instruction
    prompt = compose_treatment_blind_prompt(prompt_template, target_instruction)
    checkpoint_id = global_config["state_checkpoint_id"]
    checkpoint_world.save_state(checkpoint_id)
    base_checkpoint = Path(checkpoint_world.output_checkpoints_directory) / checkpoint_id
    base_checkpoint_attestation = tree_attestation(base_checkpoint)
    checkpoint_world.close()

    record = make_record(case)
    # Canary values exist in controller memory before any Agent process starts,
    # but are neither written nor passed through the Agent RPC boundary.  Their
    # commitments become evidence only after the three-process exit barrier.
    caller_secret = (
        "PM3AR-CALLER-SECRET::"
        + sha256_bytes(f"{nonce}\x00{args.case}\x00caller".encode("utf-8"))
    )
    branch_canaries: dict[str, dict[str, str]] = {
        branch: {
            "caller_secret": caller_secret,
            "branch_canary": (
                "PM3AR-BRANCH-CANARY::"
                + sha256_bytes(
                    f"{nonce}\x00{args.case}\x00{branch}\x00branch".encode("utf-8")
                )
            ),
            "created_role": "pre-Agent controller-only firewall canary",
        }
        for branch in BRANCHES
    }
    # The already-parsed frozen config contains private protocol fields, but no
    # witness is read and none of those fields is materialized into Agent inputs,
    # worker messages, or private evidence artifacts before all Agents exit.
    branch_contexts: dict[str, dict[str, Any]] = {}
    agent_pids: list[int] = []

    for branch in BRANCHES:
        branch_slug = branch.lower()
        branch_root = case_root / branch_slug
        branch_root.mkdir(parents=True)
        experiment_name = f"preempt3ar_{args.run_id}_{args.case}_{branch_slug}"
        _assert_new_appworld_experiment(appworld_root, experiment_name)
        world = AppWorld(
            task_id=task_id,
            experiment_name=experiment_name,
            **common_world_args,
        )
        if world.task.ground_truth is not None:
            world.close()
            raise RunnerEvidenceError(f"{branch} Agent world unexpectedly loaded ground truth")
        branch_checkpoint = Path(world.output_checkpoints_directory) / checkpoint_id
        _copytree_new(base_checkpoint, branch_checkpoint)
        if tree_attestation(branch_checkpoint)["tree_manifest_root_sha256"] != (
            base_checkpoint_attestation["tree_manifest_root_sha256"]
        ):
            world.close()
            raise RunnerEvidenceError("Branch checkpoint is not byte-equivalent to base")
        world.load_state(checkpoint_id)
        # AppWorld 0.2.0 on Windows unsets the frozen clock in load_state().
        world._set_datetime()
        if world.task.ground_truth is not None:
            world.close()
            raise RunnerEvidenceError("load_state introduced ground truth into Agent world")

        store = AuditMemoryStore()
        put_result = store.put(record)
        restore_result: dict[str, str] | None = None
        delete_result: dict[str, str] | None = None
        eviction_manifest: dict[str, Any] | None = None
        if branch == "Evicted":
            delete_result = store.delete(record.memory_id)
            eviction_manifest = store.effective_eviction_manifest(record)
        elif branch == "Restore":
            delete_result = store.delete(record.memory_id)
            eviction_manifest = store.effective_eviction_manifest(record)
            pre_restore_retrieval = store.retrieve(target_instruction, limit=1, cache_result=False)
            if pre_restore_retrieval:
                world.close()
                raise RunnerEvidenceError("Restore precondition still retrieves the deleted target")
            restore_result = store.restore(record.memory_id)

        retrieved_internal = store.agent_view().retrieve(target_instruction, limit=1)
        if branch == "Evicted" and retrieved_internal:
            world.close()
            raise RunnerEvidenceError("Evicted branch retrieved an external record")
        if branch in {"Full", "Restore"} and (
            len(retrieved_internal) != 1
            or retrieved_internal[0].get("memory_id") != record.memory_id
        ):
            world.close()
            raise RunnerEvidenceError(f"{branch} did not retrieve the exact target record")
        retrieved = public_retrieval_projection(retrieved_internal)

        request = build_agent_request(
            target_instruction=target_instruction,
            prompt=prompt,
            retrieval_results=retrieved,
            allowed_tools=allowed_tools,
            nonce_commitment_sha256=expected_commitment,
        )
        initialize_wire = build_agent_initialize(
            target_instruction=target_instruction,
            retrieval_results=retrieved,
        )

        gateway = PublicAppWorldGateway(world, allowed_tools=allowed_tools)
        capability_sandbox = _fresh_sandbox_path("probe")
        try:
            capability = run_capability_probes(
                gateway,
                worker_path=capability_worker_path,
                sandbox_directory=capability_sandbox,
            )
        finally:
            _remove_fresh_sandbox(capability_sandbox)
        if capability.get("all_pass") is not True:
            world.close()
            raise RunnerEvidenceError(f"{branch} capability probes did not all fail closed")
        capability_transcript = capability.pop("transcript", None)
        if not isinstance(capability_transcript, list) or len(capability_transcript) != 11:
            world.close()
            raise RunnerEvidenceError("Capability worker returned no complete 10+final transcript")
        capability_transcript_virtual_sha256 = sha256_bytes(
            _jsonl_bytes(capability_transcript)
        )
        if (
            capability.get("transcript_row_count") != len(capability_transcript)
            or capability.get("transcript_virtual_sha256")
            != capability_transcript_virtual_sha256
        ):
            world.close()
            raise RunnerEvidenceError("Capability transcript attestation mismatch")

        agent_sandbox = _fresh_sandbox_path("agent")
        try:
            rpc_result = run_structured_agent(
                world=world,
                target_instruction=target_instruction,
                retrieval_results=retrieved,
                allowed_tools=allowed_tools,
                redaction_nonce=nonce,
                worker_path=worker_path,
                sandbox_directory=agent_sandbox,
                max_tool_calls=global_config["max_api_calls_per_interaction"],
            )
        finally:
            _remove_fresh_sandbox(agent_sandbox)

        process_raw = rpc_result.get("process_attestation")
        if not isinstance(process_raw, Mapping):
            world.close()
            raise RunnerEvidenceError("Agent RPC returned no process attestation")
        agent_pid = process_raw.get("pid")
        if not isinstance(agent_pid, int):
            world.close()
            raise RunnerEvidenceError("Agent RPC process attestation has no PID")
        agent_pids.append(agent_pid)
        initialization_attestation = rpc_result.get("initialization_attestation")
        if not isinstance(initialization_attestation, Mapping) or (
            initialization_attestation.get("exact_fields")
            != sorted(initialize_wire)
            or initialization_attestation.get("target_instruction_sha256")
            != sha256_bytes(target_instruction.encode("utf-8"))
            or initialization_attestation.get("retrieval_results_sha256")
            != sha256_json(retrieved)
            or initialization_attestation.get("private_controller_fields_present")
            is not False
        ):
            world.close()
            raise RunnerEvidenceError("RPC initialize attestation differs from exact Agent wire")

        raw_rows = rpc_result.pop("transcript_raw_controller_only", None)
        raw_agent_result = rpc_result.pop("agent_result_raw_controller_only", None)
        redacted_rows = rpc_result.get("transcript_redacted")
        if (
            not isinstance(raw_rows, list)
            or not isinstance(redacted_rows, list)
            or not isinstance(raw_agent_result, Mapping)
        ):
            world.close()
            raise RunnerEvidenceError(
                "Agent RPC omitted raw/redacted controller-only Agent evidence"
            )
        redacted_rows, additional_redaction_count, raw_virtual_sha256 = _redact_controller_transcript(
            raw_rows=raw_rows,
            rpc_redacted_rows=redacted_rows,
            nonce=nonce,
        )
        rpc_redaction_attestation = rpc_result.get("redaction_attestation")
        if (
            not isinstance(rpc_redaction_attestation, Mapping)
            or not isinstance(rpc_redaction_attestation.get("redaction_count"), int)
            or rpc_redaction_attestation.get("post_redaction_finding_count") != 0
        ):
            world.close()
            raise RunnerEvidenceError("RPC redaction attestation is incomplete")
        rpc_redaction_count = rpc_redaction_attestation["redaction_count"]
        final_message_redacted = rpc_result.get("final_message_redacted")
        if (
            not isinstance(final_message_redacted, Mapping)
            or set(final_message_redacted)
            != {"type", "protocol_version", "ok", "result", "tool_call_count"}
            or final_message_redacted.get("type") != "final"
            or final_message_redacted.get("protocol_version") != PROTOCOL_VERSION
            or final_message_redacted.get("ok") is not True
            or final_message_redacted.get("result") != rpc_result.get("result")
            or final_message_redacted.get("tool_call_count")
            != rpc_result.get("tool_call_count")
        ):
            world.close()
            raise RunnerEvidenceError("Agent final message is not exactly bound to RPC result")

        structured_plan = {
            "schema_version": PLAN_SCHEMA,
            "tool_protocol": PROTOCOL_VERSION,
            "agent_result": rpc_result.get("result"),
            "tool_call_count": rpc_result.get("tool_call_count"),
            "requested_public_tools": [
                f"{row['call'].get('app')}.{row['call'].get('api')}"
                for row in redacted_rows
                if isinstance(row, Mapping) and isinstance(row.get("call"), Mapping)
            ],
            "arbitrary_code_execution": False,
        }
        # The Agent has exited.  Persist its state, freeze a byte copy, then
        # close the GT-free world.  save_logs() is intentionally not called.
        world.save_state()
        source_db = Path(world.output_db_home_path_on_disk)
        source_db_before = tree_attestation(source_db)
        raw_internal_log = Path(world.output_logs_directory) / "api_calls.jsonl"
        world.close()
        internal_log_attestation = _sanitize_appworld_internal_log(raw_internal_log)

        checkpoint_snapshot = branch_root / "checkpoint_snapshot"
        frozen_db = branch_root / "db_snapshot_frozen"
        _copytree_new(branch_checkpoint, checkpoint_snapshot)
        _copytree_new(source_db, frozen_db)
        checkpoint_snapshot_attestation = tree_attestation(checkpoint_snapshot)
        frozen_db_attestation = tree_attestation(frozen_db)
        if checkpoint_snapshot_attestation["tree_manifest_root_sha256"] != (
            base_checkpoint_attestation["tree_manifest_root_sha256"]
        ):
            raise RunnerEvidenceError("Evidence checkpoint differs from the case base snapshot")
        if frozen_db_attestation["tree_manifest_root_sha256"] != (
            source_db_before["tree_manifest_root_sha256"]
        ):
            raise RunnerEvidenceError("Frozen DB copy differs from the post-Agent AppWorld DB")

        # Only public/treatment evidence is written here.  Private manifests,
        # target relationship, witness, severity and evaluator vectors remain
        # controller-only until the case-wide Agent-exit barrier below.
        write_text_new(branch_root / "prompt.txt", prompt)
        write_json_new(branch_root / "retrieval_results.json", retrieved)
        write_json_new(branch_root / "agent_initialize.json", initialize_wire)
        write_json_new(branch_root / "agent_request.json", request)
        write_json_new(
            branch_root / "agent_final.redacted.json",
            dict(final_message_redacted),
        )
        write_json_new(branch_root / "structured_agent_plan.json", structured_plan)
        capability_transcript_path = (
            branch_root / "capability_probe_rpc_transcript.jsonl"
        )
        write_jsonl_new(capability_transcript_path, capability_transcript)
        capability_transcript_file_sha256 = sha256_file(capability_transcript_path)
        capability["transcript_file"] = capability_transcript_path.name
        capability["transcript_file_sha256"] = capability_transcript_file_sha256
        capability["transcript_row_count"] = len(capability_transcript)
        capability_process_raw = capability.get("process_attestation")
        capability_process = (
            dict(capability_process_raw)
            if isinstance(capability_process_raw, Mapping)
            else None
        )
        if capability_process is not None:
            capability_process["rpc_transcript_file_sha256"] = (
                capability_transcript_file_sha256
            )
            capability_process["rpc_transcript_row_count"] = len(
                capability_transcript
            )
            capability["process_attestation"] = capability_process
        write_json_new(branch_root / "capability_probes.json", capability)
        if isinstance(capability_process, Mapping):
            write_json_new(
                branch_root / "capability_process_attestation.json",
                dict(capability_process),
            )
        redaction_attestation = _write_redacted_tool_evidence(
            branch_root=branch_root,
            redacted_rows=redacted_rows,
            raw_virtual_sha256=raw_virtual_sha256,
            rpc_redaction_count=rpc_redaction_count,
            evidence_additional_redaction_count=additional_redaction_count,
            nonce_commitment_sha256=expected_commitment,
        )
        request_path = branch_root / "agent_request.json"
        initialize_path = branch_root / "agent_initialize.json"
        transcript_path = branch_root / "agent_rpc_transcript.jsonl"
        capability_path = branch_root / "capability_probes.json"
        final_message_path = branch_root / "agent_final.redacted.json"
        agent_process_attestation = {
            **dict(process_raw),
            "role": "agent",
            "exit_code": process_raw.get("return_code", process_raw.get("exit_code")),
            "boundary": "structured_json_tool_call_rpc",
            "security_scope": (
                "trusted copied structured-tool worker; not a general Windows arbitrary-code sandbox"
            ),
            "ground_truth_loaded": False,
            "project_path_disclosed": False,
            "no_project_tool_capability": True,
            "controller_state_disclosed": False,
            "no_controller_state_tool_capability": True,
            "windows_arbitrary_code_sandbox_claimed": False,
            "agent_request_file_sha256": sha256_file(request_path),
            "agent_initialize_file_sha256": sha256_file(initialize_path),
            "agent_rpc_transcript_file_sha256": sha256_file(transcript_path),
            "capability_probes_file_sha256": sha256_file(capability_path),
            "agent_final_file_sha256": sha256_file(final_message_path),
            "capability_probe_rpc_transcript_file_sha256": (
                capability_transcript_file_sha256
            ),
            "capability_probe_process_attestation": capability_process,
            "initialization_attestation": rpc_result.get("initialization_attestation"),
            "redaction_attestation": rpc_result.get("redaction_attestation"),
        }
        if agent_process_attestation["exit_code"] != 0:
            raise RunnerEvidenceError("Agent process did not exit successfully")
        write_json_new(
            branch_root / "agent_process_attestation.json",
            agent_process_attestation,
        )
        db_freeze_attestation = {
            "frozen_before_evaluator": True,
            "agent_exit_code": agent_process_attestation["exit_code"],
            "agent_process_pid": agent_pid,
            "source_db_tree_manifest_root_sha256": source_db_before[
                "tree_manifest_root_sha256"
            ],
            "db_tree_manifest_root_sha256": frozen_db_attestation[
                "tree_manifest_root_sha256"
            ],
            "db_file_count": frozen_db_attestation["file_count"],
            "db_total_bytes": frozen_db_attestation["total_bytes"],
            "appworld_internal_raw_log": internal_log_attestation,
            "controller_memory_raw_tool_log_written_to_disk": False,
            "controller_memory_raw_tool_log_retained_until_case_firewall_scan": True,
            "redacted_tool_log_file_sha256": redaction_attestation[
                "redacted_file_sha256"
            ],
        }
        write_json_new(branch_root / "db_freeze_attestation.json", db_freeze_attestation)

        branch_contexts[branch] = {
            "branch_root": branch_root,
            "experiment_name": experiment_name,
            "source_db": source_db,
            "frozen_db": frozen_db,
            "checkpoint_snapshot": checkpoint_snapshot,
            "request": request,
            "initialize_wire": initialize_wire,
            "raw_transcript_controller_only": raw_rows,
            "raw_agent_result_controller_only": raw_agent_result,
            "raw_transcript_virtual_sha256": raw_virtual_sha256,
            "retrieved": retrieved,
            "put_result": put_result,
            "delete_result": delete_result,
            "restore_result": restore_result,
            "eviction_manifest": eviction_manifest,
            "structured_plan": structured_plan,
            "agent_process_attestation": agent_process_attestation,
            "db_freeze_attestation": db_freeze_attestation,
            "checkpoint_attestation": checkpoint_snapshot_attestation,
            "db_attestation": frozen_db_attestation,
            "redaction_attestation": redaction_attestation,
        }

    if len(agent_pids) != len(BRANCHES):
        raise RunnerEvidenceError("Not all three Agent processes reached the exit barrier")
    # This barrier is the first point where any case-private file may be
    # materialized.  Every recorded Agent PID has already exited and every DB
    # has already been frozen byte-for-byte.
    write_json_new(
        case_root / "case_agent_exit_barrier.json",
        {
            "all_three_agent_processes_exited": True,
            "agent_pids": agent_pids,
            "agent_exit_codes": [
                branch_contexts[branch]["agent_process_attestation"]["exit_code"]
                for branch in BRANCHES
            ],
            "all_three_databases_frozen": True,
            "private_artifacts_written_before_barrier": False,
        },
    )

    # Only now are the pre-existing controller-memory canaries materialized.
    for branch in BRANCHES:
        write_json_new(
            branch_contexts[branch]["branch_root"]
            / "post_agent_controller_canaries.json",
            branch_canaries[branch],
        )

    # Witness evidence is first parsed/materialized as private content here.
    # Its bytes were hash-attested before the run, but no witness object was
    # created or sent to an Agent.  Frozen relationship/evaluator fields already
    # present in controller config are likewise first materialized into private
    # evidence objects here.  Neither category entered an Agent request/process.
    witness_document = read_json(witness_path)
    witness_rows = witness_document.get("witnesses") if isinstance(witness_document, Mapping) else None
    if not isinstance(witness_rows, list):
        raise RunnerEvidenceError("Witness file has no witnesses list")
    witness_matches = [item for item in witness_rows if item.get("case_id") == args.case]
    if len(witness_matches) != 1:
        raise RunnerEvidenceError(f"Expected one witness for {args.case}")
    witness = witness_matches[0]

    target_relationship = {
        "target": case["target_task"],
        "source_to_target_dependency": case["source_to_target_dependency"],
        "need_definition": case["need_definition"],
        "need_label": case["need_label"],
        "gold_state_evaluator": case["gold_state_evaluator"],
        "severity_application": case["severity_application"],
    }
    raw_controller_firewall_scan = build_raw_controller_firewall_scan(
        target_instruction=target_instruction,
        public_retrieval_records_by_branch={
            branch: branch_contexts[branch]["retrieved"] for branch in BRANCHES
        },
        target_relationship=target_relationship,
        witness=witness,
        branch_canaries=branch_canaries,
        branch_contexts=branch_contexts,
        failure_output=case_root / "raw_firewall_failure_diagnostic.json",
    )
    # Raw requests/responses/final results never cross this point and are never
    # serialized.  Only their virtual hashes and zero-match commitments survive.
    for branch in BRANCHES:
        del branch_contexts[branch]["raw_transcript_controller_only"]
        del branch_contexts[branch]["raw_agent_result_controller_only"]
    write_json_new(
        case_root / "raw_controller_firewall_scan.json",
        raw_controller_firewall_scan,
    )

    source_specs = appworld_root / "data/tasks" / case["source_episode"]["task_id"] / "specs.json"
    source_episode_artifact = {
        **case["source_episode"],
        "instruction": read_json(source_specs)["instruction"],
        "source_specs_file_sha256_recomputed": sha256_file(source_specs),
        "candidate_record": asdict(record),
        "candidate_record_sha256": record.record_sha256,
    }
    write_json_new(case_root / "source_episode.json", source_episode_artifact)
    write_json_new(case_root / "memory_provenance.json", record.provenance)
    write_json_new(case_root / "target_relationship.json", target_relationship)
    write_json_new(case_root / "witness.json", witness)
    write_json_new(
        case_root / "checkpoint_manifest.json",
        {
            "schema_version": "preempt-mem-3a-r-checkpoint-manifest-v1",
            "checkpoint_id": checkpoint_id,
            "controller_checkpoint_experiment": checkpoint_experiment,
            "base_checkpoint": base_checkpoint_attestation,
            "branch_checkpoint_roots": {
                branch: branch_contexts[branch]["checkpoint_attestation"]
                for branch in BRANCHES
            },
            "all_three_byte_equivalent": len(
                {
                    branch_contexts[branch]["checkpoint_attestation"][
                        "tree_manifest_root_sha256"
                    ]
                    for branch in BRANCHES
                }
            )
            == 1,
            "agent_world_load_ground_truth": False,
        },
    )
    for branch in ("Evicted", "Restore"):
        manifest = branch_contexts[branch]["eviction_manifest"]
        if not isinstance(manifest, Mapping) or manifest.get("all_pass") is not True:
            raise RunnerEvidenceError(f"{branch} effective eviction manifest failed")
        write_json_new(
            branch_contexts[branch]["branch_root"] / "effective_eviction_manifest.json",
            manifest,
        )

    evaluator_results: dict[str, dict[str, Any]] = {}
    for branch in BRANCHES:
        context = branch_contexts[branch]
        branch_root = context["branch_root"]
        evaluator_first, process_first, envelope_first = run_official_evaluator_process(
            worker_path=evaluator_worker_path,
            appworld_root=appworld_root,
            task_id=task_id,
            experiment_name=context["experiment_name"],
        )
        evaluator_second, process_second, envelope_second = run_official_evaluator_process(
            worker_path=evaluator_worker_path,
            appworld_root=appworld_root,
            task_id=task_id,
            experiment_name=context["experiment_name"],
        )
        semantic_first = evaluator_semantic_vector(evaluator_first)
        semantic_second = evaluator_semantic_vector(evaluator_second)
        semantic_vectors_equal = canonical_json(semantic_first) == canonical_json(
            semantic_second
        )
        raw_vectors_exactly_equal = canonical_json(evaluator_first) == canonical_json(
            evaluator_second
        )
        if not semantic_vectors_equal:
            write_json_new(
                branch_root / "evaluator_semantic_stability_failure.json",
                {
                    "schema_version": "preempt-mem-3a-r-evaluator-stability-failure-v1",
                    "first_raw_vector": evaluator_first,
                    "second_raw_vector": evaluator_second,
                    "first_semantic_vector": semantic_first,
                    "second_semantic_vector": semantic_second,
                    "excluded_diagnostic_fields": ["failures[*].trace"],
                },
            )
            raise RunnerEvidenceError(
                f"{branch} evaluator outcome/test-contract vectors are not stable"
            )
        frozen_db_root = context["db_attestation"]["tree_manifest_root_sha256"]
        for repeat_name, envelope in (
            ("first", envelope_first),
            ("second", envelope_second),
        ):
            before_tree = envelope.get("input_db_tree_before")
            after_tree = envelope.get("input_db_tree_after")
            if (
                not isinstance(before_tree, Mapping)
                or before_tree != after_tree
                or before_tree.get("tree_manifest_root_sha256") != frozen_db_root
                or before_tree.get("entries") != context["db_attestation"]["entries"]
            ):
                raise RunnerEvidenceError(
                    f"{branch} evaluator {repeat_name} did not bind the frozen DB copy"
                )
        source_db_after = tree_attestation(context["source_db"])
        if source_db_after["tree_manifest_root_sha256"] != context["db_attestation"][
            "tree_manifest_root_sha256"
        ]:
            raise RunnerEvidenceError(f"{branch} official evaluator mutated its input DB")
        write_json_new(branch_root / "evaluator_first.json", evaluator_first)
        write_json_new(branch_root / "evaluator_second.json", evaluator_second)
        write_json_new(branch_root / "evaluator_first_worker.json", envelope_first)
        write_json_new(branch_root / "evaluator_second_worker.json", envelope_second)
        evaluator_process_attestation = {
            "role": "official_evaluator",
            "pids": [process_first["pid"], process_second["pid"]],
            "exit_codes": [process_first["exit_code"], process_second["exit_code"]],
            "pid": process_first["pid"],
            "exit_code": process_first["exit_code"],
            "agent_process_pid": context["agent_process_attestation"]["pid"],
            "ground_truth_loaded": True,
            "ground_truth_loaded_per_process": [
                process_first["ground_truth_loaded"],
                process_second["ground_truth_loaded"],
            ],
            "save_report": False,
            "save_report_per_process": [
                process_first["save_report"],
                process_second["save_report"],
            ],
            "evaluation_entrypoint": "appworld.evaluator.evaluate_task",
            "evaluation_entrypoints": [
                process_first["evaluation_entrypoint"],
                process_second["evaluation_entrypoint"],
            ],
            "worker_sha256s": [
                process_first["worker_sha256"],
                process_second["worker_sha256"],
            ],
            "processes": [process_first, process_second],
            "evaluator_first_file_sha256": sha256_file(
                branch_root / "evaluator_first.json"
            ),
            "evaluator_second_file_sha256": sha256_file(
                branch_root / "evaluator_second.json"
            ),
            "evaluator_first_worker_file_sha256": sha256_file(
                branch_root / "evaluator_first_worker.json"
            ),
            "evaluator_second_worker_file_sha256": sha256_file(
                branch_root / "evaluator_second_worker.json"
            ),
            "input_db_tree_manifest_root_sha256": context["db_attestation"][
                "tree_manifest_root_sha256"
            ],
            "worker_reported_input_db_tree_manifest_root_sha256s": [
                envelope_first["input_db_tree_before"]["tree_manifest_root_sha256"],
                envelope_second["input_db_tree_before"]["tree_manifest_root_sha256"],
            ],
            "worker_reported_input_db_entries_equal_frozen_copy": True,
            "input_db_unchanged_after_both_evaluators": True,
            "starts_after_case_agent_exit_barrier": True,
            "semantic_stability_policy": (
                "exact outcome,difficulty,count,label,requirement multiset; "
                "retain but exclude failures[*].trace diagnostic repr ordering"
            ),
            "excluded_nondeterministic_diagnostic_fields": ["failures[*].trace"],
            "raw_vectors_exactly_equal": raw_vectors_exactly_equal,
            "semantic_vectors_equal": True,
            "semantic_vector_sha256": sha256_json(semantic_first),
        }
        if (
            len(set(evaluator_process_attestation["pids"])) != 2
            or context["agent_process_attestation"]["pid"]
            in evaluator_process_attestation["pids"]
        ):
            raise RunnerEvidenceError("Evaluator processes are not distinct from Agent/each other")
        write_json_new(
            branch_root / "evaluator_process_attestation.json",
            evaluator_process_attestation,
        )
        evaluator_results[branch] = {
            "first": evaluator_first,
            "second": evaluator_second,
            "process_attestation": evaluator_process_attestation,
        }

    branch_results: dict[str, dict[str, Any]] = {}
    for branch in BRANCHES:
        context = branch_contexts[branch]
        branch_root = context["branch_root"]
        evaluator = evaluator_results[branch]["first"]
        success = evaluator.get("success") is True
        severity = 0 if success else 3
        severity_reason = (
            "official evaluator success; no relevant loss"
            if success
            else "official task failure under the frozen fail-closed selector-channel control"
        )
        prompt_file = branch_root / "prompt.txt"
        plan_file = branch_root / "structured_agent_plan.json"
        branch_result = {
            "schema_version": BRANCH_RESULT_SCHEMA,
            "case_id": args.case,
            "branch": branch,
            "classification": case["case_class"],
            "mechanism_claim": config["mechanism_claim"],
            "experiment_name": context["experiment_name"],
            "target_task_id": task_id,
            "target_instruction_sha256": sha256_bytes(target_instruction.encode("utf-8")),
            "execution_freeze_id": freeze_validation["freeze_id"],
            "execution_freeze_sha256": freeze_validation["freeze_sha256"],
            "execution_freeze_validation_pass": True,
            "prompt_logical_lf_sha256": logical_lf_sha256(
                prompt_file.read_text(encoding="utf-8")
            ),
            "prompt_file_sha256": sha256_file(prompt_file),
            "structured_agent_plan_logical_lf_sha256": logical_lf_sha256(
                plan_file.read_text(encoding="utf-8")
            ),
            "structured_agent_plan_file_sha256": sha256_file(plan_file),
            "checkpoint_id": checkpoint_id,
            "checkpoint_tree_manifest_root_sha256": context[
                "checkpoint_attestation"
            ]["tree_manifest_root_sha256"],
            "checkpoint_byte_equivalent_to_case_base": True,
            "agent_model": global_config["agent_model"],
            "agent_model_type": global_config["agent_model_type"],
            "seed": global_config["seed"],
            "memory_put": context["put_result"],
            "memory_delete": context["delete_result"],
            "memory_restore": context["restore_result"],
            "retrieved_memory_ids": [
                item["memory_id"] for item in context["retrieved"]
            ],
            "agent_result": context["structured_plan"]["agent_result"],
            "agent_process_pid": context["agent_process_attestation"]["pid"],
            "agent_ground_truth_loaded": False,
            "evaluator_process_pids": evaluator_results[branch][
                "process_attestation"
            ]["pids"],
            "evaluator_ground_truth_loaded": True,
            "official_success": success,
            "evaluator_num_tests": evaluator.get("num_tests"),
            "evaluator_pass_count": len(evaluator.get("passes", [])),
            "evaluator_failure_count": len(evaluator.get("failures", [])),
            "evaluator_stable": True,
            "severity": severity,
            "severity_reason": severity_reason,
            "severe_loss": severity >= global_config["severity_rubric"][
                "severe_threshold"
            ],
            "db_tree_manifest_root_sha256": context["db_attestation"][
                "tree_manifest_root_sha256"
            ],
            "db_file_count": context["db_attestation"]["file_count"],
            "capability_probe_all_pass": True,
            "effective_eviction_all_pass": (
                context["eviction_manifest"].get("all_pass")
                if isinstance(context["eviction_manifest"], Mapping)
                else None
            ),
            "api_tool_call_count": context["structured_plan"]["tool_call_count"],
            "api_log_redaction_count": context["redaction_attestation"][
                "redaction_count"
            ],
            "raw_api_logs_retained_in_run": False,
        }
        write_json_new(branch_root / "branch_result.json", branch_result)
        branch_results[branch] = branch_result

    firewall_manifest = build_firewall_leakage_manifest(
        case_root=case_root,
        target_instruction=target_instruction,
        public_retrieval_records_by_branch={
            branch: branch_contexts[branch]["retrieved"] for branch in BRANCHES
        },
        target_relationship=target_relationship,
        witness=witness,
        branch_results=branch_results,
        branch_canaries=branch_canaries,
    )
    raw_scan_path = case_root / "raw_controller_firewall_scan.json"
    firewall_manifest["raw_controller_firewall_scan"] = {
        "file": raw_scan_path.name,
        "file_sha256": sha256_file(raw_scan_path),
        "branch_scans": raw_controller_firewall_scan["branch_scans"],
        "total_private_exact_match_count": 0,
        "total_forbidden_private_key_count": 0,
        "raw_payloads_written_to_disk": False,
        "raw_payloads_discarded_after_scan": True,
        "all_pass": True,
    }
    write_json_new(
        case_root / "firewall_leakage_manifest.json", firewall_manifest
    )

    database_diffs = {
        "checkpoint_to_full": recompute_database_diff(
            branch_contexts["Full"]["checkpoint_snapshot"],
            branch_contexts["Full"]["frozen_db"],
        ),
        "checkpoint_to_evicted": recompute_database_diff(
            branch_contexts["Evicted"]["checkpoint_snapshot"],
            branch_contexts["Evicted"]["frozen_db"],
        ),
        "checkpoint_to_restore": recompute_database_diff(
            branch_contexts["Restore"]["checkpoint_snapshot"],
            branch_contexts["Restore"]["frozen_db"],
        ),
        "full_to_evicted": recompute_database_diff(
            branch_contexts["Full"]["frozen_db"],
            branch_contexts["Evicted"]["frozen_db"],
        ),
        "full_to_restore": recompute_database_diff(
            branch_contexts["Full"]["frozen_db"],
            branch_contexts["Restore"]["frozen_db"],
        ),
    }
    write_json_new(case_root / "database_state_diff.json", database_diffs)

    full = branch_results["Full"]
    evicted = branch_results["Evicted"]
    restore = branch_results["Restore"]
    case_summary = {
        "case_id": args.case,
        "classification": case["case_class"],
        "mechanism_claim": config["mechanism_claim"],
        "source_of_truth": (
            "informational only; aggregate_smoke.py ignores this file and recomputes raw evidence"
        ),
        "all_agent_processes_exited_before_private_artifacts": True,
        "full_success": full["official_success"],
        "evicted_success": evicted["official_success"],
        "restore_success": restore["official_success"],
        "primary_full_minus_evicted_effect": bool(
            full["official_success"] and not evicted["official_success"]
        ),
        "restore_recovery_control": bool(
            restore["official_success"] and full["official_success"]
        ),
        "full_restore_db_byte_equal": database_diffs["full_to_restore"][
            "all_files_byte_equal"
        ],
        "full_restore_evaluator_equal": canonical_json(
            evaluator_results["Full"]["first"]
        )
        == canonical_json(evaluator_results["Restore"]["first"]),
        "checkpoint_equal_all_branches": len(
            {
                context["checkpoint_attestation"]["tree_manifest_root_sha256"]
                for context in branch_contexts.values()
            }
        )
        == 1,
        "agent_request_diff_is_retrieval_only": True,
        "capability_probes_all_denied": True,
        "effective_eviction_all_pass": evicted["effective_eviction_all_pass"],
        "pilot_started": False,
    }
    write_json_new(case_root / "case_summary.json", case_summary)

    invocation = {
        "argv": list(sys.argv),
        "python_executable": Path(sys.executable).as_posix(),
        "python_executable_sha256": sha256_file(Path(sys.executable)),
        "controller_pid": os.getpid(),
        "appworld_version": appworld.__version__,
        "appworld_module_relative_path": Path(appworld.__file__).resolve()
        .relative_to(project_root)
        .as_posix(),
        "appworld_module_file_sha256": sha256_file(
            Path(appworld.__file__).resolve()
        ),
        "appworld_distribution_direct_url_sha256": sha256_bytes(
            (
                importlib.metadata.distribution("appworld").read_text(
                    "direct_url.json"
                )
                or ""
            ).encode("utf-8")
        ),
        "appworld_root": appworld_root.relative_to(project_root).as_posix(),
        "config_path": config_path.relative_to(project_root).as_posix(),
        "config_file_sha256": sha256_file(config_path),
        "base_config_file_sha256": config["base_config_sha256"],
        "prompt_path": prompt_path.relative_to(project_root).as_posix(),
        "prompt_file_sha256": sha256_file(prompt_path),
        "witness_path": witness_path.relative_to(project_root).as_posix(),
        "witness_file_sha256": sha256_file(witness_path),
        "execution_freeze": freeze_validation,
        "precommit_nonce_commitment_sha256": expected_commitment,
        "controller_load_ground_truth": False,
        "evaluator_load_ground_truth": True,
        "agent_protocol": PROTOCOL_VERSION,
        "pilot_started": False,
    }
    write_json_new(case_root / "controller_invocation.json", invocation)

    environment_path = run_root / "environment.json"
    environment = {
        "python": sys.version,
        "python_executable_sha256": sha256_file(Path(sys.executable)),
        "platform": platform.platform(),
        "appworld_version": appworld.__version__,
        "appworld_module_relative_path": Path(appworld.__file__).resolve()
        .relative_to(project_root)
        .as_posix(),
        "appworld_module_file_sha256": sha256_file(
            Path(appworld.__file__).resolve()
        ),
        "appworld_distribution_direct_url_sha256": sha256_bytes(
            (
                importlib.metadata.distribution("appworld").read_text(
                    "direct_url.json"
                )
                or ""
            ).encode("utf-8")
        ),
        "appworld_data_version": (
            appworld_root / "data/version.txt"
        ).read_text(encoding="utf-8").strip(),
        "execution_freeze_id": freeze_validation["freeze_id"],
        "execution_freeze_sha256": freeze_validation["freeze_sha256"],
        "precommit_nonce_commitment_sha256": expected_commitment,
        "isolated_config_sha256": sha256_file(config_path),
        "agent_prompt_sha256": sha256_file(prompt_path),
        "dependencies": dependency_versions(),
        "controller_environment": {
            "APPWORLD_ROOT": appworld_root.relative_to(project_root).as_posix(),
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
            "PYTHONUTF8": os.environ.get("PYTHONUTF8"),
            "PYTHONWARNINGS": os.environ.get("PYTHONWARNINGS"),
        },
        "pilot_started": False,
    }
    if environment_path.exists():
        existing = read_json(environment_path)
        if existing != environment:
            raise RunnerEvidenceError("Run environment changed between case invocations")
    else:
        write_json_new(environment_path, environment)

    print(json.dumps(case_summary, ensure_ascii=False, indent=2))
    if not (
        case_summary["primary_full_minus_evicted_effect"]
        and case_summary["restore_recovery_control"]
        and case_summary["full_restore_db_byte_equal"]
        and case_summary["full_restore_evaluator_equal"]
        and case_summary["checkpoint_equal_all_branches"]
        and case_summary["capability_probes_all_denied"]
        and case_summary["effective_eviction_all_pass"]
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
