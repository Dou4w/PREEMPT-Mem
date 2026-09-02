from __future__ import annotations

"""Controller-side boundary for the structured PREEMPT-Mem agent role.

This module deliberately makes a narrow claim: the deterministic Agent role can
emit only typed JSONL tool calls, and the controller dispatches only an explicit
``app.api`` allowlist. It is *not* a Windows arbitrary-code or filesystem
sandbox. Worker source is copied to a fresh non-project directory and executed
with ``python -I`` so neither its argv nor cwd contains a project path.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from evidence_integrity import canonical_json


PROTOCOL_VERSION = "preempt3a-isolated-tool-rpc-v1"
PUBLIC_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b")
REDACTION_MARKER = re.compile(r"^<REDACTED:[A-Z0-9_]+:[0-9a-f]{16}>$")

# This exact list is mirrored in cases_isolated_v1.json and asserted by tests.
WORKER_ENVIRONMENT_KEYS = (
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONHASHSEED",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)

# These fragments cover AppWorld authentication material and user payloads.
RPC_SENSITIVE_KEY_FRAGMENTS = (
    "token",
    "password",
    "secret",
    "username",
    "email",
    "phone",
    "message",
    "content",
    "amount",
    "result",
    "authorization",
    "bearer",
)


class CapabilityDeniedError(PermissionError):
    """The structured Agent requested a capability outside the exact allowlist."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    # Public tool results must already belong to the JSON data model.  Falling
    # back to repr/str could expose internal object state or host paths.
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(fragment in normalized for fragment in RPC_SENSITIVE_KEY_FRAGMENTS)


def _redaction_marker(kind: str, value: Any, nonce: str) -> str:
    normalized_kind = re.sub(r"[^A-Z0-9_]", "_", kind.upper())[:40] or "VALUE"
    digest = _sha256_text(nonce + "\x00" + normalized_kind + "\x00" + canonical_json(value))[:16]
    return f"<REDACTED:{normalized_kind}:{digest}>"


def _collect_sensitive_literals(value: Any, *, key_hint: str = "") -> set[str]:
    """Collect structurally private scalars so echoed API errors are redacted."""

    if key_hint and _sensitive_key(key_hint):
        if value is None:
            return set()
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            return {str(value)} if str(value) else set()
        literals: set[str] = set()
        if isinstance(value, Mapping):
            for child in value.values():
                literals.update(_collect_sensitive_literals(child, key_hint=key_hint))
        elif isinstance(value, (list, tuple)):
            for child in value:
                literals.update(_collect_sensitive_literals(child, key_hint=key_hint))
        return literals
    literals: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            literals.update(_collect_sensitive_literals(child, key_hint=str(key)))
    elif isinstance(value, (list, tuple)):
        for child in value:
            literals.update(_collect_sensitive_literals(child))
    return literals


def _redact_rpc_value(
    value: Any,
    *,
    nonce: str,
    sensitive_literals: frozenset[str],
    key_hint: str = "",
    path: tuple[Any, ...] = (),
) -> tuple[Any, int]:
    protocol_metadata = bool(
        len(path) == 4
        and path[0] == "transcript"
        and isinstance(path[1], int)
        and (
            (path[2] == "call" and path[3] in {"type", "protocol_version", "request_id", "app", "api"})
            or (
                path[2] == "response"
                and path[3] in {"type", "protocol_version", "request_id", "ok"}
            )
        )
    )
    if protocol_metadata:
        return value, 0
    if key_hint and _sensitive_key(key_hint):
        if value is None:
            return None, 0
        return _redaction_marker(key_hint, value, nonce), 1
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        count = 0
        for key, child in value.items():
            child_redacted, child_count = _redact_rpc_value(
                child,
                nonce=nonce,
                sensitive_literals=sensitive_literals,
                key_hint=str(key),
                path=path + (str(key),),
            )
            redacted[str(key)] = child_redacted
            count += child_count
        return redacted, count
    if isinstance(value, list):
        redacted_items: list[Any] = []
        count = 0
        for child in value:
            child_redacted, child_count = _redact_rpc_value(
                child,
                nonce=nonce,
                sensitive_literals=sensitive_literals,
                path=path + (len(redacted_items),),
            )
            redacted_items.append(child_redacted)
            count += child_count
        return redacted_items, count
    if isinstance(value, tuple):
        return _redact_rpc_value(
            list(value),
            nonce=nonce,
            sensitive_literals=sensitive_literals,
            path=path,
        )
    if isinstance(value, str):
        if BEARER.search(value) or JWT.search(value):
            return _redaction_marker("embedded_secret", value, nonce), 1
        for literal in sorted(sensitive_literals, key=lambda item: (-len(item), item)):
            if literal and literal in value:
                return _redaction_marker("embedded_sensitive", value, nonce), 1
    return value, 0


def _sensitive_findings(value: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _sensitive_key(str(key)) and child is not None:
                if not (isinstance(child, str) and REDACTION_MARKER.fullmatch(child)):
                    findings.append(child_path)
            findings.extend(_sensitive_findings(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_sensitive_findings(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and (BEARER.search(value) or JWT.search(value)):
        findings.append(path)
    return sorted(set(findings))


def redact_rpc_evidence(value: Any, *, nonce: str) -> tuple[Any, dict[str, Any]]:
    """Return deterministic, nonce-bound redaction plus a verifiable attestation."""

    if not isinstance(nonce, str) or not HEX_64.fullmatch(nonce):
        raise ValueError("redaction_nonce must be a lowercase 256-bit hex string")
    literals = frozenset(_collect_sensitive_literals(value))
    redacted, redaction_count = _redact_rpc_value(
        value, nonce=nonce, sensitive_literals=literals
    )
    findings = _sensitive_findings(redacted)
    if findings:
        raise RuntimeError(f"sensitive RPC values remain after redaction: {findings[:10]}")
    return redacted, {
        "schema_version": "preempt-mem-rpc-redaction-v1",
        "algorithm": "sha256(nonce || kind || canonical_value)[:16]",
        "sensitive_key_fragments": list(RPC_SENSITIVE_KEY_FRAGMENTS),
        "redaction_count": redaction_count,
        "sensitive_literal_count": len(literals),
        "post_redaction_finding_count": 0,
        "nonce_commitment_sha256": _sha256_text(
            "PREEMPT-Mem-3A-R-RPC-redaction\x00" + nonce
        ),
        "raw_transcript_retained_in_shareable_artifacts": False,
    }


def _normalize_allowed_tools(world: Any, allowed_tools: Iterable[str]) -> dict[str, set[str]]:
    if isinstance(allowed_tools, (str, bytes)):
        raise TypeError("allowed_tools must be an iterable of exact 'app.api' strings")
    normalized: dict[str, set[str]] = {}
    seen: set[str] = set()
    for tool in allowed_tools:
        if not isinstance(tool, str) or tool.count(".") != 1:
            raise ValueError(f"malformed exact tool name: {tool!r}")
        app, api = tool.split(".")
        if not PUBLIC_NAME.fullmatch(app) or not PUBLIC_NAME.fullmatch(api):
            raise ValueError(f"non-public exact tool name: {tool!r}")
        if tool in seen:
            raise ValueError(f"duplicate exact tool name: {tool}")
        seen.add(tool)
        if app not in world.apis or api not in world.apis[app]:
            raise ValueError(f"allowlisted tool is not an AppWorld public API: {tool}")
        normalized.setdefault(app, set()).add(api)
    if not seen:
        raise ValueError("allowed_tools must not be empty")
    return normalized


class PublicAppWorldGateway:
    """Exact dispatcher over an explicit subset of AppWorld public APIs."""

    def __init__(self, world: Any, *, allowed_tools: Iterable[str]) -> None:
        if getattr(getattr(world, "task", None), "ground_truth", None) is not None:
            raise RuntimeError("agent world must be initialized with load_ground_truth=False")
        self._world = world
        self._allowed = _normalize_allowed_tools(world, allowed_tools)

    @property
    def allowlist(self) -> list[str]:
        return sorted(f"{app}.{api}" for app, apis in self._allowed.items() for api in apis)

    def dispatch(self, message: dict[str, Any]) -> Any:
        required = {"type", "protocol_version", "request_id", "app", "api", "arguments"}
        if not isinstance(message, dict) or set(message) != required:
            raise CapabilityDeniedError("tool call schema is not exact")
        if message.get("type") != "tool_call" or message.get("protocol_version") != PROTOCOL_VERSION:
            raise CapabilityDeniedError("invalid tool call envelope")
        request_id = message.get("request_id")
        app = message.get("app")
        api = message.get("api")
        arguments = message.get("arguments")
        if not isinstance(request_id, str) or not request_id:
            raise CapabilityDeniedError("request_id must be a non-empty string")
        if not isinstance(app, str) or not PUBLIC_NAME.fullmatch(app):
            raise CapabilityDeniedError("app name is outside the public namespace")
        if not isinstance(api, str) or not PUBLIC_NAME.fullmatch(api):
            raise CapabilityDeniedError("API name is outside the public namespace")
        if not isinstance(arguments, dict):
            raise CapabilityDeniedError("tool arguments must be an object")
        if app not in self._allowed or api not in self._allowed[app]:
            raise CapabilityDeniedError(f"AppWorld API is outside the exact allowlist: {app}.{api}")
        function = self._world.apis[app][api]
        return _json_safe(function(**arguments))


CAPABILITY_PROBES: tuple[tuple[str, str, str, dict[str, Any]], ...] = (
    ("caller_secret", "controller", "read_caller_secret", {}),
    ("inspect_stack", "runtime", "inspect_stack", {}),
    ("branch", "controller", "get_branch", {}),
    ("project_file", "host_files", "read_project_file", {"path": "sentinel"}),
    ("world_object", "controller", "get_world", {}),
    ("memory_store", "controller", "get_store", {}),
    ("controller_vault", "controller", "get_vault", {}),
    ("ground_truth", "ground_truth", "load", {}),
    ("evaluation_code", "evaluation", "read_code", {}),
    ("controller_directory", "host_files", "list_controller_directory", {}),
)


def _minimal_worker_environment() -> dict[str, str]:
    # No PATH/PYTHONPATH/APPWORLD_ROOT/branch/experiment/controller variables.
    environment = {
        key: os.environ[key]
        for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    if set(environment) != set(WORKER_ENVIRONMENT_KEYS):
        missing = sorted(set(WORKER_ENVIRONMENT_KEYS) - set(environment))
        extra = sorted(set(environment) - set(WORKER_ENVIRONMENT_KEYS))
        raise RuntimeError(f"worker environment contract mismatch; missing={missing}, extra={extra}")
    return environment


def _project_root_for_worker(worker_path: Path) -> Path:
    if worker_path.parent.name == "src" and worker_path.parent.parent.name == "third_step_a":
        return worker_path.parents[2]
    return worker_path.parent


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _external_interpreter(project_root: Path) -> Path:
    """Resolve a stdlib interpreter whose real argv is outside the project.

    Final runs use a project-local virtual environment for AppWorld, but the
    stdlib-only worker must not inherit that project path in argv.  CPython
    exposes the base interpreter used to create the venv as ``_base_executable``.
    """

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
        if not _is_within(resolved, project_root):
            return resolved
    raise RuntimeError("no Python interpreter outside the project is available for the worker")


def _launch_copied_worker(
    *, worker_path: Path, sandbox_directory: Path, role: str
) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    worker_path = worker_path.resolve(strict=True)
    sandbox_directory = sandbox_directory.resolve()
    project_root = _project_root_for_worker(worker_path).resolve()
    if _is_within(sandbox_directory, project_root):
        raise ValueError("worker sandbox must be outside the project tree")
    sandbox_directory.mkdir(parents=True, exist_ok=False)
    copied_worker = sandbox_directory / f"{role}_worker.py"
    shutil.copyfile(worker_path, copied_worker)
    source_sha256 = sha256_file(worker_path)
    copied_sha256 = sha256_file(copied_worker)
    if copied_sha256 != source_sha256:
        raise RuntimeError("copied worker hash differs from the attested source")
    environment = _minimal_worker_environment()
    interpreter = _external_interpreter(project_root)
    command = [str(interpreter), "-I", copied_worker.name]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        cwd=sandbox_directory,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        creationflags=creationflags,
    )
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    role_name = "agent_capability_probe" if role == "capability_probe" else role
    return process, {
        "role": role_name,
        "pid": process.pid,
        "argv": [interpreter.name, "-I", copied_worker.name],
        "cwd": sandbox_directory.name,
        "argv_contains_project_path": False,
        "cwd_contains_project_path": False,
        "worker_command_contains_project_path": False,
        "project_root_path_disclosed": False,
        "environment_key_names": sorted(environment),
        "interpreter_sha256": sha256_file(interpreter),
        "interpreter_outside_project": True,
        "source_worker_sha256": source_sha256,
        "copied_worker_sha256": copied_sha256,
        "source_copy_hash_equal": source_sha256 == copied_sha256,
        "worker_copied_to_fresh_external_sandbox": True,
        "worker_copied_to_temporary_directory": True,
        "python_isolated_flag": True,
        "boundary": "structured_json_tool_call_rpc",
        "structured_tool_boundary_only": True,
        "arbitrary_code_sandbox_claimed": False,
        "os_filesystem_sandbox_claimed": False,
        "appworld_imported_by_worker": False,
    }


def _finish_process(
    process: subprocess.Popen[str], process_attestation: dict[str, Any]
) -> tuple[int, str, dict[str, Any]]:
    assert process.stderr is not None and process.stdout is not None
    try:
        return_code = process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        return_code = process.wait(timeout=10)
    stderr = process.stderr.read()
    process.stdout.close()
    process.stderr.close()
    process_attestation.update(
        {
            "return_code": return_code,
            "exit_code": return_code,
            "stderr_sha256": _sha256_text(stderr),
            "stderr_empty": not bool(stderr),
        }
    )
    return return_code, stderr, process_attestation


def run_capability_probes(
    gateway: PublicAppWorldGateway,
    *,
    worker_path: Path,
    sandbox_directory: Path,
) -> dict[str, Any]:
    """Run all ten negative probes from a separate Agent-role process."""

    process, process_attestation = _launch_copied_worker(
        worker_path=worker_path,
        sandbox_directory=sandbox_directory,
        role="capability_probe",
    )
    assert process.stdin is not None and process.stdout is not None
    probes: list[dict[str, Any]] = []
    transcript: list[dict[str, Any]] = []
    final_message: dict[str, Any] | None = None
    for index, (name, app, api, arguments) in enumerate(CAPABILITY_PROBES, start=1):
        line = process.stdout.readline()
        if not line:
            break
        message = json.loads(line)
        if message.get("type") == "final":
            final_message = message
            break
        expected = {
            "type": "tool_call",
            "protocol_version": PROTOCOL_VERSION,
            "request_id": f"probe-{index:04d}-{name}",
            "app": app,
            "api": api,
            "arguments": arguments,
        }
        protocol_exact = message == expected
        denied = False
        error_type = "ProtocolError"
        if protocol_exact:
            try:
                gateway.dispatch(message)
            except CapabilityDeniedError as error:
                denied = True
                error_type = type(error).__name__
        response = {
            "type": "tool_result",
            "protocol_version": PROTOCOL_VERSION,
            "request_id": expected["request_id"],
            "ok": False,
            "result": {
                "error_code": "CAPABILITY_DENIED" if denied else "PROBE_PROTOCOL_FAILURE",
                "error_type": error_type,
            },
        }
        process.stdin.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        process.stdin.flush()
        transcript.append({"request": message, "response": response})
        probes.append(
            {
                "probe": name,
                "agent_role_request": {"app": message.get("app"), "api": message.get("api")},
                "protocol_request_exact": protocol_exact,
                "response_error_code": response["result"]["error_code"],
                "protocol_error": response["result"]["error_code"],
                "result": "PASS" if denied and protocol_exact else "FAIL",
                "denied": denied,
            }
        )
    if final_message is None:
        line = process.stdout.readline()
    if line:
        final_message = json.loads(line)
    transcript.append({"final": final_message})
    process.stdin.close()
    return_code, stderr, process_attestation = _finish_process(process, process_attestation)
    expected_names = [item[0] for item in CAPABILITY_PROBES]
    worker_verified = bool(
        final_message
        and final_message.get("type") == "final"
        and final_message.get("protocol_version") == PROTOCOL_VERSION
        and final_message.get("ok") is True
        and final_message.get("result", {}).get("all_denied") is True
        and final_message.get("result", {}).get("probe_names") == expected_names
    )
    all_pass = bool(
        len(probes) == len(CAPABILITY_PROBES)
        and all(item["result"] == "PASS" for item in probes)
        and worker_verified
        and return_code == 0
        and not stderr
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "execution_role": "separate_agent_role_capability_probe_worker",
        "boundary_claim": "structured JSONL tool capability boundary only",
        "probe_count": len(probes),
        "required_probe_count": len(CAPABILITY_PROBES),
        "all_pass": all_pass,
        "worker_verified_all_denied": worker_verified,
        "probes": probes,
        "transcript": transcript,
        "transcript_row_count": len(transcript),
        "transcript_virtual_sha256": hashlib.sha256(
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
                for row in transcript
            ).encode("utf-8")
        ).hexdigest(),
        "process_attestation": process_attestation,
    }


def run_structured_agent(
    *,
    world: Any,
    target_instruction: str,
    retrieval_results: list[dict[str, Any]],
    allowed_tools: Iterable[str],
    redaction_nonce: str,
    worker_path: Path,
    sandbox_directory: Path,
    max_tool_calls: int = 500,
) -> dict[str, Any]:
    gateway = PublicAppWorldGateway(world, allowed_tools=allowed_tools)
    process, process_attestation = _launch_copied_worker(
        worker_path=worker_path,
        sandbox_directory=sandbox_directory,
        role="structured_agent",
    )
    assert process.stdin is not None and process.stdout is not None
    initialize = {
        "type": "initialize",
        "protocol_version": PROTOCOL_VERSION,
        "target_instruction": target_instruction,
        "retrieval_results": retrieval_results,
    }
    process.stdin.write(json.dumps(initialize, ensure_ascii=False, sort_keys=True) + "\n")
    process.stdin.flush()
    raw_transcript: list[dict[str, Any]] = []
    final_message: dict[str, Any] | None = None
    tool_call_count = 0
    while True:
        line = process.stdout.readline()
        if not line:
            break
        message = json.loads(line)
        if message.get("type") == "final":
            final_message = message
            break
        tool_call_count += 1
        if tool_call_count > max_tool_calls:
            process.kill()
            raise RuntimeError(f"structured agent exceeded max_tool_calls={max_tool_calls}")
        try:
            result = gateway.dispatch(message)
            response = {
                "type": "tool_result",
                "protocol_version": PROTOCOL_VERSION,
                "request_id": message.get("request_id"),
                "ok": True,
                "result": result,
            }
        except Exception as error:
            response = {
                "type": "tool_result",
                "protocol_version": PROTOCOL_VERSION,
                "request_id": message.get("request_id"),
                "ok": False,
                "result": {
                    "error_code": (
                        "CAPABILITY_DENIED"
                        if isinstance(error, CapabilityDeniedError)
                        else "PUBLIC_API_ERROR"
                    ),
                    "error_type": type(error).__name__,
                },
            }
        raw_transcript.append({"call": message, "response": response})
        process.stdin.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        process.stdin.flush()
    process.stdin.close()
    return_code, stderr, process_attestation = _finish_process(process, process_attestation)
    if final_message is None:
        raise RuntimeError(f"structured agent exited without final message; rc={return_code}; stderr={stderr}")
    if (
        return_code != 0
        or set(final_message) != {
            "type",
            "protocol_version",
            "ok",
            "result",
            "tool_call_count",
        }
        or final_message.get("type") != "final"
        or final_message.get("protocol_version") != PROTOCOL_VERSION
        or final_message.get("ok") is not True
        or final_message.get("tool_call_count") != tool_call_count
    ):
        raise RuntimeError(
            "structured agent failed: "
            + json.dumps(
                {"return_code": return_code, "final": final_message, "stderr": stderr},
                ensure_ascii=False,
            )
        )
    raw_evidence = {"transcript": raw_transcript, "agent_result": final_message.get("result")}
    redacted_evidence, redaction_attestation = redact_rpc_evidence(
        raw_evidence, nonce=redaction_nonce
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "result": redacted_evidence["agent_result"],
        "tool_call_count": tool_call_count,
        "transcript_redacted": redacted_evidence["transcript"],
        "final_message_redacted": {
            "type": "final",
            "protocol_version": PROTOCOL_VERSION,
            "ok": True,
            "result": redacted_evidence["agent_result"],
            "tool_call_count": tool_call_count,
        },
        # Controller-memory only. The runner must redact and then discard this;
        # it must never serialize this field into shareable run artifacts.
        "transcript_raw_controller_only": raw_transcript,
        "agent_result_raw_controller_only": final_message.get("result"),
        "redaction_attestation": redaction_attestation,
        "capability_allowlist": gateway.allowlist,
        "initialization_attestation": {
            "exact_fields": sorted(initialize),
            "target_instruction_sha256": _sha256_text(target_instruction),
            "retrieval_results_sha256": _sha256_text(canonical_json(retrieval_results)),
            "private_controller_fields_present": False,
        },
        "process_attestation": process_attestation,
    }
