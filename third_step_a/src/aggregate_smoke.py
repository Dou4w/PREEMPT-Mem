from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import stat
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from audit_memory_store import AuditMemoryStore, MemoryRecord
from isolated_rpc import (
    CAPABILITY_PROBES,
    PROTOCOL_VERSION,
    RPC_SENSITIVE_KEY_FRAGMENTS,
    WORKER_ENVIRONMENT_KEYS,
)
from target_distractor_probe import run_probe as run_target_distractor_probe

from evidence_integrity import (
    MANIFEST_SCHEMA,
    REDACTION_SCHEMA,
    EvidenceError,
    assert_redacted_jsonl,
    build_manifest,
    canonical_json,
    logical_lf_sha256,
    manifest_root_sha256,
    read_json,
    sha256_file,
    tree_entries,
    validate_run_attestation,
    verify_manifest,
    write_json_new,
)
from seal_run_evidence import PRE_AGGREGATE_EXCLUSIONS


CASE_IDS = ("workflow", "gotcha", "constraint_permission")
BRANCHES = ("Full", "Evicted", "Restore")
RUN_STATIC_FILES = frozenset(
    {
        "environment.json",
        "pre_aggregate_artifact_manifest.json",
        "attestation/precommit_attestation.json",
        "attestation/target_distractor_probe.json",
    }
)
CASE_STATIC_FILES = frozenset(
    {
        "case_agent_exit_barrier.json",
        "case_summary.json",
        "checkpoint_manifest.json",
        "controller_invocation.json",
        "database_state_diff.json",
        "firewall_leakage_manifest.json",
        "memory_provenance.json",
        "raw_controller_firewall_scan.json",
        "source_episode.json",
        "target_relationship.json",
        "witness.json",
    }
)
BRANCH_STATIC_FILES = frozenset(
    {
        "agent_initialize.json",
        "agent_final.redacted.json",
        "agent_process_attestation.json",
        "agent_request.json",
        "agent_rpc_transcript.jsonl",
        "api_calls.redacted.jsonl",
        "api_log_redaction_attestation.json",
        "branch_result.json",
        "capability_probe_rpc_transcript.jsonl",
        "capability_process_attestation.json",
        "capability_probes.json",
        "db_freeze_attestation.json",
        "evaluator_first.json",
        "evaluator_first_worker.json",
        "evaluator_process_attestation.json",
        "evaluator_second.json",
        "evaluator_second_worker.json",
        "post_agent_controller_canaries.json",
        "prompt.txt",
        "retrieval_results.json",
        "structured_agent_plan.json",
    }
)
SNAPSHOT_DIRECTORY_NAMES = ("checkpoint_snapshot", "db_snapshot_frozen")
EXPECTED_APPWORLD_DB_FILES = frozenset(
    {
        "admin.jsonl",
        "amazon.jsonl",
        "api_docs.jsonl",
        "file_system.jsonl",
        "gmail.jsonl",
        "model_hashes.json",
        "phone.jsonl",
        "simple_note.jsonl",
        "spotify.jsonl",
        "splitwise.jsonl",
        "supervisor.jsonl",
        "todoist.jsonl",
        "venmo.jsonl",
    }
)
REQUIRED_CAPABILITY_PROBES = frozenset(
    {
        "caller_secret",
        "inspect_stack",
        "branch",
        "project_file",
        "world_object",
        "memory_store",
        "controller_vault",
        "ground_truth",
        "evaluation_code",
        "controller_directory",
    }
)
EXPECTED_EVALUATOR_DETERMINISTIC_ENVIRONMENT = {
    "PYTHONHASHSEED": "0",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONWARNINGS": "ignore",
}
AGENT_PROCESS_ATTESTATION_KEYS = frozenset(
    {
        "role",
        "pid",
        "argv",
        "cwd",
        "argv_contains_project_path",
        "cwd_contains_project_path",
        "worker_command_contains_project_path",
        "project_root_path_disclosed",
        "environment_key_names",
        "interpreter_sha256",
        "interpreter_outside_project",
        "source_worker_sha256",
        "copied_worker_sha256",
        "source_copy_hash_equal",
        "worker_copied_to_fresh_external_sandbox",
        "worker_copied_to_temporary_directory",
        "python_isolated_flag",
        "boundary",
        "structured_tool_boundary_only",
        "arbitrary_code_sandbox_claimed",
        "os_filesystem_sandbox_claimed",
        "appworld_imported_by_worker",
        "return_code",
        "exit_code",
        "stderr_sha256",
        "stderr_empty",
        "security_scope",
        "ground_truth_loaded",
        "project_path_disclosed",
        "no_project_tool_capability",
        "controller_state_disclosed",
        "no_controller_state_tool_capability",
        "windows_arbitrary_code_sandbox_claimed",
        "agent_request_file_sha256",
        "agent_initialize_file_sha256",
        "agent_rpc_transcript_file_sha256",
        "capability_probes_file_sha256",
        "agent_final_file_sha256",
        "capability_probe_rpc_transcript_file_sha256",
        "capability_probe_process_attestation",
        "initialization_attestation",
        "redaction_attestation",
    }
)
CAPABILITY_PROCESS_ATTESTATION_KEYS = frozenset(
    {
        "role",
        "pid",
        "argv",
        "cwd",
        "argv_contains_project_path",
        "cwd_contains_project_path",
        "worker_command_contains_project_path",
        "project_root_path_disclosed",
        "environment_key_names",
        "interpreter_sha256",
        "interpreter_outside_project",
        "source_worker_sha256",
        "copied_worker_sha256",
        "source_copy_hash_equal",
        "worker_copied_to_fresh_external_sandbox",
        "worker_copied_to_temporary_directory",
        "python_isolated_flag",
        "boundary",
        "structured_tool_boundary_only",
        "arbitrary_code_sandbox_claimed",
        "os_filesystem_sandbox_claimed",
        "appworld_imported_by_worker",
        "return_code",
        "exit_code",
        "stderr_sha256",
        "stderr_empty",
        "rpc_transcript_file_sha256",
        "rpc_transcript_row_count",
    }
)
EVALUATOR_PROCESS_ROW_KEYS = frozenset(
    {
        "pid",
        "exit_code",
        "worker_protocol",
        "worker_sha256",
        "evaluation_entrypoint",
        "ground_truth_loaded",
        "save_report",
        "task_id",
        "experiment_name",
        "appworld_version",
        "appworld_module_file",
        "appworld_module_file_sha256",
        "appworld_distribution_direct_url_sha256",
        "input_db_tree_before",
        "input_db_tree_after",
        "input_db_unchanged",
        "environment_key_names",
        "python_hash_seed",
        "deterministic_environment",
        "stderr_sha256",
        "stdout_sha256",
        "argv_attested",
    }
)
EVALUATOR_ENVELOPE_KEYS = frozenset(
    {
        "worker_protocol",
        "pid",
        "task_id",
        "experiment_name",
        "appworld_version",
        "appworld_module_file",
        "appworld_module_file_sha256",
        "appworld_distribution_direct_url_sha256",
        "ground_truth_loaded_only_in_evaluator",
        "evaluation_entrypoint",
        "save_report",
        "environment_key_names",
        "python_hash_seed",
        "deterministic_environment",
        "input_db_path_role",
        "input_db_tree_before",
        "input_db_tree_after",
        "input_db_unchanged",
        "result",
        "worker_sha256",
    }
)
EVALUATOR_PROCESS_ATTESTATION_KEYS = frozenset(
    {
        "role",
        "pids",
        "exit_codes",
        "pid",
        "exit_code",
        "agent_process_pid",
        "ground_truth_loaded",
        "ground_truth_loaded_per_process",
        "save_report",
        "save_report_per_process",
        "evaluation_entrypoint",
        "evaluation_entrypoints",
        "worker_sha256s",
        "processes",
        "evaluator_first_file_sha256",
        "evaluator_second_file_sha256",
        "evaluator_first_worker_file_sha256",
        "evaluator_second_worker_file_sha256",
        "input_db_tree_manifest_root_sha256",
        "worker_reported_input_db_tree_manifest_root_sha256s",
        "worker_reported_input_db_entries_equal_frozen_copy",
        "input_db_unchanged_after_both_evaluators",
        "starts_after_case_agent_exit_barrier",
        "semantic_stability_policy",
        "excluded_nondeterministic_diagnostic_fields",
        "raw_vectors_exactly_equal",
        "semantic_vectors_equal",
        "semantic_vector_sha256",
    }
)
AGENT_INITIALIZATION_ATTESTATION_KEYS = frozenset(
    {
        "exact_fields",
        "target_instruction_sha256",
        "retrieval_results_sha256",
        "private_controller_fields_present",
    }
)
RPC_REDACTION_ATTESTATION_KEYS = frozenset(
    {
        "schema_version",
        "algorithm",
        "sensitive_key_fragments",
        "redaction_count",
        "sensitive_literal_count",
        "post_redaction_finding_count",
        "nonce_commitment_sha256",
        "raw_transcript_retained_in_shareable_artifacts",
    }
)
API_LOG_REDACTION_ATTESTATION_KEYS = frozenset(
    {
        "schema_version",
        "raw_file_sha256",
        "raw_row_count",
        "raw_source",
        "raw_file_retained_in_shareable_artifacts",
        "redacted_file",
        "redacted_file_sha256",
        "redacted_row_count",
        "rpc_redaction_count",
        "evidence_additional_redaction_count",
        "total_redaction_count",
        "redaction_count",
        "nonce_commitment_sha256",
    }
)
STRUCTURED_AGENT_PLAN_KEYS = frozenset(
    {
        "schema_version",
        "tool_protocol",
        "agent_result",
        "tool_call_count",
        "requested_public_tools",
        "arbitrary_code_execution",
    }
)
BRANCH_RESULT_KEYS = frozenset(
    {
        "schema_version",
        "case_id",
        "branch",
        "classification",
        "mechanism_claim",
        "experiment_name",
        "target_task_id",
        "target_instruction_sha256",
        "execution_freeze_id",
        "execution_freeze_sha256",
        "execution_freeze_validation_pass",
        "prompt_logical_lf_sha256",
        "prompt_file_sha256",
        "structured_agent_plan_logical_lf_sha256",
        "structured_agent_plan_file_sha256",
        "checkpoint_id",
        "checkpoint_tree_manifest_root_sha256",
        "checkpoint_byte_equivalent_to_case_base",
        "agent_model",
        "agent_model_type",
        "seed",
        "memory_put",
        "memory_delete",
        "memory_restore",
        "retrieved_memory_ids",
        "agent_result",
        "agent_process_pid",
        "agent_ground_truth_loaded",
        "evaluator_process_pids",
        "evaluator_ground_truth_loaded",
        "official_success",
        "evaluator_num_tests",
        "evaluator_pass_count",
        "evaluator_failure_count",
        "evaluator_stable",
        "severity",
        "severity_reason",
        "severe_loss",
        "db_tree_manifest_root_sha256",
        "db_file_count",
        "capability_probe_all_pass",
        "effective_eviction_all_pass",
        "api_tool_call_count",
        "api_log_redaction_count",
        "raw_api_logs_retained_in_run",
    }
)
CONTROLLER_INVOCATION_KEYS = frozenset(
    {
        "argv",
        "python_executable",
        "python_executable_sha256",
        "controller_pid",
        "appworld_version",
        "appworld_module_relative_path",
        "appworld_module_file_sha256",
        "appworld_distribution_direct_url_sha256",
        "appworld_root",
        "config_path",
        "config_file_sha256",
        "base_config_file_sha256",
        "prompt_path",
        "prompt_file_sha256",
        "witness_path",
        "witness_file_sha256",
        "execution_freeze",
        "precommit_nonce_commitment_sha256",
        "controller_load_ground_truth",
        "evaluator_load_ground_truth",
        "agent_protocol",
        "pilot_started",
    }
)
DB_FREEZE_ATTESTATION_KEYS = frozenset(
    {
        "frozen_before_evaluator",
        "agent_exit_code",
        "agent_process_pid",
        "source_db_tree_manifest_root_sha256",
        "db_tree_manifest_root_sha256",
        "db_file_count",
        "db_total_bytes",
        "appworld_internal_raw_log",
        "controller_memory_raw_tool_log_written_to_disk",
        "controller_memory_raw_tool_log_retained_until_case_firewall_scan",
        "redacted_tool_log_file_sha256",
    }
)
APPWORLD_INTERNAL_RAW_LOG_KEYS = frozenset(
    {"path", "existed", "row_count", "file_sha256_before_removal", "removed"}
)
CASE_AGENT_EXIT_BARRIER_KEYS = frozenset(
    {
        "all_three_agent_processes_exited",
        "agent_pids",
        "agent_exit_codes",
        "all_three_databases_frozen",
        "private_artifacts_written_before_barrier",
    }
)
TREE_ATTESTATION_KEYS = frozenset(
    {
        "directory",
        "file_count",
        "total_bytes",
        "tree_manifest_root_sha256",
        "entries",
    }
)
ALLOWED_AGENT_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "target_instruction",
        "target_instruction_sha256",
        "prompt_logical_lf_sha256",
        "retrieval_results",
        "retrieval_results_sha256",
        "allowed_tools",
        "tool_protocol",
        "run_nonce_commitment_sha256",
    }
)
FORBIDDEN_AGENT_KEY_PARTS = (
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
FORBIDDEN_AGENT_EXACT_KEYS = frozenset({"gt", "stack", "store"})
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")


def _initial_firewall_path_components(path: str) -> tuple[str, ...]:
    """Map trusted scan roots without parsing Agent-controlled key text."""

    if path == "$raw":
        return ("raw",)
    if path == "$agent_rpc_transcript.jsonl":
        return ("surface", "agent_rpc_transcript.jsonl")
    return ("untrusted_surface", path)


def _allowed_public_api_schema_key(
    normalized: str, components: tuple[str | int, ...]
) -> bool:
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


def expected_preaggregate_static_paths() -> set[str]:
    expected = set(RUN_STATIC_FILES)
    for case_id in CASE_IDS:
        case_prefix = f"cases/{case_id}"
        expected.update(f"{case_prefix}/{name}" for name in CASE_STATIC_FILES)
        for branch in BRANCHES:
            branch_prefix = f"{case_prefix}/{branch.lower()}"
            expected.update(
                f"{branch_prefix}/{name}" for name in BRANCH_STATIC_FILES
            )
            if branch in {"Evicted", "Restore"}:
                expected.add(f"{branch_prefix}/effective_eviction_manifest.json")
    return expected


def expected_preaggregate_static_directories() -> set[str]:
    expected = {"attestation", "cases"}
    for case_id in CASE_IDS:
        case_prefix = f"cases/{case_id}"
        expected.add(case_prefix)
        for branch in BRANCHES:
            branch_prefix = f"{case_prefix}/{branch.lower()}"
            expected.add(branch_prefix)
            expected.update(
                f"{branch_prefix}/{name}" for name in SNAPSHOT_DIRECTORY_NAMES
            )
    return expected


def expected_snapshot_artifact_paths() -> set[str]:
    return {
        f"cases/{case_id}/{branch.lower()}/{directory}/{file_name}"
        for case_id in CASE_IDS
        for branch in BRANCHES
        for directory in SNAPSHOT_DIRECTORY_NAMES
        for file_name in EXPECTED_APPWORLD_DB_FILES
    }


def validate_exact_preaggregate_layout(run_root: Path) -> dict[str, Any]:
    """Reject every non-contract artifact outside independently checked DB trees."""

    expected_files = expected_preaggregate_static_paths()
    expected_directories = expected_preaggregate_static_directories()
    expected_snapshot_files = expected_snapshot_artifact_paths()
    expected_all_files = expected_files | expected_snapshot_files

    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    for path in run_root.rglob("*"):
        junction = bool(getattr(path, "is_junction", lambda: False)())
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        reparse = bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        if path.is_symlink() or junction or reparse:
            raise EvidenceError(
                f"Symlink/junction/reparse point is forbidden in sealed run evidence: {path}"
            )
        relative = path.relative_to(run_root).as_posix()
        if path.is_file():
            observed_files.add(relative)
        elif path.is_dir():
            observed_directories.add(relative)

    missing_files = sorted(expected_all_files - observed_files)
    unexpected_files = sorted(observed_files - expected_all_files)
    missing_directories = sorted(expected_directories - observed_directories)
    unexpected_directories = sorted(observed_directories - expected_directories)
    if missing_files or unexpected_files or missing_directories or unexpected_directories:
        raise EvidenceError(
            "Sealed run violates the exact artifact layout: "
            + json.dumps(
                {
                    "missing_files": missing_files,
                    "unexpected_files": unexpected_files,
                    "missing_directories": missing_directories,
                    "unexpected_directories": unexpected_directories,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return {
        "expected_static_file_count": len(expected_files),
        "observed_static_file_count": len(observed_files - expected_snapshot_files),
        "expected_snapshot_file_count": len(expected_snapshot_files),
        "snapshot_file_count": len(observed_files & expected_snapshot_files),
        "expected_static_directory_count": len(expected_directories),
        "observed_static_directory_count": len(observed_directories),
        "snapshot_nested_directory_count": 0,
        "unknown_file_count": 0,
        "unknown_directory_count": 0,
        "all_static_paths_exact": True,
        "snapshot_contents_validated_by_checkpoint_and_db_gates": True,
    }


def resolve_external_worker_interpreter(project_root: Path) -> Path:
    candidates = [
        Path(str(getattr(sys, "_base_executable", ""))),
        Path(sys.base_prefix) / ("python.exe" if os.name == "nt" else "bin/python"),
        Path(sys.executable),
    ]
    for candidate in candidates:
        if not str(candidate):
            continue
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError):
            continue
        if resolved != project_root and project_root not in resolved.parents:
            return resolved
    raise EvidenceError("No aggregate-verifiable worker interpreter exists outside project")


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceError(f"{label} must be a JSON object")
    return value


def resolve_project_path(project_root: Path, relative: str) -> Path:
    path = (project_root / relative).resolve()
    if path != project_root and project_root not in path.parents:
        raise EvidenceError(f"Path escapes project root: {relative}")
    return path


def read_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise EvidenceError(f"Invalid JSONL at {path}:{line_number}") from error
    return rows


def make_expected_record(case: Mapping[str, Any]) -> MemoryRecord:
    item = require_mapping(case.get("candidate_memory"), "candidate_memory")
    source = require_mapping(case.get("source_episode"), "source_episode")
    content = str(item.get("content", ""))
    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return MemoryRecord(
        memory_id=str(item.get("memory_id", "")),
        memory_type=str(item.get("memory_type", "")),
        content=content,
        provenance={
            "dataset": source.get("dataset"),
            "source_task_id": source.get("task_id"),
            "generator_or_scenario_id": source.get("generator_or_scenario_id"),
            "source_variation": source.get("variation"),
            "source_specs_sha256": source.get("specs_sha256"),
            "source_solution_sha256": source.get("source_solution_sha256"),
            "derivation": item.get("provenance"),
        },
        aliases=tuple(item.get("aliases", [])),
        retrieval_keys=tuple(item.get("retrieval_keys", [])),
        metadata={
            "policy_id": item.get("policy_id"),
            "summary": content,
            "graph_edges": [],
            "leakage_sentinel": (
                f"PM3A-SENTINEL::{item.get('memory_id')}::{content_sha256[:16]}"
            ),
        },
    )


def expected_public_projection(record: MemoryRecord) -> dict[str, Any]:
    return {
        "memory_id": record.memory_id,
        "memory_type": record.memory_type,
        "content": record.content,
        "aliases": list(record.aliases),
        "retrieval_keys": list(record.retrieval_keys),
        "metadata": {"policy_id": record.metadata["policy_id"]},
    }


def record_artifact_mapping(record: MemoryRecord) -> dict[str, Any]:
    """Return the exact JSON-native representation persisted by the runner.

    ``dataclasses.asdict`` preserves tuple fields, while JSON persistence turns
    them into arrays.  Recomputing an artifact contract must compare the
    serialized logical value, not Python's tuple-vs-list implementation detail.
    """

    value = json.loads(canonical_json(asdict(record)))
    if not isinstance(value, dict):
        raise EvidenceError("Canonical MemoryRecord artifact is not a mapping")
    return value


def load_frozen_contract(
    *, project_root: Path, config_path: Path, witnesses_path: Path
) -> dict[str, Any]:
    overlay = require_mapping(read_json(config_path), "isolated case config")
    if overlay.get("mechanism_claim") != "constructed deterministic selector-channel mechanism smoke":
        raise EvidenceError("Isolated config broadens the frozen mechanism claim")
    if overlay.get("semantic_memory_utility_claim_allowed") is not False:
        raise EvidenceError("Isolated config improperly enables a semantic-memory claim")
    base_relative = overlay.get("base_config_path")
    if not isinstance(base_relative, str):
        raise EvidenceError("Isolated config has no base_config_path")
    base = require_mapping(
        read_json(resolve_project_path(project_root, base_relative)), "base case config"
    )
    isolation = require_mapping(overlay.get("isolation"), "isolation config")
    configured_probes = isolation.get("required_denied_capability_probes")
    if not isinstance(configured_probes, list) or set(configured_probes) != REQUIRED_CAPABILITY_PROBES:
        raise EvidenceError("Config capability probe set differs from the frozen gate")
    if isolation.get("agent_input_fields") != [
        "type",
        "protocol_version",
        "target_instruction",
        "retrieval_results",
    ]:
        raise EvidenceError("Config Agent input contract is not the exact four-field wire")
    if (
        isolation.get("arbitrary_code_execution") is not False
        or isolation.get("windows_arbitrary_code_sandbox_claimed") is not False
        or isolation.get("os_filesystem_sandbox_claimed") is not False
    ):
        raise EvidenceError("Config makes an unsupported arbitrary-code/OS sandbox claim")
    allowed_by_case = require_mapping(
        isolation.get("allowed_tools_by_case"), "allowed_tools_by_case"
    )
    cases_raw = base.get("cases")
    if not isinstance(cases_raw, list):
        raise EvidenceError("Base config contains no cases")
    cases = {
        str(case.get("case_id")): require_mapping(case, "case")
        for case in cases_raw
        if isinstance(case, Mapping)
    }
    if set(cases) != set(CASE_IDS) or set(allowed_by_case) != set(CASE_IDS):
        raise EvidenceError("Frozen config must define exactly the three smoke cases")
    global_config = require_mapping(base.get("global"), "base global config")
    effective_global_config = dict(global_config)
    effective_global_config.update(
        require_mapping(overlay.get("global_overrides"), "global overrides")
    )
    witnesses_document = require_mapping(read_json(witnesses_path), "witnesses")
    witness_rows = witnesses_document.get("witnesses")
    if not isinstance(witness_rows, list):
        raise EvidenceError("Witness source contains no witnesses list")
    witnesses: dict[str, Mapping[str, Any]] = {}
    for row in witness_rows:
        if isinstance(row, Mapping) and row.get("case_id") in CASE_IDS:
            case_id = str(row["case_id"])
            if case_id in witnesses:
                raise EvidenceError(f"Duplicate witness for {case_id}")
            witnesses[case_id] = row
    if set(witnesses) != set(CASE_IDS):
        raise EvidenceError("Witness source does not bind exactly the three cases")

    contracts: dict[str, Any] = {}
    data_root = project_root / "third_step_a/appworld_root/data/tasks"
    for case_id in CASE_IDS:
        case = cases[case_id]
        source = require_mapping(case.get("source_episode"), f"{case_id}.source_episode")
        target = require_mapping(case.get("target_task"), f"{case_id}.target_task")
        source_root = data_root / str(source.get("task_id"))
        target_root = data_root / str(target.get("task_id"))
        source_specs = source_root / "specs.json"
        source_solution = source_root / "ground_truth/solution.py"
        target_specs = target_root / "specs.json"
        target_test = target_root / "ground_truth/test_data.json"
        target_evaluation = target_root / "ground_truth/evaluation.py"
        if sha256_file(source_specs) != source.get("specs_sha256"):
            raise EvidenceError(f"{case_id} source specs hash mismatch")
        if sha256_file(source_solution) != source.get("source_solution_sha256"):
            raise EvidenceError(f"{case_id} source solution hash mismatch")
        if sha256_file(target_specs) != target.get("specs_sha256"):
            raise EvidenceError(f"{case_id} target specs hash mismatch")
        gold = require_mapping(case.get("gold_state_evaluator"), f"{case_id}.gold")
        if sha256_file(target_test) != gold.get("test_data_sha256"):
            raise EvidenceError(f"{case_id} target evaluator test-data hash mismatch")
        if sha256_file(target_evaluation) != gold.get("evaluation_code_sha256"):
            raise EvidenceError(f"{case_id} target evaluator code hash mismatch")
        target_specs_document = require_mapping(read_json(target_specs), "target specs")
        instruction = target_specs_document.get("instruction")
        if not isinstance(instruction, str) or not instruction:
            raise EvidenceError(f"{case_id} target specs contain no instruction")
        tools = allowed_by_case[case_id]
        if not isinstance(tools, list) or not tools or any(
            not isinstance(tool, str) or tool.count(".") != 1 for tool in tools
        ):
            raise EvidenceError(f"{case_id} exact public tool allowlist is malformed")
        record = make_expected_record(case)
        contracts[case_id] = {
            "case": case,
            "record": record,
            "record_mapping": record_artifact_mapping(record),
            "public_projection": expected_public_projection(record),
            "target_instruction": instruction,
            "allowed_tools": sorted(tools),
            "witness": witnesses[case_id],
            "state_checkpoint_id": global_config.get("state_checkpoint_id"),
            "classification": case.get("case_class"),
            "agent_model": effective_global_config.get("agent_model"),
            "agent_model_type": effective_global_config.get("agent_model_type"),
            "seed": effective_global_config.get("seed"),
            "severe_threshold": require_mapping(
                global_config.get("severity_rubric"), "severity rubric"
            ).get("severe_threshold"),
            "appworld_code_version": global_config.get("appworld_code_version"),
            "config_relative_path": config_path.relative_to(project_root).as_posix(),
            "base_config_relative_path": str(base_relative),
            "witnesses_relative_path": witnesses_path.relative_to(project_root).as_posix(),
            "prompt_relative_path": require_mapping(
                overlay.get("global_overrides"), "global overrides"
            ).get("prompt_path"),
        }
    return {
        "mechanism_claim": overlay["mechanism_claim"],
        "probe_ids": sorted(configured_probes),
        "contracts": contracts,
    }


def validate_execution_freeze(
    freeze: Mapping[str, Any],
    *,
    freeze_path: Path,
    project_root: Path,
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
        raise EvidenceError("Execution freeze schema/status/claim/Pilot contract mismatch")
    if freeze.get("primary_evidence_run") != run_root.name:
        raise EvidenceError("Execution freeze binds a different run id")
    expected_run = resolve_project_path(project_root, str(freeze.get("must_precede_run", "")))
    if expected_run != run_root:
        raise EvidenceError("Execution freeze binds a different run root")
    if not str(freeze.get("status", "")).startswith("FROZEN_BEFORE_"):
        raise EvidenceError("Execution freeze is not marked as pre-run")
    files = freeze.get("files")
    if not isinstance(files, Mapping) or not files:
        raise EvidenceError("Execution freeze has no frozen files")
    config_relative = freeze.get("case_config")
    base_relative = freeze.get("base_config")
    environment_relative = freeze.get("environment_spec")
    if not all(
        isinstance(value, str) and value
        for value in (config_relative, base_relative, environment_relative)
    ):
        raise EvidenceError("Execution freeze omits config/base/environment paths")
    config_path = resolve_project_path(project_root, str(config_relative))
    overlay = require_mapping(read_json(config_path), "freeze case config")
    if overlay.get("base_config_path") != base_relative:
        raise EvidenceError("Execution freeze base config differs from config overlay")
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
        raise EvidenceError("Execution freeze file set is under/over-inclusive")
    if freeze.get("file_count") != len(required_relatives):
        raise EvidenceError("Execution freeze file_count mismatch")
    checks: list[dict[str, Any]] = []
    for relative, expected in sorted(files.items()):
        path = resolve_project_path(project_root, str(relative))
        actual = sha256_file(path) if path.is_file() else None
        checks.append(
            {
                "path": str(relative),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "equal": actual == expected,
            }
        )
    failed = [row["path"] for row in checks if not row["equal"]]
    if failed:
        raise EvidenceError(f"Execution freeze file mismatch: {failed}")
    return {
        "freeze_path": freeze_path.relative_to(project_root).as_posix(),
        "freeze_sha256": sha256_file(freeze_path),
        "freeze_id": freeze.get("execution_freeze_id"),
        "file_count": len(checks),
        "all_files_equal": True,
        "checks": checks,
    }


def tree_attestation(path: Path) -> dict[str, Any]:
    entries = tree_entries(path)
    return {
        "directory": path.name,
        "file_count": len(entries),
        "total_bytes": sum(item["size"] for item in entries),
        "tree_manifest_root_sha256": manifest_root_sha256(entries),
        "entries": entries,
    }


def validate_run_environment(
    run_root: Path,
    *,
    project_root: Path,
    freeze_result: Mapping[str, Any],
    attestation_result: Mapping[str, Any],
    case_contract: Mapping[str, Any],
) -> dict[str, Any]:
    environment = require_mapping(read_json(run_root / "environment.json"), "run environment")
    import appworld

    module_path = Path(appworld.__file__).resolve()
    direct_url_text = importlib.metadata.distribution("appworld").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        raise EvidenceError("Run environment AppWorld has no direct_url.json")
    dependencies: dict[str, str] = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            dependencies[str(name)] = distribution.version
    dependencies = {
        name: dependencies[name] for name in sorted(dependencies, key=str.casefold)
    }
    appworld_root = project_root / "third_step_a/appworld_root"
    expected = {
        "python": sys.version,
        "python_executable_sha256": sha256_file(Path(sys.executable)),
        "platform": platform.platform(),
        "appworld_version": appworld.__version__,
        "appworld_module_relative_path": module_path.relative_to(project_root).as_posix(),
        "appworld_module_file_sha256": sha256_file(module_path),
        "appworld_distribution_direct_url_sha256": hashlib.sha256(
            direct_url_text.encode("utf-8")
        ).hexdigest(),
        "appworld_data_version": (appworld_root / "data/version.txt")
        .read_text(encoding="utf-8")
        .strip(),
        "execution_freeze_id": freeze_result["freeze_id"],
        "execution_freeze_sha256": freeze_result["freeze_sha256"],
        "precommit_nonce_commitment_sha256": attestation_result[
            "nonce_commitment_sha256"
        ],
        "isolated_config_sha256": sha256_file(
            resolve_project_path(project_root, case_contract["config_relative_path"])
        ),
        "agent_prompt_sha256": sha256_file(
            resolve_project_path(project_root, case_contract["prompt_relative_path"])
        ),
        "dependencies": dependencies,
        "controller_environment": {
            "APPWORLD_ROOT": "third_step_a/appworld_root",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "PYTHONWARNINGS": "ignore",
        },
        "pilot_started": False,
    }
    if environment != expected:
        differing = sorted(
            key
            for key in set(environment) | set(expected)
            if environment.get(key) != expected.get(key)
        )
        raise EvidenceError(f"Run environment differs from live/frozen environment: {differing}")
    return {
        "environment_file_sha256": sha256_file(run_root / "environment.json"),
        "dependency_count": len(dependencies),
        "appworld_module_bound_to_attested_source": True,
        "controller_environment_recomputed": True,
        "pilot_started": False,
    }


def _line_counter(path: Path) -> Counter[bytes]:
    if not path.is_file():
        return Counter()
    return Counter(line for line in path.read_bytes().splitlines() if line)


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
        left_sha256 = sha256_file(left_path) if left_path is not None else None
        right_sha256 = sha256_file(right_path) if right_path is not None else None
        row: dict[str, Any] = {
            "file": name,
            "left_sha256": left_sha256,
            "right_sha256": right_sha256,
            "byte_equal": left_sha256 == right_sha256,
        }
        if name.endswith(".jsonl"):
            left_rows = _line_counter(left_path) if left_path is not None else Counter()
            right_rows = _line_counter(right_path) if right_path is not None else Counter()
            row["removed_count"] = sum((left_rows - right_rows).values())
            row["added_count"] = sum((right_rows - left_rows).values())
        files.append(row)
    left_tree_root = tree_attestation(left)["tree_manifest_root_sha256"]
    right_tree_root = tree_attestation(right)["tree_manifest_root_sha256"]
    return {
        "left_tree_manifest_root_sha256": left_tree_root,
        "right_tree_manifest_root_sha256": right_tree_root,
        "all_files_byte_equal": left_tree_root == right_tree_root
        and all(row["byte_equal"] for row in files),
        "files": files,
    }


def locate_unique_file(root: Path, name: str) -> Path:
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise EvidenceError(f"Expected exactly one {name} under {root}, found {len(matches)}")
    return matches[0]


def locate_checkpoint_directory(branch_root: Path) -> Path:
    direct = branch_root / "checkpoint_snapshot"
    if direct.is_dir():
        return direct
    legacy = branch_root / "appworld_output_snapshot/checkpoints"
    children = sorted(path for path in legacy.glob("*") if path.is_dir()) if legacy.is_dir() else []
    if len(children) == 1:
        return children[0]
    raise EvidenceError(f"Missing unique checkpoint snapshot under {branch_root}")


def locate_frozen_db_directory(branch_root: Path) -> Path:
    candidates = (
        branch_root / "db_snapshot_frozen",
        branch_root / "dbs_frozen",
        branch_root / "appworld_output_snapshot/dbs",
    )
    existing = [path for path in candidates if path.is_dir()]
    if len(existing) != 1:
        raise EvidenceError(f"Missing unique frozen DB snapshot under {branch_root}")
    return existing[0]


def evaluator_semantic_vector(value: Any, label: str) -> dict[str, Any]:
    vector = require_mapping(value, label)
    if set(vector) != {"difficulty", "failures", "num_tests", "passes", "success"}:
        raise EvidenceError(f"{label} official vector schema is not exact")
    passes = vector.get("passes")
    failures = vector.get("failures")
    if not isinstance(passes, list) or not isinstance(failures, list):
        raise EvidenceError(f"{label} must contain pass/failure lists")
    projected_passes: list[dict[str, Any]] = []
    projected_failures: list[dict[str, Any]] = []
    for index, row_raw in enumerate(passes):
        row = require_mapping(row_raw, f"{label}.passes[{index}]")
        if set(row) != {"label", "requirement"}:
            raise EvidenceError(f"{label} pass row schema is not exact")
        projected_passes.append(dict(row))
    for index, row_raw in enumerate(failures):
        row = require_mapping(row_raw, f"{label}.failures[{index}]")
        if set(row) != {"label", "requirement", "trace"} or not isinstance(
            row.get("trace"), str
        ):
            raise EvidenceError(f"{label} failure row schema is not exact")
        projected_failures.append(
            {"label": row["label"], "requirement": row["requirement"]}
        )
    return {
        "difficulty": vector["difficulty"],
        "success": vector["success"],
        "num_tests": vector["num_tests"],
        "passes": sorted(projected_passes, key=canonical_json),
        "failures": sorted(projected_failures, key=canonical_json),
    }


def validate_evaluator_vector(value: Any, label: str) -> dict[str, Any]:
    vector = require_mapping(value, label)
    semantic = evaluator_semantic_vector(vector, label)
    if not isinstance(vector.get("success"), bool):
        raise EvidenceError(f"{label}.success must be boolean")
    if not isinstance(vector.get("num_tests"), int) or vector["num_tests"] < 1:
        raise EvidenceError(f"{label}.num_tests must be positive")
    passes = vector.get("passes")
    failures = vector.get("failures")
    if not isinstance(passes, list) or not isinstance(failures, list):
        raise EvidenceError(f"{label} must contain passes/failures vectors")
    if len(passes) + len(failures) != vector["num_tests"]:
        raise EvidenceError(f"{label} vector length does not equal num_tests")
    if vector["success"] is not (len(failures) == 0 and len(passes) == vector["num_tests"]):
        raise EvidenceError(f"{label}.success is inconsistent with passes/failures")
    serialized_items = [
        canonical_json(item) for item in [*semantic["passes"], *semantic["failures"]]
    ]
    if len(serialized_items) != len(set(serialized_items)):
        raise EvidenceError(f"{label} contains duplicate pass/failure vector items")
    return {
        "success": vector["success"],
        "num_tests": vector["num_tests"],
        "passed": len(passes),
        "failed": len(failures),
        "vector_sha256": hashlib.sha256(canonical_json(vector).encode("utf-8")).hexdigest(),
        "semantic_vector_sha256": hashlib.sha256(
            canonical_json(semantic).encode("utf-8")
        ).hexdigest(),
    }


def recompute_capability_probes(
    value: Any, label: str, *, branch_root: Path
) -> dict[str, Any]:
    document = require_mapping(value, label)
    expected_document_keys = {
        "protocol_version",
        "execution_role",
        "boundary_claim",
        "probe_count",
        "required_probe_count",
        "all_pass",
        "worker_verified_all_denied",
        "probes",
        "transcript_row_count",
        "transcript_virtual_sha256",
        "process_attestation",
        "transcript_file",
        "transcript_file_sha256",
    }
    if set(document) != expected_document_keys:
        raise EvidenceError(f"{label} capability document has missing/extra fields")
    transcript_path = branch_root / "capability_probe_rpc_transcript.jsonl"
    transcript = read_jsonl(transcript_path)
    if len(transcript) != len(CAPABILITY_PROBES) + 1:
        raise EvidenceError(f"{label} capability RPC transcript is not 10 requests plus final")
    expected_names: list[str] = []
    for index, (name, app, api, arguments) in enumerate(CAPABILITY_PROBES, start=1):
        expected_names.append(name)
        row = require_mapping(transcript[index - 1], f"{label} transcript[{index - 1}]")
        request_id = f"probe-{index:04d}-{name}"
        expected_request = {
            "type": "tool_call",
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "app": app,
            "api": api,
            "arguments": arguments,
        }
        expected_response = {
            "type": "tool_result",
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "ok": False,
            "result": {
                "error_code": "CAPABILITY_DENIED",
                "error_type": "CapabilityDeniedError",
            },
        }
        if row != {"request": expected_request, "response": expected_response}:
            raise EvidenceError(f"{label} transcript probe {name} was not exactly denied")
    expected_final = {
        "type": "final",
        "protocol_version": PROTOCOL_VERSION,
        "ok": True,
        "result": {
            "all_denied": True,
            "probe_count": len(expected_names),
            "probe_names": expected_names,
        },
    }
    if transcript[-1] != {"final": expected_final}:
        raise EvidenceError(f"{label} worker final message is not exact")
    transcript_sha256 = sha256_file(transcript_path)
    if (
        document.get("protocol_version") != PROTOCOL_VERSION
        or document.get("execution_role")
        != "separate_agent_role_capability_probe_worker"
        or document.get("boundary_claim")
        != "structured JSONL tool capability boundary only"
        or document.get("probe_count") != len(CAPABILITY_PROBES)
        or document.get("required_probe_count") != len(CAPABILITY_PROBES)
        or document.get("all_pass") is not True
        or document.get("worker_verified_all_denied") is not True
        or document.get("transcript_file") != transcript_path.name
        or document.get("transcript_file_sha256") != transcript_sha256
        or document.get("transcript_virtual_sha256") != transcript_sha256
        or document.get("transcript_row_count") != len(transcript)
    ):
        raise EvidenceError(f"{label} transcript/hash binding failed")
    probes = document.get("probes")
    if not isinstance(probes, list):
        raise EvidenceError(f"{label}.probes must be a list")
    rows: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(probes):
        row = require_mapping(item, f"{label}.probes[{index}]")
        probe_id = row.get("probe")
        if not isinstance(probe_id, str) or not probe_id:
            raise EvidenceError(f"{label}.probes[{index}] has no probe name")
        if probe_id in rows:
            raise EvidenceError(f"Duplicate capability probe: {probe_id}")
        rows[probe_id] = row
    missing = sorted(REQUIRED_CAPABILITY_PROBES - rows.keys())
    extra = sorted(rows.keys() - REQUIRED_CAPABILITY_PROBES)
    if missing or extra:
        raise EvidenceError(f"Capability probe set mismatch; missing={missing}, extra={extra}")
    failed = sorted(
        probe_id
        for probe_id, row in rows.items()
        if row.get("denied") is not True or row.get("result") != "PASS"
    )
    if failed:
        raise EvidenceError(f"Capability probes did not fail closed: {failed}")
    for index, (name, app, api, _arguments) in enumerate(CAPABILITY_PROBES):
        expected_probe_row = {
            "probe": name,
            "agent_role_request": {"app": app, "api": api},
            "protocol_request_exact": True,
            "response_error_code": "CAPABILITY_DENIED",
            "protocol_error": "CAPABILITY_DENIED",
            "result": "PASS",
            "denied": True,
        }
        if probes[index] != expected_probe_row:
            raise EvidenceError(f"Capability summary row is not exact for {name}")
    process = require_mapping(document.get("process_attestation"), f"{label} process")
    process_file = require_mapping(
        read_json(branch_root / "capability_process_attestation.json"),
        f"{label} process file",
    )
    if process != process_file:
        raise EvidenceError(f"{label} process attestations differ")
    expected_worker_sha = sha256_file(
        Path(__file__).resolve().parent / "isolated_capability_probe_worker.py"
    )
    external_interpreter = resolve_external_worker_interpreter(
        Path(__file__).resolve().parents[2]
    )
    argv = process.get("argv")
    process_pid = process.get("pid")
    process_cwd = process.get("cwd")
    if set(process) != CAPABILITY_PROCESS_ATTESTATION_KEYS:
        raise EvidenceError(f"{label} capability process has missing/extra fields")
    if (
        process.get("role") != "agent_capability_probe"
        or not isinstance(process_pid, int)
        or process_pid <= 0
        or process.get("return_code") != 0
        or process.get("exit_code") != 0
        or process.get("stderr_empty") is not True
        or process.get("stderr_sha256") != hashlib.sha256(b"").hexdigest()
        or process.get("boundary") != "structured_json_tool_call_rpc"
        or process.get("structured_tool_boundary_only") is not True
        or process.get("arbitrary_code_sandbox_claimed") is not False
        or process.get("os_filesystem_sandbox_claimed") is not False
        or process.get("worker_copied_to_fresh_external_sandbox") is not True
        or process.get("worker_copied_to_temporary_directory") is not True
        or process.get("python_isolated_flag") is not True
        or process.get("source_copy_hash_equal") is not True
        or process.get("interpreter_outside_project") is not True
        or process.get("interpreter_sha256") != sha256_file(external_interpreter)
        or process.get("source_worker_sha256") != expected_worker_sha
        or process.get("copied_worker_sha256") != expected_worker_sha
        or process.get("environment_key_names") != sorted(WORKER_ENVIRONMENT_KEYS)
        or process.get("project_root_path_disclosed") is not False
        or process.get("argv_contains_project_path") is not False
        or process.get("cwd_contains_project_path") is not False
        or process.get("worker_command_contains_project_path") is not False
        or process.get("appworld_imported_by_worker") is not False
        or not isinstance(process_cwd, str)
        or not re.fullmatch(r"preempt3a-probe-[0-9a-f]{32}", process_cwd)
        or process.get("rpc_transcript_file_sha256") != transcript_sha256
        or process.get("rpc_transcript_row_count") != len(transcript)
        or not isinstance(argv, list)
        or len(argv) != 3
        or argv[0] != external_interpreter.name
        or argv[1:] != ["-I", "capability_probe_worker.py"]
        or any("/" in str(item) or "\\" in str(item) for item in argv)
    ):
        raise EvidenceError(f"{label} separate capability worker boundary failed")
    return {
        "probe_count": len(rows),
        "required_probe_ids": sorted(REQUIRED_CAPABILITY_PROBES),
        "all_denied_recomputed": True,
        "probe_evidence_sha256": {
            probe_id: hashlib.sha256(canonical_json(rows[probe_id]).encode("utf-8")).hexdigest()
            for probe_id in sorted(rows)
        },
        "rpc_transcript_file_sha256": transcript_sha256,
        "capability_worker_pid": process.get("pid"),
    }


def recompute_eviction_manifest(
    value: Any,
    label: str,
    *,
    expected_record: MemoryRecord,
) -> dict[str, Any]:
    document = require_mapping(value, label)
    independent_store = AuditMemoryStore()
    independent_store.put(expected_record)
    independent_store.delete(expected_record.memory_id)
    independently_recomputed = independent_store.effective_eviction_manifest(
        expected_record
    )
    if canonical_json(document) != canonical_json(independently_recomputed):
        raise EvidenceError(
            f"{label} differs from the complete independently recomputed manifest"
        )
    checks = document.get("checks")
    if not isinstance(checks, list) or len(checks) < 15:
        raise EvidenceError(f"{label} requires at least 15 concrete checks")
    surfaces: set[str] = set()
    failed: list[str] = []
    for index, item in enumerate(checks):
        row = require_mapping(item, f"{label}.checks[{index}]")
        surface = row.get("surface")
        if not isinstance(surface, str) or not surface:
            raise EvidenceError(f"{label}.checks[{index}] has no surface")
        if surface in surfaces:
            raise EvidenceError(f"Duplicate eviction surface: {surface}")
        surfaces.add(surface)
        matched = row.get("matched_forbidden_needles", [])
        if row.get("result") != "PASS" or matched not in ([], None):
            failed.append(surface)
    if failed:
        raise EvidenceError(f"Effective eviction checks failed: {failed}")
    expected_core_checks = independently_recomputed["checks"]
    expected_surface_names = {
        row["surface"] for row in expected_core_checks
    }
    if not expected_surface_names.issubset(surfaces):
        raise EvidenceError(f"{label} omits one or more concrete eviction components")
    return {
        "check_count": len(checks),
        "surfaces": sorted(surfaces),
        "all_pass_recomputed": document.get("all_pass") is True,
        "core_check_count_independently_recomputed": len(expected_core_checks),
    }


def recursive_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(recursive_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(recursive_keys(item))
    return keys


def validate_agent_request(value: Any, label: str) -> Mapping[str, Any]:
    request = require_mapping(value, label)
    extra = sorted(set(request) - ALLOWED_AGENT_REQUEST_KEYS)
    if extra:
        raise EvidenceError(f"Agent request has non-whitelisted top-level keys: {extra}")
    missing = sorted(ALLOWED_AGENT_REQUEST_KEYS - set(request))
    if missing:
        raise EvidenceError(f"Agent request missing keys: {missing}")
    forbidden_keys = _forbidden_agent_key_findings(request, path="$agent_request")
    if forbidden_keys:
        raise EvidenceError(
            f"Agent request exposes {len(forbidden_keys)} private/controller keys"
        )
    if not isinstance(request["target_instruction"], str):
        raise EvidenceError("Agent target instruction must be text")
    if not isinstance(request["retrieval_results"], list):
        raise EvidenceError("Agent retrieval_results must be a list")
    if not isinstance(request["allowed_tools"], list) or not request["allowed_tools"]:
        raise EvidenceError("Agent request must contain a non-empty exact AppWorld tool allowlist")
    if any(
        not isinstance(tool, str) or tool.count(".") != 1
        for tool in request["allowed_tools"]
    ):
        raise EvidenceError("Agent request contains a malformed exact AppWorld tool name")
    return request


def treatment_blind_request(request: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(request)
    normalized["retrieval_results"] = "<TREATMENT>"
    normalized["retrieval_results_sha256"] = "<TREATMENT>"
    return normalized


def _iter_nontrivial_strings(value: Any, *, path: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            rows.extend(_iter_nontrivial_strings(child, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(_iter_nontrivial_strings(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and len(value.strip()) >= 12:
        rows.append((path, value))
    return rows


def _forbidden_agent_key_findings(
    value: Any,
    *,
    path: str,
    _components: tuple[str | int, ...] | None = None,
) -> list[dict[str, str]]:
    """Recursively reject private/controller keys independent of value type."""

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
            forbidden = normalized in FORBIDDEN_AGENT_EXACT_KEYS or any(
                part in normalized for part in FORBIDDEN_AGENT_KEY_PARTS
            )
            if forbidden and not _allowed_public_api_schema_key(normalized, components):
                findings.append(
                    {
                        "path": f"{path}.{key_text}",
                        "key_sha256": hashlib.sha256(
                            key_text.encode("utf-8")
                        ).hexdigest(),
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


def _private_needle_partition(
    *, public: Any, private_sources: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public_values = {
        value for _, value in _iter_nontrivial_strings(public, path="$public")
    }
    private_values: dict[str, set[str]] = {}
    excluded_values: dict[str, set[str]] = {}
    for source_name, source in private_sources.items():
        for source_path, value in _iter_nontrivial_strings(
            source, path=f"${source_name}"
        ):
            destination = excluded_values if value in public_values else private_values
            destination.setdefault(value, set()).add(source_path)
    needles = [
        {
            "value": value,
            "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "length": len(value),
            "source_paths": sorted(paths),
        }
        for value, paths in sorted(private_values.items())
    ]
    exclusions = [
        {
            "value": value,
            "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "length": len(value),
            "source_paths": sorted(paths),
        }
        for value, paths in sorted(excluded_values.items())
    ]
    return needles, exclusions


def recompute_case_firewall(
    case_root: Path,
    *,
    case_id: str,
    case_contract: Mapping[str, Any],
    branch_results: Mapping[str, Mapping[str, Any]],
    run_nonce: str,
) -> dict[str, Any]:
    case = case_contract["case"]
    expected_relationship = {
        "target": case["target_task"],
        "source_to_target_dependency": case["source_to_target_dependency"],
        "need_definition": case["need_definition"],
        "need_label": case["need_label"],
        "gold_state_evaluator": case["gold_state_evaluator"],
        "severity_application": case["severity_application"],
    }
    relationship = require_mapping(
        read_json(case_root / "target_relationship.json"), "target relationship"
    )
    witness = require_mapping(read_json(case_root / "witness.json"), "witness")
    if relationship != expected_relationship or witness != case_contract["witness"]:
        raise EvidenceError(f"{case_id} private relationship/witness differs from frozen inputs")
    caller_secret = "PM3AR-CALLER-SECRET::" + hashlib.sha256(
        f"{run_nonce}\x00{case_id}\x00caller".encode("utf-8")
    ).hexdigest()
    canaries: dict[str, Mapping[str, str]] = {}
    for branch in BRANCHES:
        expected = {
            "caller_secret": caller_secret,
            "branch_canary": "PM3AR-BRANCH-CANARY::"
            + hashlib.sha256(
                f"{run_nonce}\x00{case_id}\x00{branch}\x00branch".encode("utf-8")
            ).hexdigest(),
            "created_role": "pre-Agent controller-only firewall canary",
        }
        actual = require_mapping(
            read_json(case_root / branch.lower() / "post_agent_controller_canaries.json"),
            f"{branch} controller canaries",
        )
        if actual != expected:
            raise EvidenceError(f"{case_id}/{branch} controller canary mismatch")
        canaries[branch] = actual

    raw_private_sources = {
        "target_relationship": relationship,
        "witness": witness,
        "controller_canaries": canaries,
    }
    raw_scan_path = case_root / "raw_controller_firewall_scan.json"
    raw_scan = require_mapping(read_json(raw_scan_path), "raw controller firewall scan")
    if (
        raw_scan.get("schema_version")
        != "preempt-mem-3a-r-raw-controller-firewall-scan-v2"
        or raw_scan.get("total_private_exact_match_count") != 0
        or raw_scan.get("total_forbidden_private_key_count") != 0
        or raw_scan.get("raw_payloads_written_to_disk") is not False
        or raw_scan.get("raw_payloads_discarded_after_scan") is not True
        or raw_scan.get("all_pass") is not True
    ):
        raise EvidenceError(f"{case_id} raw pre-redaction firewall commitment mismatch")
    raw_branch_rows = raw_scan.get("branch_scans")
    if not isinstance(raw_branch_rows, list) or len(raw_branch_rows) != 3:
        raise EvidenceError(f"{case_id} raw firewall scan lacks three branches")
    raw_by_branch = {
        str(require_mapping(row, "raw branch scan").get("branch")): row
        for row in raw_branch_rows
    }
    if set(raw_by_branch) != set(BRANCHES):
        raise EvidenceError(f"{case_id} raw firewall branch set mismatch")
    for branch in BRANCHES:
        row = raw_by_branch[branch]
        expected_retrieval = (
            [] if branch == "Evicted" else [case_contract["public_projection"]]
        )
        branch_public = {
            "target_instruction": case_contract["target_instruction"],
            "public_retrieval_records": expected_retrieval,
        }
        raw_needles, raw_exclusions = _private_needle_partition(
            public=branch_public, private_sources=raw_private_sources
        )
        expected_raw_needles = [
            {
                "value_sha256": needle["value_sha256"],
                "source_paths": needle["source_paths"],
            }
            for needle in raw_needles
        ]
        redaction_attestation = require_mapping(
            read_json(case_root / branch.lower() / "api_log_redaction_attestation.json"),
            "redaction attestation",
        )
        if (
            row.get("raw_transcript_virtual_sha256")
            != redaction_attestation.get("raw_file_sha256")
            or not _HEX_64_RE.fullmatch(str(row.get("raw_virtual_payload_sha256", "")))
            or row.get("private_exact_match_count") != 0
            or row.get("matches") != []
            or row.get("forbidden_private_key_count") != 0
            or row.get("forbidden_private_key_findings") != []
            or row.get("private_needles") != expected_raw_needles
            or row.get("private_needle_count") != len(expected_raw_needles)
            or row.get("public_overlap_exclusion_count") != len(raw_exclusions)
            or row.get("public_overlap_exclusion_sha256s")
            != sorted(item["value_sha256"] for item in raw_exclusions)
        ):
            raise EvidenceError(f"{case_id}/{branch} raw firewall scan/hash mismatch")

    persisted_private_sources = {
        **raw_private_sources,
        "severity": {
            branch: {
                "severity": branch_results[branch].get("severity"),
                "severity_reason": branch_results[branch].get("severity_reason"),
            }
            for branch in BRANCHES
        },
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
    expected_partitions: list[dict[str, Any]] = []
    total_private_needles = 0
    for branch in BRANCHES:
        expected_retrieval = (
            [] if branch == "Evicted" else [case_contract["public_projection"]]
        )
        branch_public = {
            "target_instruction": case_contract["target_instruction"],
            "public_retrieval_records": expected_retrieval,
        }
        needles, exclusions = _private_needle_partition(
            public=branch_public, private_sources=persisted_private_sources
        )
        total_private_needles += len(needles)
        expected_partitions.append(
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
                    json.loads(line) for line in text.splitlines() if line.strip()
                ]
            else:
                structured = None
            key_findings = (
                _forbidden_agent_key_findings(structured, path=f"${name}")
                if structured is not None
                else []
            )
            if matches or key_findings:
                raise EvidenceError(f"{case_id}/{branch}/{name} contains controller-private input")
            scans.append(
                {
                    "branch": branch,
                    "surface": name,
                    "surface_file_sha256": sha256_file(path),
                    "private_exact_match_count": 0,
                    "matches": [],
                    "forbidden_private_key_count": 0,
                    "forbidden_private_key_findings": [],
                }
            )
    manifest = require_mapping(
        read_json(case_root / "firewall_leakage_manifest.json"), "firewall manifest"
    )
    raw_summary = require_mapping(
        manifest.get("raw_controller_firewall_scan"), "raw firewall summary"
    )
    if (
        manifest.get("schema_version") != "preempt-mem-3a-r-firewall-leakage-v2"
        or manifest.get("branch_partitions") != expected_partitions
        or manifest.get("surface_scans") != scans
        or manifest.get("surface_scan_count") != len(scans)
        or manifest.get("total_private_exact_match_count") != 0
        or manifest.get("total_forbidden_private_key_count") != 0
        or manifest.get("all_pass") is not True
        or raw_summary.get("file_sha256") != sha256_file(raw_scan_path)
        or raw_summary.get("branch_scans") != raw_branch_rows
        or raw_summary.get("total_forbidden_private_key_count") != 0
        or raw_summary.get("all_pass") is not True
    ):
        raise EvidenceError(f"{case_id} persisted firewall manifest is not independently reproducible")
    return {
        "pre_redaction_private_match_count": 0,
        "pre_redaction_forbidden_private_key_count": 0,
        "persisted_surface_private_match_count": 0,
        "persisted_surface_forbidden_private_key_count": 0,
        "private_needle_count_across_branch_partitions": total_private_needles,
        "surface_scan_count": len(scans),
        "canaries_existed_pre_agent_and_match_nonce": True,
        "raw_payloads_not_persisted": True,
    }


def validate_hash_contract(branch_root: Path, branch_result: Mapping[str, Any]) -> dict[str, Any]:
    prompt_path = branch_root / "prompt.txt"
    plan_path = branch_root / "structured_agent_plan.json"
    if not prompt_path.is_file() or not plan_path.is_file():
        raise EvidenceError(f"Missing prompt or structured agent plan under {branch_root}")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    plan_text = plan_path.read_text(encoding="utf-8")
    actual = {
        "prompt_logical_lf_sha256": logical_lf_sha256(prompt_text),
        "prompt_file_sha256": sha256_file(prompt_path),
        "structured_agent_plan_logical_lf_sha256": logical_lf_sha256(plan_text),
        "structured_agent_plan_file_sha256": sha256_file(plan_path),
    }
    for key, digest in actual.items():
        if branch_result.get(key) != digest:
            raise EvidenceError(f"Logical/file hash mismatch {branch_root.name}:{key}")
    return actual


def validate_process_boundaries(
    branch_root: Path,
    *,
    request_path: Path,
    initialize_path: Path,
    transcript_path: Path,
    capability_path: Path,
    capability_transcript_path: Path,
    evaluator_first_path: Path,
    evaluator_second_path: Path,
    db_attestation: Mapping[str, Any],
    db_tree: Mapping[str, Any],
    expected_task_id: str,
    expected_experiment_name: str,
    expected_appworld_version: str,
    expected_nonce_commitment_sha256: str,
    expected_rpc_redaction_count: int,
) -> dict[str, Any]:
    agent = require_mapping(
        read_json(branch_root / "agent_process_attestation.json"), "agent process attestation"
    )
    evaluator = require_mapping(
        read_json(branch_root / "evaluator_process_attestation.json"),
        "evaluator process attestation",
    )
    if set(agent) != AGENT_PROCESS_ATTESTATION_KEYS:
        raise EvidenceError(
            f"Agent process attestation has missing/extra fields under {branch_root}"
        )
    if set(evaluator) != EVALUATOR_PROCESS_ATTESTATION_KEYS:
        raise EvidenceError(
            f"Evaluator process attestation has missing/extra fields under {branch_root}"
        )
    empty_sha256 = hashlib.sha256(b"").hexdigest()
    external_interpreter = resolve_external_worker_interpreter(
        Path(__file__).resolve().parents[2]
    )
    agent_pid = agent.get("pid")
    agent_cwd = agent.get("cwd")
    if (
        agent.get("role") != "agent"
        or not isinstance(agent_pid, int)
        or agent_pid <= 0
        or agent.get("return_code") != 0
        or agent.get("exit_code") != 0
        or agent.get("stderr_empty") is not True
        or agent.get("stderr_sha256") != empty_sha256
        or agent.get("boundary") != "structured_json_tool_call_rpc"
        or agent.get("security_scope")
        != "trusted copied structured-tool worker; not a general Windows arbitrary-code sandbox"
        or agent.get("ground_truth_loaded") is not False
        or agent.get("project_path_disclosed") is not False
        or agent.get("no_project_tool_capability") is not True
        or agent.get("controller_state_disclosed") is not False
        or agent.get("no_controller_state_tool_capability") is not True
        or agent.get("windows_arbitrary_code_sandbox_claimed") is not False
        or agent.get("structured_tool_boundary_only") is not True
        or agent.get("arbitrary_code_sandbox_claimed") is not False
        or agent.get("os_filesystem_sandbox_claimed") is not False
        or agent.get("appworld_imported_by_worker") is not False
        or agent.get("worker_copied_to_fresh_external_sandbox") is not True
        or agent.get("worker_copied_to_temporary_directory") is not True
        or agent.get("python_isolated_flag") is not True
        or agent.get("source_copy_hash_equal") is not True
        or agent.get("source_worker_sha256") != agent.get("copied_worker_sha256")
        or agent.get("interpreter_outside_project") is not True
        or agent.get("interpreter_sha256") != sha256_file(external_interpreter)
        or agent.get("environment_key_names") != sorted(WORKER_ENVIRONMENT_KEYS)
        or agent.get("argv_contains_project_path") is not False
        or agent.get("cwd_contains_project_path") is not False
        or agent.get("worker_command_contains_project_path") is not False
        or agent.get("project_root_path_disclosed") is not False
        or not isinstance(agent_cwd, str)
        or not re.fullmatch(r"preempt3a-agent-[0-9a-f]{32}", agent_cwd)
    ):
        raise EvidenceError(f"Agent process boundary attestation failed under {branch_root}")
    argv = agent.get("argv")
    if (
        not isinstance(argv, list)
        or len(argv) != 3
        or argv[0] != external_interpreter.name
        or argv[1:] != ["-I", "structured_agent_worker.py"]
        or any("/" in str(item) or "\\" in str(item) for item in argv)
    ):
        raise EvidenceError(f"Agent worker argv discloses a path or differs from contract under {branch_root}")
    expected_agent_worker_sha = sha256_file(
        Path(__file__).resolve().parent / "isolated_agent_worker.py"
    )
    if agent.get("source_worker_sha256") != expected_agent_worker_sha:
        raise EvidenceError(f"Agent worker source hash mismatch under {branch_root}")
    required_agent_hashes = {
        "agent_request_file_sha256": sha256_file(request_path),
        "agent_initialize_file_sha256": sha256_file(initialize_path),
        "agent_rpc_transcript_file_sha256": sha256_file(transcript_path),
        "capability_probes_file_sha256": sha256_file(capability_path),
        "agent_final_file_sha256": sha256_file(
            branch_root / "agent_final.redacted.json"
        ),
        "capability_probe_rpc_transcript_file_sha256": sha256_file(
            capability_transcript_path
        ),
    }
    for key, actual in required_agent_hashes.items():
        if agent.get(key) != actual:
            raise EvidenceError(f"Agent process evidence hash mismatch: {key}")
    final_message = require_mapping(
        read_json(branch_root / "agent_final.redacted.json"),
        "persisted redacted Agent final message",
    )
    if (
        set(final_message)
        != {"type", "protocol_version", "ok", "result", "tool_call_count"}
        or final_message.get("type") != "final"
        or final_message.get("protocol_version") != PROTOCOL_VERSION
        or final_message.get("ok") is not True
        or not isinstance(final_message.get("tool_call_count"), int)
        or final_message["tool_call_count"] < 0
    ):
        raise EvidenceError("Persisted Agent final message schema is not exact")
    initialize = require_mapping(read_json(initialize_path), "Agent initialize")
    initialization_attestation = require_mapping(
        agent.get("initialization_attestation"), "Agent initialization attestation"
    )
    if (
        set(initialization_attestation) != AGENT_INITIALIZATION_ATTESTATION_KEYS
        or initialization_attestation.get("exact_fields") != sorted(initialize)
        or initialization_attestation.get("target_instruction_sha256")
        != hashlib.sha256(str(initialize.get("target_instruction", "")).encode("utf-8")).hexdigest()
        or initialization_attestation.get("retrieval_results_sha256")
        != hashlib.sha256(
            canonical_json(initialize.get("retrieval_results")).encode("utf-8")
        ).hexdigest()
        or initialization_attestation.get("private_controller_fields_present") is not False
    ):
        raise EvidenceError("Agent process initialization attestation does not bind the four-field wire")
    rpc_redaction_attestation = require_mapping(
        agent.get("redaction_attestation"), "Agent RPC redaction attestation"
    )
    if (
        set(rpc_redaction_attestation) != RPC_REDACTION_ATTESTATION_KEYS
        or rpc_redaction_attestation.get("schema_version")
        != "preempt-mem-rpc-redaction-v1"
        or rpc_redaction_attestation.get("algorithm")
        != "sha256(nonce || kind || canonical_value)[:16]"
        or rpc_redaction_attestation.get("sensitive_key_fragments")
        != list(RPC_SENSITIVE_KEY_FRAGMENTS)
        or rpc_redaction_attestation.get("redaction_count")
        != expected_rpc_redaction_count
        or not isinstance(
            rpc_redaction_attestation.get("sensitive_literal_count"), int
        )
        or rpc_redaction_attestation["sensitive_literal_count"] < 0
        or rpc_redaction_attestation.get("post_redaction_finding_count") != 0
        or rpc_redaction_attestation.get("nonce_commitment_sha256")
        != expected_nonce_commitment_sha256
        or rpc_redaction_attestation.get(
            "raw_transcript_retained_in_shareable_artifacts"
        )
        is not False
    ):
        raise EvidenceError("Agent RPC redaction attestation is not exactly bound")
    capability_process = require_mapping(
        read_json(branch_root / "capability_process_attestation.json"),
        "capability process attestation",
    )
    if (
        agent.get("capability_probe_process_attestation") != capability_process
        or capability_process.get("pid") == agent.get("pid")
    ):
        raise EvidenceError("Capability-probe process is not separately bound to Agent evidence")
    evaluator_pids = evaluator.get("pids")
    evaluator_exit_codes = evaluator.get("exit_codes")
    evaluator_processes = evaluator.get("processes")
    if (
        evaluator.get("role") != "official_evaluator"
        or evaluator_pids is None
        or not isinstance(evaluator_pids, list)
        or len(evaluator_pids) != 2
        or any(not isinstance(pid, int) or pid <= 0 for pid in evaluator_pids)
        or len(set(evaluator_pids)) != 2
        or agent.get("pid") in evaluator_pids
        or capability_process.get("pid") in evaluator_pids
        or evaluator_exit_codes != [0, 0]
        or evaluator.get("pid") != evaluator_pids[0]
        or evaluator.get("exit_code") != 0
        or evaluator.get("ground_truth_loaded") is not True
        or evaluator.get("ground_truth_loaded_per_process") != [True, True]
        or evaluator.get("save_report") is not False
        or evaluator.get("save_report_per_process") != [False, False]
        or evaluator.get("evaluation_entrypoint")
        != "appworld.evaluator.evaluate_task"
        or evaluator.get("evaluation_entrypoints")
        != ["appworld.evaluator.evaluate_task", "appworld.evaluator.evaluate_task"]
        or evaluator.get("agent_process_pid") != agent.get("pid")
        or evaluator.get("starts_after_case_agent_exit_barrier") is not True
        or not isinstance(evaluator_processes, list)
        or len(evaluator_processes) != 2
        or any(
            not isinstance(process_row, Mapping)
            or set(process_row) != EVALUATOR_PROCESS_ROW_KEYS
            or process_row.get("task_id") != expected_task_id
            or process_row.get("experiment_name") != expected_experiment_name
            for process_row in evaluator_processes
        )
    ):
        raise EvidenceError(f"Evaluator process boundary attestation failed under {branch_root}")
    evaluator_first_worker_path = branch_root / "evaluator_first_worker.json"
    evaluator_second_worker_path = branch_root / "evaluator_second_worker.json"
    required_evaluator_hashes = {
        "evaluator_first_file_sha256": sha256_file(evaluator_first_path),
        "evaluator_second_file_sha256": sha256_file(evaluator_second_path),
        "evaluator_first_worker_file_sha256": sha256_file(evaluator_first_worker_path),
        "evaluator_second_worker_file_sha256": sha256_file(evaluator_second_worker_path),
        "input_db_tree_manifest_root_sha256": db_tree["tree_manifest_root_sha256"],
    }
    for key, actual in required_evaluator_hashes.items():
        if evaluator.get(key) != actual:
            raise EvidenceError(f"Evaluator process evidence hash mismatch: {key}")
    expected_evaluator_worker_sha = sha256_file(
        Path(__file__).resolve().parent / "isolated_evaluator_worker.py"
    )
    import appworld

    expected_appworld_module_path = Path(appworld.__file__).resolve()
    expected_appworld_module_sha = sha256_file(expected_appworld_module_path)
    direct_url_text = importlib.metadata.distribution("appworld").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        raise EvidenceError("Aggregate runtime AppWorld has no direct_url.json")
    expected_direct_url_sha = hashlib.sha256(
        direct_url_text.encode("utf-8")
    ).hexdigest()
    expected_evaluator_environment_keys = sorted(
        {
            key
            for key in (
                "COMSPEC",
                "PATH",
                "PATHEXT",
                "SYSTEMDRIVE",
                "SYSTEMROOT",
                "TEMP",
                "TMP",
                "WINDIR",
            )
            if key in os.environ
        }
        | set(EXPECTED_EVALUATOR_DETERMINISTIC_ENVIRONMENT)
        | {"APPWORLD_ROOT"}
    )
    envelopes = [
        require_mapping(read_json(evaluator_first_worker_path), "first evaluator envelope"),
        require_mapping(read_json(evaluator_second_worker_path), "second evaluator envelope"),
    ]
    vectors = [read_json(evaluator_first_path), read_json(evaluator_second_path)]
    semantic_vectors = [
        evaluator_semantic_vector(vector, f"evaluator process vector {index + 1}")
        for index, vector in enumerate(vectors)
    ]
    semantic_hashes = [
        hashlib.sha256(canonical_json(vector).encode("utf-8")).hexdigest()
        for vector in semantic_vectors
    ]
    raw_vectors_exactly_equal = canonical_json(vectors[0]) == canonical_json(
        vectors[1]
    )
    for index, (envelope, vector) in enumerate(zip(envelopes, vectors, strict=True)):
        if set(envelope) != EVALUATOR_ENVELOPE_KEYS:
            raise EvidenceError(
                f"Evaluator worker envelope {index + 1} has missing/extra fields"
            )
        process_row = require_mapping(
            evaluator_processes[index], f"evaluator process row {index + 1}"
        )
        before = require_mapping(envelope.get("input_db_tree_before"), "evaluator input DB before")
        after = require_mapping(envelope.get("input_db_tree_after"), "evaluator input DB after")
        expected_argv = [
            Path(sys.executable).name,
            "-I",
            "isolated_evaluator_worker.py",
            "--appworld-root",
            "<ATTESTED_APPWORLD_ROOT>",
            "--task-id",
            expected_task_id,
            "--experiment-name",
            expected_experiment_name,
        ]
        if (
            envelope.get("result") != vector
            or envelope.get("worker_protocol")
            != "preempt3a-isolated-evaluator-v1"
            or envelope.get("pid") != evaluator_pids[index]
            or envelope.get("task_id") != expected_task_id
            or envelope.get("experiment_name") != expected_experiment_name
            or envelope.get("appworld_version") != expected_appworld_version
            or envelope.get("worker_sha256") != expected_evaluator_worker_sha
            or Path(str(envelope.get("appworld_module_file", ""))).resolve()
            != expected_appworld_module_path
            or envelope.get("appworld_module_file_sha256")
            != expected_appworld_module_sha
            or envelope.get("appworld_distribution_direct_url_sha256")
            != expected_direct_url_sha
            or envelope.get("evaluation_entrypoint") != "appworld.evaluator.evaluate_task"
            or envelope.get("ground_truth_loaded_only_in_evaluator") is not True
            or envelope.get("save_report") is not False
            or envelope.get("environment_key_names")
            != expected_evaluator_environment_keys
            or envelope.get("python_hash_seed") != "0"
            or envelope.get("deterministic_environment")
            != EXPECTED_EVALUATOR_DETERMINISTIC_ENVIRONMENT
            or envelope.get("input_db_path_role")
            != "live experiment DB frozen by controller before evaluator start"
            or envelope.get("input_db_unchanged") is not True
            or before != after
            or before.get("tree_manifest_root_sha256")
            != db_tree["tree_manifest_root_sha256"]
            or before.get("entries") != db_tree["entries"]
            or before.get("file_count") != db_tree["file_count"]
            or before.get("total_bytes") != db_tree["total_bytes"]
            or process_row.get("pid") != envelope.get("pid")
            or process_row.get("exit_code") != 0
            or process_row.get("worker_protocol") != envelope.get("worker_protocol")
            or process_row.get("worker_sha256") != envelope.get("worker_sha256")
            or process_row.get("evaluation_entrypoint")
            != envelope.get("evaluation_entrypoint")
            or process_row.get("ground_truth_loaded")
            != envelope.get("ground_truth_loaded_only_in_evaluator")
            or process_row.get("save_report") != envelope.get("save_report")
            or process_row.get("task_id") != envelope.get("task_id")
            or process_row.get("experiment_name") != envelope.get("experiment_name")
            or process_row.get("appworld_version") != envelope.get("appworld_version")
            or process_row.get("appworld_module_file")
            != envelope.get("appworld_module_file")
            or process_row.get("appworld_module_file_sha256")
            != envelope.get("appworld_module_file_sha256")
            or process_row.get("appworld_distribution_direct_url_sha256")
            != envelope.get("appworld_distribution_direct_url_sha256")
            or process_row.get("input_db_tree_before") != before
            or process_row.get("input_db_tree_after") != after
            or process_row.get("input_db_unchanged") is not True
            or process_row.get("environment_key_names")
            != envelope.get("environment_key_names")
            or process_row.get("python_hash_seed") != "0"
            or process_row.get("deterministic_environment")
            != EXPECTED_EVALUATOR_DETERMINISTIC_ENVIRONMENT
            or not _HEX_64_RE.fullmatch(str(process_row.get("stderr_sha256", "")))
            or not _HEX_64_RE.fullmatch(str(process_row.get("stdout_sha256", "")))
            or process_row.get("argv_attested") != expected_argv
        ):
            raise EvidenceError(
                f"Evaluator worker envelope {index + 1} is not bound to the frozen DB/vector"
            )
    if (
        evaluator.get("worker_sha256s")
        != [row["worker_sha256"] for row in evaluator_processes]
        or evaluator.get("worker_reported_input_db_tree_manifest_root_sha256s")
        != [
            envelope["input_db_tree_before"]["tree_manifest_root_sha256"]
            for envelope in envelopes
        ]
        or evaluator.get("worker_reported_input_db_entries_equal_frozen_copy")
        is not True
        or evaluator.get("input_db_unchanged_after_both_evaluators") is not True
        or evaluator.get("semantic_stability_policy")
        != (
            "exact outcome,difficulty,count,label,requirement multiset; "
            "retain but exclude failures[*].trace diagnostic repr ordering"
        )
        or evaluator.get("excluded_nondeterministic_diagnostic_fields")
        != ["failures[*].trace"]
        or evaluator.get("raw_vectors_exactly_equal")
        is not raw_vectors_exactly_equal
        or evaluator.get("semantic_vectors_equal") is not True
        or semantic_hashes[0] != semantic_hashes[1]
        or evaluator.get("semantic_vector_sha256") != semantic_hashes[0]
    ):
        raise EvidenceError(f"Evaluator outer/process/envelope cross-binding failed under {branch_root}")
    internal_raw_log = require_mapping(
        db_attestation.get("appworld_internal_raw_log"),
        "AppWorld internal raw-log removal attestation",
    )
    raw_log_existed = internal_raw_log.get("existed")
    raw_log_before_sha = internal_raw_log.get("file_sha256_before_removal")
    if (
        set(db_attestation) != DB_FREEZE_ATTESTATION_KEYS
        or set(internal_raw_log) != APPWORLD_INTERNAL_RAW_LOG_KEYS
        or db_attestation.get("frozen_before_evaluator") is not True
        or db_attestation.get("agent_exit_code") != 0
        or db_attestation.get("agent_process_pid") != agent.get("pid")
        or db_attestation.get("source_db_tree_manifest_root_sha256")
        != db_tree["tree_manifest_root_sha256"]
        or db_attestation.get("db_tree_manifest_root_sha256")
        != db_tree["tree_manifest_root_sha256"]
        or db_attestation.get("db_file_count") != db_tree["file_count"]
        or db_attestation.get("db_total_bytes") != db_tree["total_bytes"]
        or db_attestation.get("controller_memory_raw_tool_log_written_to_disk")
        is not False
        or db_attestation.get(
            "controller_memory_raw_tool_log_retained_until_case_firewall_scan"
        )
        is not True
        or db_attestation.get("redacted_tool_log_file_sha256")
        != sha256_file(branch_root / "api_calls.redacted.jsonl")
        or internal_raw_log.get("path") != "api_calls.jsonl"
        or not isinstance(raw_log_existed, bool)
        or internal_raw_log.get("row_count") != 0
        or internal_raw_log.get("removed") is not raw_log_existed
        or (
            raw_log_existed
            and (
                not isinstance(raw_log_before_sha, str)
                or not _HEX_64_RE.fullmatch(raw_log_before_sha)
            )
        )
        or (not raw_log_existed and raw_log_before_sha is not None)
    ):
        raise EvidenceError(f"DB freeze attestation failed under {branch_root}")
    return {
        "agent_pid": agent.get("pid"),
        "evaluator_pids": evaluator_pids,
        "capability_probe_pid": capability_process.get("pid"),
        "distinct_processes": True,
        "agent_ground_truth_loaded": False,
        "evaluator_ground_truth_loaded": True,
        "db_frozen_before_evaluator": True,
    }


def validate_redacted_logs(
    branch_root: Path, *, nonce_commitment_sha256: str
) -> dict[str, Any]:
    raw_logs = [path for path in branch_root.rglob("api_calls.jsonl")]
    if raw_logs:
        raise EvidenceError(f"Raw sensitive API logs retained in shareable artifacts: {raw_logs}")
    redacted_path = locate_unique_file(branch_root, "api_calls.redacted.jsonl")
    redacted = assert_redacted_jsonl(redacted_path)
    attestation_path = locate_unique_file(branch_root, "api_log_redaction_attestation.json")
    attestation = require_mapping(read_json(attestation_path), "API redaction attestation")
    if (
        set(attestation) != API_LOG_REDACTION_ATTESTATION_KEYS
        or attestation.get("schema_version") != REDACTION_SCHEMA
        or attestation.get("raw_row_count") != redacted["row_count"]
        or attestation.get("raw_source")
        != "controller-memory-only canonical JSONL; never written to run artifacts"
        or attestation.get("raw_file_retained_in_shareable_artifacts") is not False
        or attestation.get("redacted_file") != redacted_path.name
        or attestation.get("redacted_file_sha256") != redacted["file_sha256"]
        or attestation.get("redacted_row_count") != redacted["row_count"]
        or not isinstance(attestation.get("raw_file_sha256"), str)
        or not _HEX_64_RE.fullmatch(attestation["raw_file_sha256"])
        or not isinstance(attestation.get("rpc_redaction_count"), int)
        or attestation["rpc_redaction_count"] < 0
        or not isinstance(attestation.get("evidence_additional_redaction_count"), int)
        or attestation["evidence_additional_redaction_count"] < 0
        or not isinstance(attestation.get("total_redaction_count"), int)
        or attestation["total_redaction_count"] < 0
        or attestation.get("redaction_count") != attestation.get("total_redaction_count")
        or attestation.get("total_redaction_count")
        != attestation.get("rpc_redaction_count")
        + attestation.get("evidence_additional_redaction_count")
        or attestation.get("nonce_commitment_sha256") != nonce_commitment_sha256
    ):
        raise EvidenceError(f"API redaction attestation mismatch under {branch_root}")
    transcript_path = branch_root / "agent_rpc_transcript.jsonl"
    transcript = assert_redacted_jsonl(transcript_path)
    if transcript_path.read_bytes() != redacted_path.read_bytes():
        raise EvidenceError(f"Redacted API log and RPC transcript differ under {branch_root}")
    return {
        "api_log": redacted,
        "api_redaction_count": attestation["total_redaction_count"],
        "rpc_redaction_count": attestation["rpc_redaction_count"],
        "evidence_additional_redaction_count": attestation[
            "evidence_additional_redaction_count"
        ],
        "rpc_transcript": transcript,
        "raw_log_retained": False,
    }


def recompute_structured_tool_transcript(
    branch_root: Path, *, expected_tools: list[str]
) -> dict[str, Any]:
    transcript_path = branch_root / "agent_rpc_transcript.jsonl"
    rows = read_jsonl(transcript_path)
    allowed = set(expected_tools)
    requested_tools: list[str] = []
    for index, item in enumerate(rows, start=1):
        row = require_mapping(item, f"agent transcript row {index}")
        if set(row) != {"call", "response"}:
            raise EvidenceError(f"Agent transcript row {index} schema is not exact")
        call = require_mapping(row.get("call"), f"agent transcript call {index}")
        response = require_mapping(row.get("response"), f"agent transcript response {index}")
        expected_call_keys = {
            "type",
            "protocol_version",
            "request_id",
            "app",
            "api",
            "arguments",
        }
        if set(call) != expected_call_keys:
            raise EvidenceError(f"Agent tool call {index} schema is not exact")
        request_id = f"call-{index:04d}"
        tool = f"{call.get('app')}.{call.get('api')}"
        if (
            call.get("type") != "tool_call"
            or call.get("protocol_version") != PROTOCOL_VERSION
            or call.get("request_id") != request_id
            or not isinstance(call.get("arguments"), Mapping)
            or tool not in allowed
        ):
            raise EvidenceError(f"Agent tool call {index} is outside the frozen RPC/allowlist contract")
        if (
            set(response) != {"type", "protocol_version", "request_id", "ok", "result"}
            or response.get("type") != "tool_result"
            or response.get("protocol_version") != PROTOCOL_VERSION
            or response.get("request_id") != request_id
            or response.get("ok") is not True
        ):
            raise EvidenceError(f"Agent tool response {index} is not a successful matching result")
        requested_tools.append(tool)
    plan = require_mapping(
        read_json(branch_root / "structured_agent_plan.json"), "structured agent plan"
    )
    final_message = require_mapping(
        read_json(branch_root / "agent_final.redacted.json"),
        "persisted redacted Agent final message",
    )
    if (
        set(plan) != STRUCTURED_AGENT_PLAN_KEYS
        or plan.get("schema_version") != "preempt-mem-3a-r-structured-agent-plan-v1"
        or plan.get("tool_protocol") != PROTOCOL_VERSION
        or plan.get("tool_call_count") != len(rows)
        or plan.get("requested_public_tools") != requested_tools
        or plan.get("arbitrary_code_execution") is not False
        or plan.get("agent_result") != final_message.get("result")
        or plan.get("tool_call_count") != final_message.get("tool_call_count")
    ):
        raise EvidenceError("Structured Agent plan is inconsistent with its raw redacted RPC transcript")
    branch_result = require_mapping(read_json(branch_root / "branch_result.json"), "branch result")
    if branch_result.get("api_tool_call_count") != len(rows):
        raise EvidenceError("Branch result tool-call count differs from the RPC transcript")
    return {
        "tool_call_count": len(rows),
        "requested_public_tools": requested_tools,
        "all_calls_exactly_allowlisted": True,
        "protocol_and_request_ids_recomputed": True,
    }


def _boolean_leaf_pass(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, Mapping):
        return value.get("pass") is True or value.get("equal") is True
    return False


def validate_target_distractor_probe(value: Any) -> dict[str, Any]:
    document = require_mapping(value, "target+distractor probe")
    if document.get("schema_version") != "preempt-mem-3a-r-target-distractor-probe-v1":
        raise EvidenceError("Target+distractor probe schema is not the frozen v1 contract")
    if document.get("all_pass") is not True:
        raise EvidenceError("Target+distractor probe top-level gate did not pass")

    # Re-execute the frozen deterministic probe and require full canonical
    # equality.  This independently binds delete_result, the complete effective
    # eviction manifest (including all surface checks), shared-cache checks,
    # restore identity, and every derived hash instead of trusting selected
    # summary booleans from the stored artifact.
    fresh_document = run_target_distractor_probe()
    if fresh_document.get("all_pass") is not True:
        raise EvidenceError("Fresh target+distractor recomputation failed")
    if canonical_json(document) != canonical_json(fresh_document):
        raise EvidenceError(
            "Stored target+distractor artifact differs from fresh frozen-code recomputation"
        )

    serializer = require_mapping(document.get("serializer_checks"), "serializer checks")
    required_serializer = {
        "non_empty_memory_record",
        "dataclass_matches_field_mapping",
        "set_is_stable",
        "set_members_sorted",
        "set_has_type_domain_separation",
        "tuple_is_stable",
    }
    if not required_serializer.issubset(serializer):
        raise EvidenceError("Serializer probe does not cover MemoryRecord/dataclass/tuple/set")
    if not all(serializer.get(key) is True for key in required_serializer):
        raise EvidenceError("Canonical serializer probe failed")

    positive = require_mapping(document.get("positive_surface_coverage"), "positive surface coverage")
    positive_rows = {
        name: require_mapping(row, f"positive surface {name}")
        for name, row in positive.items()
        if name != "all_surfaces_nonempty"
    }
    if len(positive_rows) < 9 or any(
        row.get("target_nonempty") is not True
        or row.get("distractor_nonempty") is not True
        or not _HEX_64_RE.fullmatch(str(row.get("target_before_sha256", "")))
        or not _HEX_64_RE.fullmatch(str(row.get("distractor_before_sha256", "")))
        for row in positive_rows.values()
    ):
        raise EvidenceError("Target+distractor probe lacks positive coverage for every surface")

    components = require_mapping(
        document.get("positive_component_coverage"), "positive component coverage"
    )
    component_rows = {
        name: require_mapping(row, f"positive component {name}")
        for name, row in components.items()
        if name != "all_components_nonempty"
    }
    if len(component_rows) < 25 or any(
        row.get("target_nonempty") is not True
        or row.get("distractor_nonempty") is not True
        for row in component_rows.values()
    ):
        raise EvidenceError("Positive component coverage is vacuous or incomplete")

    target_absence = require_mapping(
        document.get("target_component_absence_after_delete"),
        "target component absence",
    )
    target_absence_rows = {
        name: absent
        for name, absent in target_absence.items()
        if name != "all_components_absent"
    }
    if len(target_absence_rows) < 25 or any(absent is not True for absent in target_absence_rows.values()):
        raise EvidenceError("Target-scoped deletion leaves one or more target-derived components")

    target_unreachable = require_mapping(document.get("target_unreachable"), "target unreachable")
    target_checks = {
        key: item
        for key, item in target_unreachable.items()
        if key not in {"all_pass", "effective_eviction_check_count"}
    }
    if not target_checks or any(item is not True for item in target_checks.values()):
        raise EvidenceError("Target remains reachable after target-scoped deletion")
    if not isinstance(target_unreachable.get("effective_eviction_check_count"), int) or target_unreachable["effective_eviction_check_count"] < 9:
        raise EvidenceError("Target eviction probe does not cover all store surfaces")

    distractor = require_mapping(
        document.get("distractor_equivalence_after_target_delete"),
        "distractor equivalence",
    )
    surfaces = require_mapping(distractor.get("surfaces"), "distractor surfaces")
    if len(surfaces) < 9:
        raise EvidenceError("Distractor equivalence covers fewer than nine memory surfaces")
    failed_surfaces: list[str] = []
    for name, value_row in surfaces.items():
        row = require_mapping(value_row, f"distractor surface {name}")
        before_json = row.get("before_canonical_json")
        after_json = row.get("after_canonical_json")
        if not isinstance(before_json, str) or not isinstance(after_json, str):
            failed_surfaces.append(name)
            continue
        before_sha256 = hashlib.sha256(before_json.encode("utf-8")).hexdigest()
        after_sha256 = hashlib.sha256(after_json.encode("utf-8")).hexdigest()
        if (
            row.get("before_sha256") != before_sha256
            or row.get("after_sha256") != after_sha256
            or before_json != after_json
            or row.get("equal") is not True
        ):
            failed_surfaces.append(name)
    if failed_surfaces:
        raise EvidenceError(f"Distractor surfaces changed: {failed_surfaces}")

    shared = require_mapping(
        document.get("shared_keyword_cache_and_ann_collision"),
        "shared keyword/cache and ANN collision",
    )
    before_shared = require_mapping(shared.get("before_delete"), "shared collision before")
    after_shared = require_mapping(shared.get("after_delete"), "shared collision after")
    put_results = require_mapping(document.get("put_results"), "probe put results")
    target_put = require_mapping(put_results.get("target"), "target put")
    distractor_put = require_mapping(put_results.get("distractor"), "distractor put")
    target_id = target_put.get("memory_id")
    distractor_id = distractor_put.get("memory_id")
    if not isinstance(target_id, str) or not isinstance(distractor_id, str) or target_id == distractor_id:
        raise EvidenceError("Target+distractor probe does not bind two distinct record IDs")
    expected_before_ids = sorted([target_id, distractor_id])
    shared_hashes = [
        before_shared.get("ann_content_sha256"),
        before_shared.get("target_content_sha256"),
        before_shared.get("distractor_content_sha256"),
    ]
    if (
        before_shared.get("shared_query") != "shared retrieval"
        or before_shared.get("target_derived_mixed_query")
        != "cobalt ledger shared retrieval"
        or any(not isinstance(value, str) or not _HEX_64_RE.fullmatch(value) for value in shared_hashes)
        or len(set(shared_hashes)) != 1
        or before_shared.get("same_content_sha256") is not True
        or sorted(before_shared.get("ann_members", [])) != expected_before_ids
        or sorted(before_shared.get("shared_query_result_ids", [])) != expected_before_ids
        or sorted(before_shared.get("shared_cache_ids", [])) != expected_before_ids
        or sorted(before_shared.get("target_derived_mixed_query_result_ids", []))
        != expected_before_ids
        or sorted(before_shared.get("target_derived_mixed_cache_ids", []))
        != expected_before_ids
        or after_shared.get("ann_members") != [distractor_id]
        or after_shared.get("shared_query_result_ids") != [distractor_id]
        or after_shared.get("shared_cache_ids") != [distractor_id]
        or after_shared.get("target_derived_mixed_cache_present") is not False
    ):
        raise EvidenceError("Shared keyword/cache or ANN collision invalidation is not target-scoped")

    restore = require_mapping(document.get("restore_identity"), "restore identity")
    restore_id_equal = restore.get("requested_memory_id") == restore.get("restored_memory_id")
    restore_hash_equal = restore.get("put_record_sha256") == restore.get("restored_record_sha256")
    record_ids_equal = sorted(restore.get("expected_record_ids", [])) == sorted(
        restore.get("actual_record_ids", [])
    )
    if not (
        restore_id_equal
        and restore_hash_equal
        and record_ids_equal
        and restore.get("same_target_item") is True
        and restore.get("no_extra_record") is True
        and restore.get("distractor_unchanged_by_restore") is True
    ):
        raise EvidenceError("Restore did not recover the exact target item")
    return {
        "serializer_memory_record_pass": True,
        "serializer_set_pass": True,
        "positive_surface_count": len(positive_rows),
        "positive_all_surfaces_nonempty_recomputed": True,
        "positive_component_count": len(component_rows),
        "positive_all_components_nonempty_recomputed": True,
        "target_component_absence_count": len(target_absence_rows),
        "target_all_components_absent_recomputed": True,
        "target_unreachable": True,
        "distractor_surface_count": len(surfaces),
        "distractor_all_equal_recomputed": True,
        "shared_keyword_cache_ann_collision_recomputed": True,
        "restore_identity": True,
    }


def recompute_branch(
    branch_root: Path,
    *,
    branch_name: str,
    nonce_commitment_sha256: str,
    run_nonce: str,
    freeze_id: str,
    freeze_sha256: str,
    case_contract: Mapping[str, Any],
) -> dict[str, Any]:
    result = require_mapping(read_json(branch_root / "branch_result.json"), "branch result")
    if (
        set(result) != BRANCH_RESULT_KEYS
        or result.get("schema_version") != "preempt-mem-3a-r-branch-result-v1"
        or result.get("case_id") != case_contract["case"]["case_id"]
        or result.get("branch") != branch_name
        or result.get("classification") != case_contract["classification"]
        or result.get("mechanism_claim")
        != "constructed deterministic selector-channel mechanism smoke"
        or result.get("execution_freeze_id") != freeze_id
        or result.get("execution_freeze_sha256") != freeze_sha256
        or result.get("execution_freeze_validation_pass") is not True
        or result.get("checkpoint_id") != case_contract["state_checkpoint_id"]
        or result.get("checkpoint_byte_equivalent_to_case_base") is not True
        or result.get("agent_model") != case_contract["agent_model"]
        or result.get("agent_model_type") != case_contract["agent_model_type"]
        or result.get("seed") != case_contract["seed"]
    ):
        raise EvidenceError(f"Branch result identity/freeze/config contract mismatch under {branch_root}")
    hash_contract = validate_hash_contract(branch_root, result)
    request_path = branch_root / "agent_request.json"
    request = validate_agent_request(read_json(request_path), f"{branch_name} agent request")
    expected_instruction = case_contract["target_instruction"]
    expected_tools = case_contract["allowed_tools"]
    expected_projection = case_contract["public_projection"]
    expected_retrieval = [] if branch_name == "Evicted" else [expected_projection]
    if (
        request.get("schema_version") != "preempt-mem-3a-r-agent-request-v1"
        or request.get("tool_protocol") != PROTOCOL_VERSION
        or request.get("target_instruction") != expected_instruction
        or request.get("target_instruction_sha256")
        != hashlib.sha256(expected_instruction.encode("utf-8")).hexdigest()
        or request.get("allowed_tools") != expected_tools
        or request.get("retrieval_results") != expected_retrieval
    ):
        raise EvidenceError(f"{branch_name} Agent request differs from the frozen case/tool contract")
    initialize = require_mapping(
        read_json(branch_root / "agent_initialize.json"), f"{branch_name} Agent initialize"
    )
    expected_initialize = {
        "type": "initialize",
        "protocol_version": PROTOCOL_VERSION,
        "target_instruction": expected_instruction,
        "retrieval_results": expected_retrieval,
    }
    if initialize != expected_initialize:
        raise EvidenceError(f"{branch_name} Agent wire is not the exact four-field contract")
    if request.get("run_nonce_commitment_sha256") != nonce_commitment_sha256:
        raise EvidenceError(f"Agent request nonce commitment mismatch under {branch_root}")
    if request["prompt_logical_lf_sha256"] != hash_contract["prompt_logical_lf_sha256"]:
        raise EvidenceError(f"Agent request prompt hash mismatch under {branch_root}")
    if request["retrieval_results"] != read_json(branch_root / "retrieval_results.json"):
        raise EvidenceError(f"Agent request/retrieval artifact mismatch under {branch_root}")
    retrieval_sha256 = hashlib.sha256(
        canonical_json(request["retrieval_results"]).encode("utf-8")
    ).hexdigest()
    if request["retrieval_results_sha256"] != retrieval_sha256:
        raise EvidenceError(f"Agent retrieval logical hash mismatch under {branch_root}")

    record = case_contract["record"]
    expected_put = {"memory_id": record.memory_id, "record_sha256": record.record_sha256}
    expected_delete = {
        "memory_id": record.memory_id,
        "content_sha256": record.content_sha256,
        "record_sha256": record.record_sha256,
    }
    if result.get("memory_put") != expected_put:
        raise EvidenceError(f"{branch_name} memory_put is not the frozen target item")
    if branch_name == "Full":
        expected_delete_event, expected_restore_event = None, None
    elif branch_name == "Evicted":
        expected_delete_event, expected_restore_event = expected_delete, None
    else:
        expected_delete_event, expected_restore_event = expected_delete, expected_put
    if (
        result.get("memory_delete") != expected_delete_event
        or result.get("memory_restore") != expected_restore_event
        or result.get("retrieved_memory_ids")
        != ([] if branch_name == "Evicted" else [record.memory_id])
        or result.get("target_task_id")
        != case_contract["case"]["target_task"]["task_id"]
        or result.get("experiment_name")
        != (
            f"preempt3ar_{branch_root.parents[2].name}_"
            f"{case_contract['case']['case_id']}_{branch_name.lower()}"
        )
        or result.get("target_instruction_sha256")
        != hashlib.sha256(expected_instruction.encode("utf-8")).hexdigest()
        or result.get("mechanism_claim")
        != "constructed deterministic selector-channel mechanism smoke"
    ):
        raise EvidenceError(f"{branch_name} memory event/claim contract mismatch")

    capability_path = branch_root / "capability_probes.json"
    capability_transcript_path = branch_root / "capability_probe_rpc_transcript.jsonl"
    capability = recompute_capability_probes(
        read_json(capability_path),
        f"{branch_name} capability probes",
        branch_root=branch_root,
    )
    transcript_path = branch_root / "agent_rpc_transcript.jsonl"
    redaction = validate_redacted_logs(
        branch_root, nonce_commitment_sha256=nonce_commitment_sha256
    )
    tool_transcript = recompute_structured_tool_transcript(
        branch_root, expected_tools=expected_tools
    )
    checkpoint_path = locate_checkpoint_directory(branch_root)
    db_path = locate_frozen_db_directory(branch_root)
    checkpoint = tree_attestation(checkpoint_path)
    db_tree = tree_attestation(db_path)
    db_attestation = require_mapping(
        read_json(branch_root / "db_freeze_attestation.json"), "DB freeze attestation"
    )
    evaluator_first_path = branch_root / "evaluator_first.json"
    evaluator_second_path = branch_root / "evaluator_second.json"
    evaluator_first_raw = read_json(evaluator_first_path)
    evaluator_second_raw = read_json(evaluator_second_path)
    evaluator_first = validate_evaluator_vector(evaluator_first_raw, "evaluator_first")
    evaluator_second = validate_evaluator_vector(
        evaluator_second_raw, "evaluator_second"
    )
    evaluator_stable = (
        evaluator_first["semantic_vector_sha256"]
        == evaluator_second["semantic_vector_sha256"]
    )
    if not evaluator_stable:
        raise EvidenceError(f"Evaluator is unstable under {branch_root}")
    if branch_name == "Full":
        effective_eviction_all_pass: bool | None = None
    else:
        eviction_recomputed = recompute_eviction_manifest(
            read_json(branch_root / "effective_eviction_manifest.json"),
            f"{branch_name} effective eviction",
            expected_record=record,
        )
        effective_eviction_all_pass = bool(
            eviction_recomputed["all_pass_recomputed"]
        )
    process = validate_process_boundaries(
        branch_root,
        request_path=request_path,
        initialize_path=branch_root / "agent_initialize.json",
        transcript_path=transcript_path,
        capability_path=capability_path,
        capability_transcript_path=capability_transcript_path,
        evaluator_first_path=evaluator_first_path,
        evaluator_second_path=evaluator_second_path,
        db_attestation=db_attestation,
        db_tree=db_tree,
        expected_task_id=str(case_contract["case"]["target_task"]["task_id"]),
        expected_experiment_name=(
            f"preempt3ar_{branch_root.parents[2].name}_"
            f"{case_contract['case']['case_id']}_{branch_name.lower()}"
        ),
        expected_appworld_version=str(case_contract["appworld_code_version"]),
        expected_nonce_commitment_sha256=hashlib.sha256(
            ("PREEMPT-Mem-3A-R-RPC-redaction\x00" + run_nonce).encode("utf-8")
        ).hexdigest(),
        expected_rpc_redaction_count=redaction["rpc_redaction_count"],
    )
    plan = require_mapping(
        read_json(branch_root / "structured_agent_plan.json"), "structured agent plan"
    )
    success = evaluator_first["success"]
    expected_severity = 0 if success else 3
    expected_severity_reason = (
        "official evaluator success; no relevant loss"
        if success
        else "official task failure under the frozen fail-closed selector-channel control"
    )
    if (
        result.get("agent_result") != plan.get("agent_result")
        or result.get("agent_process_pid") != process["agent_pid"]
        or result.get("evaluator_process_pids") != process["evaluator_pids"]
        or result.get("agent_ground_truth_loaded") is not False
        or result.get("evaluator_ground_truth_loaded") is not True
        or result.get("official_success") is not success
        or result.get("evaluator_num_tests") != evaluator_first["num_tests"]
        or result.get("evaluator_pass_count") != evaluator_first["passed"]
        or result.get("evaluator_failure_count") != evaluator_first["failed"]
        or result.get("evaluator_stable") is not True
        or result.get("severity") != expected_severity
        or result.get("severity_reason") != expected_severity_reason
        or result.get("severe_loss")
        != (expected_severity >= int(case_contract["severe_threshold"]))
        or result.get("db_tree_manifest_root_sha256")
        != db_tree["tree_manifest_root_sha256"]
        or result.get("db_file_count") != db_tree["file_count"]
        or result.get("checkpoint_tree_manifest_root_sha256")
        != checkpoint["tree_manifest_root_sha256"]
        or result.get("capability_probe_all_pass") is not True
        or capability.get("all_denied_recomputed") is not True
        or result.get("effective_eviction_all_pass")
        is not effective_eviction_all_pass
        or result.get("api_tool_call_count")
        != tool_transcript["tool_call_count"]
        or result.get("api_log_redaction_count")
        != redaction["api_redaction_count"]
        or result.get("raw_api_logs_retained_in_run") is not False
    ):
        raise EvidenceError(f"{branch_name} branch result does not match raw process/DB/evaluator evidence")
    return {
        "branch": branch_name,
        "result": result,
        "hash_contract": hash_contract,
        "agent_request": request,
        "checkpoint": checkpoint,
        "_checkpoint_path": checkpoint_path,
        "db_tree": db_tree,
        "_db_path": db_path,
        "evaluator": evaluator_first,
        "evaluator_stable": True,
        "capability": capability,
        "process_boundary": process,
        "redaction": redaction,
        "tool_transcript": tool_transcript,
    }


def recompute_case(
    case_root: Path,
    *,
    project_root: Path,
    case_id: str,
    nonce_commitment_sha256: str,
    run_nonce: str,
    freeze_result: Mapping[str, Any],
    freeze_id: str,
    freeze_sha256: str,
    planned_runner_argv: list[str],
    case_contract: Mapping[str, Any],
) -> dict[str, Any]:
    invocation = require_mapping(
        read_json(case_root / "controller_invocation.json"), "controller invocation"
    )
    if set(invocation) != CONTROLLER_INVOCATION_KEYS:
        raise EvidenceError(f"Controller invocation schema differs from contract: {case_id}")
    if invocation.get("argv") != planned_runner_argv:
        raise EvidenceError(f"Actual runner argv differs from pre-run commitment: {case_id}")
    def planned_value(flag: str) -> str:
        try:
            index = planned_runner_argv.index(flag)
            return planned_runner_argv[index + 1]
        except (ValueError, IndexError) as error:
            raise EvidenceError(f"Planned runner argv omits {flag}") from error

    config_path = resolve_project_path(project_root, case_contract["config_relative_path"])
    base_config_path = resolve_project_path(
        project_root, case_contract["base_config_relative_path"]
    )
    prompt_path = resolve_project_path(project_root, case_contract["prompt_relative_path"])
    witnesses_path = resolve_project_path(
        project_root, case_contract["witnesses_relative_path"]
    )
    import appworld

    module_path = Path(appworld.__file__).resolve()
    direct_url_text = importlib.metadata.distribution("appworld").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        raise EvidenceError("Controller AppWorld distribution has no direct_url.json")
    if (
        planned_value("--config") != case_contract["config_relative_path"]
        or planned_value("--case") != case_id
        or planned_value("--run-id") != case_root.parents[1].name
        or planned_value("--witnesses") != case_contract["witnesses_relative_path"]
        or invocation.get("python_executable") != Path(sys.executable).as_posix()
        or invocation.get("python_executable_sha256")
        != sha256_file(Path(sys.executable))
        or invocation.get("appworld_version") != case_contract["appworld_code_version"]
        or invocation.get("appworld_module_relative_path")
        != module_path.relative_to(project_root).as_posix()
        or invocation.get("appworld_module_file_sha256") != sha256_file(module_path)
        or invocation.get("appworld_distribution_direct_url_sha256")
        != hashlib.sha256(direct_url_text.encode("utf-8")).hexdigest()
        or invocation.get("appworld_root") != "third_step_a/appworld_root"
        or invocation.get("config_path") != case_contract["config_relative_path"]
        or invocation.get("config_file_sha256") != sha256_file(config_path)
        or invocation.get("base_config_file_sha256") != sha256_file(base_config_path)
        or invocation.get("prompt_path") != case_contract["prompt_relative_path"]
        or invocation.get("prompt_file_sha256") != sha256_file(prompt_path)
        or invocation.get("witness_path") != case_contract["witnesses_relative_path"]
        or invocation.get("witness_file_sha256") != sha256_file(witnesses_path)
        or require_mapping(invocation.get("execution_freeze"), "invocation freeze")
        != freeze_result
        or invocation.get("precommit_nonce_commitment_sha256")
        != nonce_commitment_sha256
        or invocation.get("controller_load_ground_truth") is not False
        or invocation.get("evaluator_load_ground_truth") is not True
        or invocation.get("agent_protocol") != PROTOCOL_VERSION
        or invocation.get("pilot_started") is not False
        or not isinstance(invocation.get("controller_pid"), int)
        or invocation["controller_pid"] <= 0
    ):
        raise EvidenceError(f"{case_id} controller invocation/source/environment binding failed")
    branches = {
        branch: recompute_branch(
            case_root / branch.lower(),
            branch_name=branch,
            nonce_commitment_sha256=nonce_commitment_sha256,
            run_nonce=run_nonce,
            freeze_id=freeze_id,
            freeze_sha256=freeze_sha256,
            case_contract=case_contract,
        )
        for branch in BRANCHES
    }
    prompt_template = prompt_path.read_text(encoding="utf-8")
    expected_prompt = prompt_template.format(
        target_instruction=case_contract["target_instruction"],
        retrieval_query=case_contract["target_instruction"],
    )
    if any(
        (case_root / branch.lower() / "prompt.txt").read_text(encoding="utf-8")
        != expected_prompt
        for branch in BRANCHES
    ):
        raise EvidenceError(f"{case_id} prompt differs from frozen treatment-blind template")
    worker_pids = {
        pid
        for branch in branches.values()
        for pid in (
            branch["process_boundary"]["agent_pid"],
            branch["process_boundary"]["capability_probe_pid"],
            *branch["process_boundary"]["evaluator_pids"],
        )
    }
    if invocation["controller_pid"] in worker_pids:
        raise EvidenceError(f"{case_id} controller PID is not separate from a worker")
    branch_results = {branch: data["result"] for branch, data in branches.items()}
    case = case_contract["case"]
    record = case_contract["record"]
    source = case["source_episode"]
    source_specs_path = (
        project_root
        / "third_step_a/appworld_root/data/tasks"
        / str(source["task_id"])
        / "specs.json"
    )
    source_specs = require_mapping(read_json(source_specs_path), "source specs")
    expected_source_episode = {
        **source,
        "instruction": source_specs["instruction"],
        "source_specs_file_sha256_recomputed": sha256_file(source_specs_path),
        "candidate_record": case_contract["record_mapping"],
        "candidate_record_sha256": record.record_sha256,
    }
    if (
        read_json(case_root / "source_episode.json") != expected_source_episode
        or read_json(case_root / "memory_provenance.json") != record.provenance
    ):
        raise EvidenceError(f"{case_id} source/candidate memory provenance is not reproducible")
    barrier = require_mapping(
        read_json(case_root / "case_agent_exit_barrier.json"), "Agent exit barrier"
    )
    expected_agent_pids = [branches[branch]["process_boundary"]["agent_pid"] for branch in BRANCHES]
    if (
        set(barrier) != CASE_AGENT_EXIT_BARRIER_KEYS
        or barrier.get("all_three_agent_processes_exited") is not True
        or barrier.get("agent_pids") != expected_agent_pids
        or barrier.get("agent_exit_codes") != [0, 0, 0]
        or barrier.get("all_three_databases_frozen") is not True
        or barrier.get("private_artifacts_written_before_barrier") is not False
    ):
        raise EvidenceError(f"{case_id} Agent-exit/private-artifact barrier mismatch")
    checkpoint_manifest = require_mapping(
        read_json(case_root / "checkpoint_manifest.json"), "checkpoint manifest"
    )
    branch_checkpoint_roots = checkpoint_manifest.get("branch_checkpoint_roots")
    expected_checkpoint_manifest_keys = {
        "schema_version",
        "checkpoint_id",
        "controller_checkpoint_experiment",
        "base_checkpoint",
        "branch_checkpoint_roots",
        "all_three_byte_equivalent",
        "agent_world_load_ground_truth",
    }
    expected_checkpoint_experiment = (
        f"preempt3ar_{case_root.parents[1].name}_{case_id}_checkpoint"
    )
    fresh_checkpoint_rows = {
        branch: branches[branch]["checkpoint"] for branch in BRANCHES
    }
    base_checkpoint_row = require_mapping(
        checkpoint_manifest.get("base_checkpoint"), "base checkpoint"
    )
    checkpoint_content_keys = (
        "file_count",
        "total_bytes",
        "tree_manifest_root_sha256",
        "entries",
    )
    if (
        set(checkpoint_manifest) != expected_checkpoint_manifest_keys
        or checkpoint_manifest.get("schema_version")
        != "preempt-mem-3a-r-checkpoint-manifest-v1"
        or checkpoint_manifest.get("checkpoint_id") != case_contract["state_checkpoint_id"]
        or checkpoint_manifest.get("controller_checkpoint_experiment")
        != expected_checkpoint_experiment
        or checkpoint_manifest.get("all_three_byte_equivalent") is not True
        or checkpoint_manifest.get("agent_world_load_ground_truth") is not False
        or set(base_checkpoint_row) != TREE_ATTESTATION_KEYS
        or base_checkpoint_row.get("directory") != case_contract["state_checkpoint_id"]
        or any(
            base_checkpoint_row.get(key) != fresh_checkpoint_rows["Full"].get(key)
            for key in checkpoint_content_keys
        )
        or not isinstance(branch_checkpoint_roots, Mapping)
        or set(branch_checkpoint_roots) != set(BRANCHES)
        or any(
            set(require_mapping(branch_checkpoint_roots[branch], "branch checkpoint"))
            != TREE_ATTESTATION_KEYS
            for branch in BRANCHES
        )
        or any(
            require_mapping(branch_checkpoint_roots[branch], "branch checkpoint")
            != fresh_checkpoint_rows[branch]
            for branch in BRANCHES
        )
        or len(
            {
                require_mapping(branch_checkpoint_roots[branch], "branch checkpoint").get(
                    "tree_manifest_root_sha256"
                )
                for branch in BRANCHES
            }
        )
        != 1
    ):
        raise EvidenceError(f"{case_id} branch checkpoints are not the same frozen snapshot")
    full, evicted, restore = branches["Full"], branches["Evicted"], branches["Restore"]
    checkpoint_equal = len(
        {branch["checkpoint"]["tree_manifest_root_sha256"] for branch in branches.values()}
    ) == 1
    prompt_equal = len(
        {branch["hash_contract"]["prompt_logical_lf_sha256"] for branch in branches.values()}
    ) == 1
    agent_request_treatment_only = len(
        {
            canonical_json(treatment_blind_request(branch["agent_request"]))
            for branch in branches.values()
        }
    ) == 1
    full_retrieval = full["agent_request"]["retrieval_results"]
    evicted_retrieval = evicted["agent_request"]["retrieval_results"]
    restore_retrieval = restore["agent_request"]["retrieval_results"]
    retrieval_contract = bool(
        isinstance(full_retrieval, list)
        and len(full_retrieval) == 1
        and evicted_retrieval == []
        and restore_retrieval == full_retrieval
    )
    db_full_restore_equal = full["db_tree"]["entries"] == restore["db_tree"]["entries"]
    evaluator_full_restore_equal = (
        full["evaluator"]["vector_sha256"] == restore["evaluator"]["vector_sha256"]
    )
    outcome_direction = bool(
        full["evaluator"]["success"]
        and not evicted["evaluator"]["success"]
        and restore["evaluator"]["success"]
    )
    plan_full_restore_equal = (
        full["hash_contract"]["structured_agent_plan_logical_lf_sha256"]
        == restore["hash_contract"]["structured_agent_plan_logical_lf_sha256"]
    )
    rpc_full_restore_equal = (
        full["redaction"]["rpc_transcript"]["file_sha256"]
        == restore["redaction"]["rpc_transcript"]["file_sha256"]
    )
    full_put = require_mapping(full["result"].get("memory_put"), "Full memory_put")
    restore_put = require_mapping(restore["result"].get("memory_put"), "Restore memory_put")
    restore_event = require_mapping(restore["result"].get("memory_restore"), "Restore memory_restore")
    restore_same_item = bool(
        full_put.get("memory_id")
        == restore_put.get("memory_id")
        == restore_event.get("memory_id")
        and full_put.get("record_sha256")
        == restore_put.get("record_sha256")
        == restore_event.get("record_sha256")
    )
    database_diffs = {
        "checkpoint_to_full": recompute_database_diff(
            full["_checkpoint_path"], full["_db_path"]
        ),
        "checkpoint_to_evicted": recompute_database_diff(
            evicted["_checkpoint_path"], evicted["_db_path"]
        ),
        "checkpoint_to_restore": recompute_database_diff(
            restore["_checkpoint_path"], restore["_db_path"]
        ),
        "full_to_evicted": recompute_database_diff(full["_db_path"], evicted["_db_path"]),
        "full_to_restore": recompute_database_diff(full["_db_path"], restore["_db_path"]),
    }
    if read_json(case_root / "database_state_diff.json") != database_diffs:
        raise EvidenceError(f"{case_id} stored DB diff differs from independent recomputation")
    evicted_manifest = recompute_eviction_manifest(
        read_json(case_root / "evicted/effective_eviction_manifest.json"),
        f"{case_id} Evicted effective eviction",
        expected_record=case_contract["record"],
    )
    restore_delete_manifest = recompute_eviction_manifest(
        read_json(case_root / "restore/effective_eviction_manifest.json"),
        f"{case_id} Restore intermediate deletion",
        expected_record=case_contract["record"],
    )
    firewall = recompute_case_firewall(
        case_root,
        case_id=case_id,
        case_contract=case_contract,
        branch_results=branch_results,
        run_nonce=run_nonce,
    )
    checks = {
        "same_checkpoint_all_branches": checkpoint_equal,
        "same_prompt_all_branches": prompt_equal,
        "agent_request_diff_is_retrieval_only": agent_request_treatment_only,
        "retrieval_full_one_evicted_zero_restore_same": retrieval_contract,
        "all_capability_probes_denied": all(
            branch["capability"]["all_denied_recomputed"] for branch in branches.values()
        ),
        "agent_and_evaluator_processes_separated": all(
            branch["process_boundary"]["distinct_processes"] for branch in branches.values()
        ),
        "agent_world_has_no_ground_truth": all(
            branch["process_boundary"]["agent_ground_truth_loaded"] is False
            for branch in branches.values()
        ),
        "db_frozen_before_evaluation": all(
            branch["process_boundary"]["db_frozen_before_evaluator"]
            for branch in branches.values()
        ),
        "evaluator_vectors_stable": all(branch["evaluator_stable"] for branch in branches.values()),
        "full_evicted_restore_direction": outcome_direction,
        "full_restore_evaluator_equal": evaluator_full_restore_equal,
        "full_restore_db_byte_equal": db_full_restore_equal,
        "full_restore_plan_equal": plan_full_restore_equal,
        "full_restore_rpc_transcript_byte_equal": rpc_full_restore_equal,
        "restore_same_memory_item": restore_same_item,
        "evicted_effective_eviction_all_pass": evicted_manifest["all_pass_recomputed"],
        "restore_delete_effective_eviction_all_pass": restore_delete_manifest["all_pass_recomputed"],
        "sensitive_logs_redacted": all(
            branch["redaction"]["raw_log_retained"] is False for branch in branches.values()
        ),
        "firewall_private_inputs_absent_pre_and_post_redaction": (
            firewall["pre_redaction_private_match_count"] == 0
            and firewall["persisted_surface_private_match_count"] == 0
            and firewall["pre_redaction_forbidden_private_key_count"] == 0
            and firewall["persisted_surface_forbidden_private_key_count"] == 0
        ),
        "exact_public_tool_allowlist_enforced": all(
            branch["tool_transcript"]["all_calls_exactly_allowlisted"]
            for branch in branches.values()
        ),
    }
    return {
        "case_id": case_id,
        "source_of_truth": "raw branch/checkpoint/DB/evaluator/manifest/probe artifacts; case_summary.json not read",
        "branches": {
            branch: {
                "official_success": data["evaluator"]["success"],
                "passed_tests": data["evaluator"]["passed"],
                "failed_tests": data["evaluator"]["failed"],
                "checkpoint_tree_manifest_root_sha256": data["checkpoint"]["tree_manifest_root_sha256"],
                "db_tree_manifest_root_sha256": data["db_tree"]["tree_manifest_root_sha256"],
                "prompt_logical_lf_sha256": data["hash_contract"]["prompt_logical_lf_sha256"],
                "prompt_file_sha256": data["hash_contract"]["prompt_file_sha256"],
                "structured_agent_plan_logical_lf_sha256": data["hash_contract"]["structured_agent_plan_logical_lf_sha256"],
                "structured_agent_plan_file_sha256": data["hash_contract"]["structured_agent_plan_file_sha256"],
                "capability_probe_count": data["capability"]["probe_count"],
                "api_log_row_count": data["redaction"]["api_log"]["row_count"],
                "api_redaction_count": data["redaction"]["api_redaction_count"],
            }
            for branch, data in branches.items()
        },
        "effective_eviction": evicted_manifest,
        "restore_intermediate_delete": restore_delete_manifest,
        "database_diffs_recomputed": database_diffs,
        "firewall_recomputed": firewall,
        "checks": checks,
        "controller_invocation": {
            "argv_matches_precommit": True,
            "argv": planned_runner_argv,
        },
        "case_pass_recomputed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evidence-first 3A-R gate; never trusts case_summary booleans."
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--execution-freeze", required=True)
    parser.add_argument("--precommit-attestation", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    run_root = resolve_project_path(project_root, args.run_root)
    freeze_path = resolve_project_path(project_root, args.execution_freeze)
    precommit_path = resolve_project_path(project_root, args.precommit_attestation)
    if not run_root.is_dir():
        raise FileNotFoundError(run_root)
    output_path = run_root / "aggregate_gate.json"
    final_manifest_path = run_root / "artifact_manifest.json"
    if output_path.exists() or final_manifest_path.exists():
        raise FileExistsError("Refusing to overwrite aggregate or final artifact manifest")

    freeze = require_mapping(read_json(freeze_path), "execution freeze")
    freeze_result = validate_execution_freeze(
        freeze,
        freeze_path=freeze_path,
        project_root=project_root,
        run_root=run_root,
    )
    attestation = require_mapping(read_json(precommit_path), "precommit attestation")
    attestation_result = validate_run_attestation(
        attestation,
        project_root=project_root,
        run_root=run_root,
        freeze_path=freeze_path,
    )
    frozen_contract = load_frozen_contract(
        project_root=project_root,
        config_path=resolve_project_path(
            project_root, attestation_result["files"]["case_config"]["path"]
        ),
        witnesses_path=resolve_project_path(
            project_root, attestation_result["files"]["witnesses"]["path"]
        ),
    )
    run_environment = validate_run_environment(
        run_root,
        project_root=project_root,
        freeze_result=freeze_result,
        attestation_result=attestation_result,
        case_contract=frozen_contract["contracts"]["workflow"],
    )
    copied_precommit = run_root / "attestation/precommit_attestation.json"
    if not copied_precommit.is_file() or sha256_file(copied_precommit) != sha256_file(precommit_path):
        raise EvidenceError("Run does not contain a byte-identical copy of its pre-run attestation")

    pre_manifest_path = run_root / "pre_aggregate_artifact_manifest.json"
    pre_manifest = require_mapping(read_json(pre_manifest_path), "pre-aggregate artifact manifest")
    verified_pre_manifest = verify_manifest(
        pre_manifest,
        run_root,
        expected_scope="pre_aggregate_evidence",
        expected_excluded_paths=PRE_AGGREGATE_EXCLUSIONS,
    )
    exact_layout = validate_exact_preaggregate_layout(run_root)
    target_distractor_path = run_root / "attestation/target_distractor_probe.json"
    target_distractor = validate_target_distractor_probe(read_json(target_distractor_path))

    cases = [
        recompute_case(
            run_root / "cases" / case_id,
            project_root=project_root,
            case_id=case_id,
            nonce_commitment_sha256=attestation_result["nonce_commitment_sha256"],
            run_nonce=str(attestation["nonce"]),
            freeze_result=freeze_result,
            freeze_id=str(freeze_result["freeze_id"]),
            freeze_sha256=freeze_result["freeze_sha256"],
            planned_runner_argv=attestation_result["planned_runner_argv_by_case"][case_id],
            case_contract=frozen_contract["contracts"][case_id],
        )
        for case_id in CASE_IDS
    ]
    passing_cases = sum(case["case_pass_recomputed"] for case in cases)
    gate_checks = {
        "execution_freeze_recomputed": freeze_result["all_files_equal"],
        "source_data_environment_attestation_recomputed": True,
        "run_environment_recomputed": run_environment["pilot_started"] is False,
        "pre_aggregate_manifest_recomputed": (
            verified_pre_manifest["manifest_root_sha256"]
            == pre_manifest["manifest_root_sha256"]
        ),
        "exact_artifact_layout_recomputed": exact_layout["all_static_paths_exact"],
        "target_distractor_probe_recomputed": all(target_distractor.values()),
        "all_three_cases_pass_raw_gate": passing_cases == len(CASE_IDS),
    }
    gate = {
        "schema_version": "preempt-mem-3a-r-aggregate-gate-v1",
        "run_id": run_root.name,
        "run_root": run_root.relative_to(project_root).as_posix(),
        "evidence_policy": "case_summary boolean fields are ignored; every gate is recomputed from raw checkpoint, branch, DB, evaluator, eviction, capability and attestation evidence",
        "execution_freeze": freeze_result,
        "precommit_attestation": attestation_result,
        "run_environment": run_environment,
        "pre_aggregate_manifest": {
            "schema_version": MANIFEST_SCHEMA,
            "entry_count": verified_pre_manifest["entry_count"],
            "total_bytes": verified_pre_manifest["total_bytes"],
            "manifest_root_sha256": verified_pre_manifest["manifest_root_sha256"],
            "manifest_file_sha256": sha256_file(pre_manifest_path),
        },
        "exact_artifact_layout": exact_layout,
        "target_distractor_probe": target_distractor,
        "cases": cases,
        "passing_cases": passing_cases,
        "total_cases": len(cases),
        "checks": gate_checks,
        "pass_3a_r_gate": all(gate_checks.values()),
    }
    gate["deterministic_verdict"] = (
        "PASS_3A_R_READY_FOR_INDEPENDENT_AUDIT"
        if gate["pass_3a_r_gate"]
        else "FAIL_3A_R_REPAIRABLE"
    )
    write_json_new(output_path, gate)

    final_manifest = build_manifest(
        run_root,
        scope="final_run_evidence",
        exclude_relative_paths=("artifact_manifest.json",),
    )
    write_json_new(final_manifest_path, final_manifest)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    print(f"final_artifact_manifest_sha256={sha256_file(final_manifest_path)}")
    print(f"final_artifact_manifest_root_sha256={final_manifest['manifest_root_sha256']}")


if __name__ == "__main__":
    main()
