from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import re
import sys
import warnings
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ATTESTATION_SCHEMA = "preempt-mem-run-attestation-v1"
MANIFEST_SCHEMA = "preempt-mem-artifact-manifest-v1"
REDACTION_SCHEMA = "preempt-mem-deterministic-redaction-v1"

_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b"
)
_REDACTED_RE = re.compile(
    r"^(?:<REDACTED>|Bearer <REDACTED>|<REDACTED:[A-Z0-9_]+:[0-9a-f]{16}>)$"
)

# These keys are private in evidence artifacts even when AppWorld uses synthetic data.
# Endpoint, method, status and schema keys intentionally remain visible for auditing.
SENSITIVE_KEY_PARTS = (
    "access_token",
    "api_key",
    "amount",
    "authorization",
    "bearer",
    "cookie",
    "content",
    "credential",
    "email",
    "description",
    "destination_file_path",
    "directory_path",
    "file_path",
    "first_name",
    "last_name",
    "message",
    "password",
    "phone",
    "phone_number",
    "query",
    "result",
    "refresh_token",
    "secret",
    "source_file_path",
    "token",
    "username",
)

DEFAULT_TREE_IGNORES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
    }
)
DEFAULT_SUFFIX_IGNORES = frozenset({".pyc", ".pyo"})


class EvidenceError(RuntimeError):
    """Raised when evidence is absent, malformed, or fails recomputation."""


def canonical_value(value: Any) -> Any:
    """Return a JSON-safe, deterministically ordered representation.

    This deliberately supports dataclasses, sets and Path values because evidence
    objects use all three.  Mapping keys must be scalar so collisions cannot be
    hidden by stringification.
    """

    if is_dataclass(value) and not isinstance(value, type):
        return canonical_value(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        if "__canonical_type__" in value:
            raise ValueError("__canonical_type__ is reserved for canonical type tags")
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, (str, int, float, bool)) and key is not None:
                raise TypeError(f"Unsupported mapping key type: {type(key).__name__}")
            text_key = json.dumps(key, ensure_ascii=False, sort_keys=True) if not isinstance(key, str) else key
            if text_key in normalized:
                raise ValueError(f"Canonical mapping key collision: {text_key!r}")
            normalized[text_key] = canonical_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (set, frozenset)):
        items = [canonical_value(item) for item in value]
        return {
            "__canonical_type__": (
                "frozenset" if isinstance(value, frozenset) else "set"
            ),
            "items": sorted(items, key=canonical_json),
        }
    if isinstance(value, tuple):
        return [canonical_value(item) for item in value]
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported canonical value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def git_head_from_metadata(repository: Path) -> str:
    """Resolve HEAD without invoking git or changing the user's safe.directory config."""

    git_directory = repository / ".git"
    if git_directory.is_file():
        marker = git_directory.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir:"):
            raise EvidenceError(f"Malformed gitdir marker: {git_directory}")
        git_directory = (repository / marker.split(":", 1)[1].strip()).resolve()
    head = (git_directory / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise EvidenceError(f"Malformed detached HEAD: {repository}")
        return head
    reference = head.removeprefix("ref: ")
    loose = git_directory / reference
    if loose.is_file():
        commit = loose.read_text(encoding="utf-8").strip()
        if re.fullmatch(r"[0-9a-f]{40}", commit):
            return commit
    packed = git_directory / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(("#", "^")):
                commit, name = line.split(" ", 1)
                if name == reference and re.fullmatch(r"[0-9a-f]{40}", commit):
                    return commit
    raise EvidenceError(f"Cannot resolve git HEAD: {repository}")


def normalize_logical_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def logical_lf_sha256(text: str) -> str:
    return sha256_bytes(normalize_logical_lf(text).encode("utf-8"))


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Missing required evidence: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid JSON evidence {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise EvidenceError(f"Missing required JSONL evidence: {path}") from exc
    rows: list[Any] = []
    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise EvidenceError(f"Invalid JSONL {path}:{line_number}: {exc}") from exc
    return rows


def write_json_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_ignored(relative: Path, ignored_names: frozenset[str]) -> bool:
    return any(part in ignored_names for part in relative.parts)


def tree_entries(
    root: Path,
    *,
    exclude_relative_paths: Iterable[str] = (),
    ignored_names: frozenset[str] = DEFAULT_TREE_IGNORES,
    ignored_suffixes: frozenset[str] = DEFAULT_SUFFIX_IGNORES,
) -> list[dict[str, Any]]:
    if not root.is_dir():
        raise EvidenceError(f"Tree root is not a directory: {root}")
    excluded = {item.replace("\\", "/") for item in exclude_relative_paths}
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        if path.is_symlink():
            raise EvidenceError(f"Symlink is not allowed in attested tree: {path}")
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if relative in excluded or _is_ignored(relative_path, ignored_names):
            continue
        if path.suffix.lower() in ignored_suffixes:
            continue
        data = path.read_bytes()
        entries.append({"path": relative, "size": len(data), "sha256": sha256_bytes(data)})
    return entries


def manifest_root_sha256(entries: Sequence[Mapping[str, Any]]) -> str:
    normalized = [
        {"path": str(item["path"]).replace("\\", "/"), "size": int(item["size"]), "sha256": str(item["sha256"])}
        for item in entries
    ]
    normalized.sort(key=lambda item: item["path"])
    return sha256_json(normalized)


def build_manifest(
    root: Path,
    *,
    scope: str,
    exclude_relative_paths: Iterable[str] = (),
) -> dict[str, Any]:
    excluded = sorted({item.replace("\\", "/") for item in exclude_relative_paths})
    entries = tree_entries(root, exclude_relative_paths=excluded)
    return {
        "schema_version": MANIFEST_SCHEMA,
        "scope": scope,
        "root_name": root.name,
        "excluded_paths": excluded,
        "entry_count": len(entries),
        "total_bytes": sum(item["size"] for item in entries),
        "manifest_root_sha256": manifest_root_sha256(entries),
        "entries": entries,
    }


def verify_manifest(
    manifest: Mapping[str, Any],
    root: Path,
    *,
    expected_scope: str,
    expected_excluded_paths: Iterable[str],
) -> dict[str, Any]:
    expected_excluded = sorted(
        {item.replace("\\", "/") for item in expected_excluded_paths}
    )
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise EvidenceError("Unknown artifact manifest schema")
    if manifest.get("scope") != expected_scope:
        raise EvidenceError("Artifact manifest scope mismatch")
    if manifest.get("excluded_paths") != expected_excluded:
        raise EvidenceError("Artifact manifest exclusions do not match the gate contract")
    recomputed = build_manifest(
        root, scope=expected_scope, exclude_relative_paths=expected_excluded
    )
    for key in ("entry_count", "total_bytes", "manifest_root_sha256", "entries"):
        if manifest.get(key) != recomputed[key]:
            raise EvidenceError(f"Artifact manifest mismatch: {key}")
    return recomputed


def nonce_commitment(run_id: str, nonce: str) -> str:
    return sha256_bytes(f"PREEMPT-Mem-3A-R:{run_id}:{nonce}".encode("utf-8"))


def validate_run_attestation(
    attestation: Mapping[str, Any],
    *,
    project_root: Path,
    run_root: Path,
    freeze_path: Path,
) -> dict[str, Any]:
    if attestation.get("schema_version") != ATTESTATION_SCHEMA:
        raise EvidenceError("Unknown precommit attestation schema")
    run_id = run_root.name
    if attestation.get("run_id") != run_id:
        raise EvidenceError("Precommit attestation run_id mismatch")
    expected_relative = run_root.relative_to(project_root).as_posix()
    if attestation.get("run_relative_path") != expected_relative:
        raise EvidenceError("Precommit attestation run path mismatch")
    nonce = attestation.get("nonce")
    if not isinstance(nonce, str) or not _HEX_64_RE.fullmatch(nonce):
        raise EvidenceError("Run nonce must be a fresh 256-bit lowercase hex value")
    if attestation.get("nonce_commitment_sha256") != nonce_commitment(run_id, nonce):
        raise EvidenceError("Run nonce commitment mismatch")
    command_argv = attestation.get("command_argv")
    if not isinstance(command_argv, list) or not command_argv or not all(
        isinstance(item, str) and item for item in command_argv
    ):
        raise EvidenceError("Precommit attestation must bind a non-empty argv")
    planned_runner = attestation.get("planned_runner_argv_by_case")
    required_cases = {"workflow", "gotcha", "constraint_permission"}
    if not isinstance(planned_runner, Mapping) or set(planned_runner) != required_cases:
        raise EvidenceError("Precommit attestation must bind runner argv for exactly three smoke cases")
    for case_id, argv in planned_runner.items():
        if not isinstance(argv, list) or not argv or not all(
            isinstance(item, str) and item for item in argv
        ):
            raise EvidenceError(f"Malformed planned runner argv: {case_id}")

    trees = attestation.get("trees")
    required_trees = {"harness_source", "appworld_source", "appworld_data"}
    if not isinstance(trees, Mapping) or set(trees) != required_trees:
        raise EvidenceError(f"Attested trees must be exactly {sorted(required_trees)}")
    tree_results: dict[str, Any] = {}
    for name in sorted(required_trees):
        record = trees[name]
        if not isinstance(record, Mapping):
            raise EvidenceError(f"Malformed tree attestation: {name}")
        relative = record.get("path")
        if not isinstance(relative, str):
            raise EvidenceError(f"Missing attested tree path: {name}")
        root = (project_root / relative).resolve()
        if project_root != root and project_root not in root.parents:
            raise EvidenceError(f"Attested tree escapes project: {relative}")
        entries = tree_entries(root)
        recomputed = {
            "file_count": len(entries),
            "total_bytes": sum(item["size"] for item in entries),
            "tree_manifest_root_sha256": manifest_root_sha256(entries),
        }
        for key, actual in recomputed.items():
            if record.get(key) != actual:
                raise EvidenceError(f"Attested tree mismatch {name}:{key}")
        if name == "appworld_source":
            commit = git_head_from_metadata(root)
            if record.get("git_commit") != commit:
                raise EvidenceError("Attested AppWorld source commit mismatch")
            recomputed["git_commit"] = commit
        tree_results[name] = {"path": relative, **recomputed}

    files = attestation.get("files")
    required_files = {"case_config", "environment_spec", "execution_freeze", "witnesses"}
    if not isinstance(files, Mapping) or set(files) != required_files:
        raise EvidenceError(f"Attested files must be exactly {sorted(required_files)}")
    file_results: dict[str, Any] = {}
    for name in sorted(required_files):
        record = files[name]
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise EvidenceError(f"Malformed file attestation: {name}")
        path = (project_root / record["path"]).resolve()
        if project_root != path and project_root not in path.parents:
            raise EvidenceError(f"Attested file escapes project: {path}")
        actual = sha256_file(path)
        if record.get("sha256") != actual:
            raise EvidenceError(f"Attested file mismatch: {name}")
        file_results[name] = {"path": record["path"], "sha256": actual}
    if Path(file_results["execution_freeze"]["path"]).as_posix() != freeze_path.relative_to(project_root).as_posix():
        raise EvidenceError("Attestation binds a different execution freeze")

    environment = attestation.get("environment")
    if not isinstance(environment, Mapping):
        raise EvidenceError("Missing environment attestation")
    environment_spec = read_json(project_root / file_results["environment_spec"]["path"])
    if not isinstance(environment_spec, Mapping):
        raise EvidenceError("Environment spec must be a JSON object")
    if (
        environment_spec.get("schema_version")
        != "preempt-mem-3a-r-environment-v1"
        or environment_spec.get("network_dependencies") != []
        or environment_spec.get("pilot_started") is not False
    ):
        raise EvidenceError("Environment spec schema/network/Pilot contract mismatch")
    base_spec = environment_spec.get("base")
    appworld_spec = environment_spec.get("appworld")
    if not isinstance(base_spec, Mapping) or not isinstance(appworld_spec, Mapping):
        raise EvidenceError("Environment spec must define base and appworld objects")
    controller_environment = environment_spec.get("controller_environment")
    if controller_environment != {
        "APPWORLD_ROOT": "third_step_a/appworld_root",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "PYTHONWARNINGS": "ignore",
    }:
        raise EvidenceError("Environment spec controller environment mismatch")
    agent_boundary = environment_spec.get("agent_boundary")
    if not isinstance(agent_boundary, Mapping) or (
        agent_boundary.get("transport") != "typed JSONL over stdin/stdout"
        or agent_boundary.get("arbitrary_model_generated_code") is not False
        or agent_boundary.get("worker_copied_to_fresh_temporary_directory") is not True
        or agent_boundary.get("python_isolated_flag") != "-I"
        or agent_boundary.get("project_path_sent_to_agent") is not False
        or agent_boundary.get("ground_truth_loaded") is not False
        or "not a general Windows arbitrary-code sandbox"
        not in str(agent_boundary.get("security_scope", ""))
    ):
        raise EvidenceError("Environment spec Agent boundary mismatch")
    evaluator_boundary = environment_spec.get("evaluator_boundary")
    if not isinstance(evaluator_boundary, Mapping) or (
        evaluator_boundary.get("entrypoint") != "appworld.evaluator.evaluate_task"
        or evaluator_boundary.get("processes_per_frozen_db") != 2
        or evaluator_boundary.get("starts_after_agent_exit_and_db_freeze") is not True
        or evaluator_boundary.get("ground_truth_loaded") is not True
    ):
        raise EvidenceError("Environment spec evaluator boundary mismatch")
    critical_distributions = environment_spec.get("critical_python_distributions")
    if not isinstance(critical_distributions, Mapping) or not critical_distributions:
        raise EvidenceError("Environment spec has no critical Python distributions")
    actual_distributions = {
        str(name): importlib.metadata.version(str(name))
        for name in sorted(critical_distributions)
    }
    if actual_distributions != dict(critical_distributions):
        raise EvidenceError(
            f"Critical distribution mismatch: expected={critical_distributions}, actual={actual_distributions}"
        )
    expected_source_relative = str(appworld_spec.get("source_path", ""))
    expected_data_relative = str(appworld_spec.get("data_path", ""))
    if tree_results["appworld_source"]["path"] != expected_source_relative:
        raise EvidenceError("Environment spec/source tree path mismatch")
    if tree_results["appworld_data"]["path"] != expected_data_relative:
        raise EvidenceError("Environment spec/data tree path mismatch")
    appworld_source = (project_root / expected_source_relative).resolve()
    appworld_data = (project_root / expected_data_relative).resolve()
    python_executable = (project_root / str(base_spec.get("python_executable", ""))).resolve()
    if python_executable != Path(sys.executable).resolve():
        raise EvidenceError("Environment spec binds a different Python executable")
    if base_spec.get("python_version") != platform.python_version():
        raise EvidenceError("Environment spec Python version mismatch")
    if base_spec.get("operating_system") != platform.platform():
        raise EvidenceError("Environment spec operating system mismatch")
    if base_spec.get("python_executable_sha256") != sha256_file(Path(sys.executable)):
        raise EvidenceError("Environment spec Python executable hash mismatch")
    source_commit = git_head_from_metadata(appworld_source)
    if appworld_spec.get("source_commit") != source_commit:
        raise EvidenceError("Environment spec AppWorld source commit mismatch")
    code_version = importlib.metadata.version("appworld")
    if appworld_spec.get("code_version") != code_version:
        raise EvidenceError("Environment spec AppWorld code version mismatch")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import appworld
    appworld_module_path = Path(appworld.__file__).resolve()
    if appworld_source not in appworld_module_path.parents:
        raise EvidenceError("Runtime AppWorld module is outside the attested vendor source tree")
    direct_url_text = importlib.metadata.distribution("appworld").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        raise EvidenceError("Runtime AppWorld distribution has no direct_url.json")
    try:
        direct_url_document = json.loads(direct_url_text)
    except json.JSONDecodeError as error:
        raise EvidenceError("Runtime AppWorld direct_url.json is malformed") from error
    if direct_url_document.get("dir_info", {}).get("editable") is not True:
        raise EvidenceError("Runtime AppWorld distribution is not the attested editable source")
    data_version = (appworld_data / "version.txt").read_text(
        encoding="utf-8"
    ).strip()
    if appworld_spec.get("data_version") != data_version:
        raise EvidenceError("Environment spec AppWorld data version mismatch")
    expected_environment = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "python_executable_sha256": sha256_file(Path(sys.executable)),
        "critical_python_distributions": actual_distributions,
        "appworld_source_commit": source_commit,
        "appworld_code_version": code_version,
        "appworld_module_relative_path": appworld_module_path.relative_to(
            project_root
        ).as_posix(),
        "appworld_module_file_sha256": sha256_file(appworld_module_path),
        "appworld_distribution_direct_url_sha256": sha256_bytes(
            direct_url_text.encode("utf-8")
        ),
        "appworld_distribution_editable": True,
        "appworld_data_version": data_version,
    }
    for key, actual in expected_environment.items():
        if environment.get(key) != actual:
            raise EvidenceError(f"Environment attestation mismatch: {key}")
    return {
        "run_id": run_id,
        "nonce_commitment_sha256": attestation["nonce_commitment_sha256"],
        "trees": tree_results,
        "files": file_results,
        "environment": expected_environment,
        "planned_runner_argv_by_case": {
            case_id: list(planned_runner[case_id]) for case_id in sorted(required_cases)
        },
    }


def _sensitive_key(key: str) -> bool:
    lowered = key.casefold().replace("-", "_")
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def _redaction_marker(kind: str, value: Any, nonce: str) -> str:
    kind_text = re.sub(r"[^A-Z0-9_]", "_", kind.upper())[:40] or "VALUE"
    digest = sha256_bytes(
        (nonce + "\x00" + kind_text + "\x00" + canonical_json(value)).encode("utf-8")
    )[:16]
    return f"<REDACTED:{kind_text}:{digest}>"


def redact_sensitive(value: Any, *, nonce: str, key_hint: str = "") -> tuple[Any, int]:
    """Deterministically redact private values while retaining evidence structure."""

    if key_hint and _sensitive_key(key_hint):
        if value is None:
            return None, 0
        return _redaction_marker(key_hint, value, nonce), 1
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        count = 0
        for key, item in value.items():
            item_redacted, item_count = redact_sensitive(item, nonce=nonce, key_hint=str(key))
            redacted[str(key)] = item_redacted
            count += item_count
        return redacted, count
    if isinstance(value, list):
        redacted_items: list[Any] = []
        count = 0
        for item in value:
            item_redacted, item_count = redact_sensitive(item, nonce=nonce)
            redacted_items.append(item_redacted)
            count += item_count
        return redacted_items, count
    if isinstance(value, tuple):
        return redact_sensitive(list(value), nonce=nonce)
    if isinstance(value, str):
        matches = list(_BEARER_RE.finditer(value)) + list(_JWT_RE.finditer(value))
        if matches:
            return _redaction_marker("embedded_secret", value, nonce), 1
    return value, 0


def sensitive_findings(value: Any, *, path: str = "$") -> list[str]:
    """Find raw secrets/private fields in an artifact expected to be redacted."""

    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if _sensitive_key(str(key)) and item is not None:
                if not (isinstance(item, str) and _REDACTED_RE.fullmatch(item)):
                    findings.append(item_path)
            findings.extend(sensitive_findings(item, path=item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(sensitive_findings(item, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        if _BEARER_RE.search(value) or _JWT_RE.search(value):
            findings.append(path)
    return sorted(set(findings))


def assert_redacted_jsonl(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    findings: list[str] = []
    for index, row in enumerate(rows):
        findings.extend(sensitive_findings(row, path=f"$[{index}]"))
    if findings:
        raise EvidenceError(f"Unredacted sensitive API/RPC evidence in {path}: {findings[:10]}")
    return {"path": path.name, "row_count": len(rows), "file_sha256": sha256_file(path)}


def redact_jsonl_file_new(
    raw_path: Path,
    output_path: Path,
    *,
    nonce: str,
    nonce_commitment_sha256: str,
) -> dict[str, Any]:
    """Write a deterministic redacted JSONL copy and return its audit record.

    The caller must keep the raw source outside the shareable run and remove it
    through its own lifecycle.  This helper never mutates or deletes the source.
    """

    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite redacted evidence: {output_path}")
    rows = read_jsonl(raw_path)
    redacted_rows: list[Any] = []
    redaction_count = 0
    for row in rows:
        redacted, count = redact_sensitive(row, nonce=nonce)
        redacted_rows.append(redacted)
        redaction_count += count
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in redacted_rows
    )
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
    assert_redacted_jsonl(output_path)
    return {
        "schema_version": REDACTION_SCHEMA,
        "raw_file_sha256": sha256_file(raw_path),
        "raw_row_count": len(rows),
        "raw_file_retained_in_shareable_artifacts": False,
        "redacted_file": output_path.name,
        "redacted_file_sha256": sha256_file(output_path),
        "redacted_row_count": len(redacted_rows),
        "redaction_count": redaction_count,
        "nonce_commitment_sha256": nonce_commitment_sha256,
    }
