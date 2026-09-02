#!/usr/bin/env python3
"""Generate the repository content audit and external-asset index.

The script emits only file metadata and hashes. It never prints file contents.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


AUDIT_REL = "docs/REPOSITORY_CONTENT_AUDIT_2026-09-02.md"
EXTERNAL_REL = "docs/EXTERNAL_ASSET_INDEX.md"
BASELINE_REL = "docs/TRACKED_FILE_SHA256_BASELINE_2026-09-02.tsv"
CANDIDATE_SOURCE = "PREEMPT-Mem_论文内容与候选统一设计报告取舍说明_2026-09-01 (1).md"
CANDIDATE_COPY = f"research/candidate_inputs/{CANDIDATE_SOURCE}"


@dataclass(frozen=True)
class Decision:
    category: str
    action: str
    reason: str


TRACKED_EVIDENCE_NAMES = {
    "aggregate_gate.json",
    "artifact_manifest.json",
    "pre_aggregate_artifact_manifest.json",
    "environment.json",
    "case_summary.json",
    "checkpoint_manifest.json",
    "case_agent_exit_barrier.json",
    "firewall_leakage_manifest.json",
    "raw_controller_firewall_scan.json",
    "memory_provenance.json",
    "source_episode.json",
    "target_relationship.json",
    "witness.json",
    "branch_result.json",
    "effective_eviction_manifest.json",
    "effective_eviction_pre_agent_manifest.json",
    "db_freeze_attestation.json",
    "api_log_redaction_attestation.json",
    "capability_process_attestation.json",
    "agent_process_attestation.json",
    "evaluator_process_attestation.json",
    "post_agent_controller_canaries.json",
    "evaluator_first.json",
    "evaluator_second.json",
    "evaluator_first_worker.json",
    "evaluator_second_worker.json",
    "agent_initialize.json",
}


def posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_secret_name(p: PurePosixPath) -> bool:
    name = p.name.lower()
    if name == ".env" or name.startswith(".env."):
        return name != ".env.example"
    if p.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}:
        return True
    return False


def classify(rel: str) -> Decision:
    p = PurePosixPath(rel)
    lower = rel.lower()

    if rel == AUDIT_REL:
        return Decision("TRACKED_EVIDENCE", "TRACK (self-hash omitted)", "Repository content audit; recursive self-hash is intentionally undefined.")
    if rel == BASELINE_REL:
        return Decision("TRACKED_EVIDENCE", "TRACK (co-generated hash omitted)", "Tracked Git-blob SHA-256 baseline; its audit hash is omitted to avoid a generation cycle with this audit.")
    if rel == CANDIDATE_SOURCE:
        return Decision("CANDIDATE_NON_AUTHORITATIVE", f"PRESERVE UNTRACKED; archive copy at {CANDIDATE_COPY}", "Historical source path retained; candidate content is not a formal project basis.")
    if rel == CANDIDATE_COPY or rel == "research/candidate_inputs/STATUS.md":
        return Decision("CANDIDATE_NON_AUTHORITATIVE", "TRACK", "Byte-preserved candidate archive or its non-authoritative status boundary.")
    if is_secret_name(p):
        return Decision("EXCLUDED_SECRET", "EXCLUDE", "Credential-bearing filename or private-key format.")
    if lower.startswith(".repository-audit/"):
        return Decision("REGENERABLE", "EXCLUDE", "Local staging allowlist generated from the repository audit.")
    if lower.startswith("third_step_a/.venv/") or "/__pycache__/" in lower or p.suffix.lower() in {".pyc", ".pyo"}:
        return Decision("REGENERABLE", "EXCLUDE", "Local virtual environment or generated Python bytecode.")
    if lower.startswith("third_step_a/vendor/appworld_source/"):
        return Decision("EXTERNAL_LARGE_ASSET", "EXCLUDE; INDEX EXTERNALLY", "Whole third-party AppWorld checkout; use the recorded upstream commit instead of vendoring it.")
    if lower.startswith("third_step_a/appworld_root/"):
        return Decision("EXCLUDED_LICENSE", "EXCLUDE; INDEX EXTERNALLY", "Protected AppWorld data/output or derivative subject to redistribution restrictions.")
    if lower.startswith(".aris/traces/") or lower.startswith(".aris/meta/") or lower.startswith(".aris/compute/"):
        return Decision("EXCLUDED_SECRET", "EXCLUDE; PRESERVE LOCALLY", "Local runtime metadata or raw reviewer request/response material was not cleared for repository sharing.")
    if lower.startswith("third_step_a/artifacts/smoke/"):
        parts = p.parts
        run = parts[3] if len(parts) > 3 else ""
        if any(part in {"checkpoint_snapshot", "db_snapshot_frozen", "appworld_output_snapshot"} for part in parts):
            return Decision("EXCLUDED_LICENSE", "EXCLUDE; INDEX EXTERNALLY", "AppWorld protected-data snapshot or derivative.")
        if p.name == "api_calls.jsonl" or p.name in {"prompt.txt", "generated_code.py"}:
            return Decision("EXCLUDED_SECRET", "EXCLUDE; PRESERVE LOCALLY", "Unredacted or high-risk raw run payload retained outside Git.")
        if run in {"run_reproduction_001", "run_isolated_001"} and p.name in TRACKED_EVIDENCE_NAMES:
            return Decision("TRACKED_EVIDENCE", "TRACK", "Reviewed small structured evidence for the required historical run.")
        return Decision("EXTERNAL_LARGE_ASSET", "EXCLUDE; INDEX EXTERNALLY", "Historical/raw run package remains immutable in external local storage; manifests and selected summaries are tracked.")
    if lower.startswith(".aris/audits/"):
        return Decision("TRACKED_EVIDENCE", "TRACK", "Formal experiment-audit report.")
    if lower.startswith("research/") or lower.startswith("review/"):
        return Decision("TRACKED_EVIDENCE", "TRACK", "Formal research, protocol, revision, or review record.")
    if lower.startswith("third_step_a/artifacts/"):
        return Decision("TRACKED_EVIDENCE", "TRACK", "Small top-level freeze, manifest, or probe record.")
    if lower.startswith("third_step_a/tests/"):
        return Decision("TRACKED_CORE", "TRACK", "Project-owned test or integration check.")
    if lower.startswith("third_step_a/"):
        return Decision("TRACKED_CORE", "TRACK", "Project-owned source, configuration, prompt, diagnostic, or environment record.")
    if lower.startswith("docs/") or lower.startswith(".github/") or lower.startswith("scripts/"):
        return Decision("TRACKED_CORE", "TRACK", "Repository management, collaboration, environment, or audit tooling.")
    if p.name in {"README.md", "CONTRIBUTING.md", ".gitignore", ".gitattributes"}:
        return Decision("TRACKED_CORE", "TRACK", "Repository management file.")
    if p.suffix.lower() in {".md", ".tex", ".bib"}:
        return Decision("TRACKED_EVIDENCE", "TRACK", "Project research or paper document.")
    return Decision("TRACKED_CORE", "TRACK", "Project-owned file within the confirmed PREEMPT-Mem root.")


def iter_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if current_path == root:
            dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            result.append(current_path / name)
    return sorted(result, key=lambda p: posix(p, root).casefold())


def tree_hash(entries: list[tuple[str, int, str]]) -> str:
    digest = hashlib.sha256()
    for rel, size, sha in sorted(entries, key=lambda item: item[0].casefold()):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def write_audit(root: Path, rows: list[tuple[str, Decision, int, str]]) -> None:
    audit = root / AUDIT_REL
    counts: dict[str, int] = {}
    bytes_by_category: dict[str, int] = {}
    for _, decision, size, _ in rows:
        counts[decision.category] = counts.get(decision.category, 0) + 1
        bytes_by_category[decision.category] = bytes_by_category.get(decision.category, 0) + size
    lines = [
        "# Repository Content Audit — 2026-09-02",
        "",
        "Confirmed project root: `E:\\\\科研\\\\ICLR2027-PREEMPT-Mem`.",
        "",
        "This audit enumerates every file under the confirmed project root except root Git metadata. SHA-256 is computed from bytes without opening file contents in the report. The audit row for this file uses `SELF-EXCLUDED`; the co-generated tracked-file baseline uses `CO-GENERATED-EXCLUDED` to avoid a mutual hash cycle. The baseline independently hashes canonical Git blob bytes.",
        "",
        "## Category summary",
        "",
        "| Category | Files | Bytes |",
        "|---|---:|---:|",
    ]
    for category in sorted(counts):
        lines.append(f"| {category} | {counts[category]} | {bytes_by_category[category]} |")
    lines.extend([
        "",
        "## File classification",
        "",
        "| Path | Category | Git action | Size | SHA-256 | Reason |",
        "|---|---|---|---:|---|---|",
    ])
    for rel, decision, size, sha in rows:
        lines.append(
            f"| `{escape_md(rel)}` | {decision.category} | {escape_md(decision.action)} | {size} | `{sha}` | {escape_md(decision.reason)} |"
        )
    audit.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_external_index(root: Path, rows: list[tuple[str, Decision, int, str]]) -> None:
    groups = {
        "AppWorld third-party source checkout": ("third_step_a/vendor/appworld_source/", {"EXTERNAL_LARGE_ASSET"}),
        "AppWorld protected data and experiment outputs": ("third_step_a/appworld_root/", {"EXCLUDED_LICENSE"}),
        "Local Python environment": ("third_step_a/.venv/", {"REGENERABLE"}),
        "Historical and raw smoke evidence": ("third_step_a/artifacts/smoke/", {"EXTERNAL_LARGE_ASSET", "EXCLUDED_LICENSE", "EXCLUDED_SECRET"}),
        "Local ARIS traces and host state": (".aris/", {"EXCLUDED_SECRET"}),
    }
    lines = [
        "# External Asset Index",
        "",
        "These assets remain at their existing local paths and were not moved, renamed, regenerated, or deleted during repository onboarding. Tree SHA-256 values hash the sorted sequence `relative-path NUL size NUL file-sha256 LF`; individual file hashes are in `REPOSITORY_CONTENT_AUDIT_2026-09-02.md`.",
        "",
        "| Asset | Existing location | Files | Bytes | Tree SHA-256 | Run/version | Recovery or replay | Why outside Git |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for label, (prefix, categories) in groups.items():
        selected = [(rel, size, sha) for rel, decision, size, sha in rows if rel.startswith(prefix) and decision.category in categories]
        if not selected:
            continue
        if label == "AppWorld third-party source checkout":
            version = "commit a072b7a86e7c1d5b1d7175659d750ebb9b79f10a (local checkout dirty)"
            recovery = "Clone https://github.com/StonyBrookNLP/appworld.git and check out the recorded commit; review any compatibility patch separately."
            reason = "Whole third-party checkout is reproducible from upstream and must not be copied wholesale into the project repository."
        elif label == "AppWorld protected data and experiment outputs":
            version = "AppWorld data 0.2.0; includes protected/derived database material"
            recovery = "Obtain through the authorized AppWorld distribution; use APPWORLD_ROOT and the commands in third_step_a/README.md."
            reason = "Redistribution restriction and protected-data derivatives."
        elif label == "Local Python environment":
            version = "Python 3.12.13; package versions in third_step_a/env-spec-isolated-v1.json"
            recovery = "Recreate a virtual environment and install the recorded AppWorld source/dependency versions."
            reason = "Platform-specific, regenerable local environment."
        elif label == "Historical and raw smoke evidence":
            version = "Includes run_reproduction_001, run_isolated_001, prior and failed development runs"
            recovery = "Use existing immutable local paths; verify with each run's artifact_manifest.json and the per-file audit hashes."
            reason = "Protected snapshots, unredacted/raw payloads, and bulk historical packages; selected manifests and summaries are tracked."
        else:
            version = "Local audit runtime records"
            recovery = "Use the existing local .aris directory; formal audit reports are tracked separately."
            reason = "Raw prompts/responses and host-local metadata were not cleared for repository sharing."
        lines.append(
            f"| {label} | `{prefix.rstrip('/')}` | {len(selected)} | {sum(item[1] for item in selected)} | `{tree_hash(selected)}` | {version} | {recovery} | {reason} |"
        )
    lines.extend([
        "",
        "## Historical run commands",
        "",
        "The authoritative A-R replay sequence is preserved in `third_step_a/README.md`. Existing run IDs are immutable and must not be reused. A replay must choose a new run ID, record the repository commit/configuration/model/seed provenance, and produce a new manifest.",
        "",
        "## Storage status",
        "",
        "No new external storage service was created during onboarding. The indexed assets remain only at their existing local locations. Loss of those locations would prevent complete raw-evidence reconstruction even though tracked manifests would still expose integrity drift.",
    ])
    (root / EXTERNAL_REL).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_allowlist(root: Path, rows: list[tuple[str, Decision, int, str]], output: Path) -> None:
    tracked = [rel for rel, decision, _, _ in rows if decision.action.startswith("TRACK")]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(tracked) + "\n", encoding="utf-8")


def write_baseline(root: Path, tracked_paths: list[str], git_rev: str) -> None:
    safe_root = root.as_posix()
    commit = subprocess.check_output(
        ["git", "-c", f"safe.directory={safe_root}", "rev-parse", git_rev],
        cwd=str(root),
    ).decode("ascii").strip()
    lines = [
        "# PREEMPT-Mem tracked-file SHA-256 baseline, generated 2026-09-02",
        f"# Source commit: {commit}",
        "# Hashes canonical Git blob bytes. Excludes this baseline and the repository content audit to avoid a mutual hash cycle.",
        "path\tbytes\tsha256",
    ]
    for rel in sorted(tracked_paths, key=str.casefold):
        if rel in {BASELINE_REL, AUDIT_REL}:
            continue
        blob = subprocess.check_output(
            ["git", "-c", f"safe.directory={safe_root}", "show", f"{git_rev}:{rel}"],
            cwd=str(root),
        )
        lines.append(f"{rel}\t{len(blob)}\t{hashlib.sha256(blob).hexdigest()}")
    (root / BASELINE_REL).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--allowlist", type=Path, default=Path(".repository-audit/tracked-paths.txt"))
    parser.add_argument("--baseline-from", type=Path)
    parser.add_argument("--baseline-git-rev", default="HEAD")
    args = parser.parse_args()
    root = args.root.resolve()

    if args.baseline_from:
        tracked_paths = [line.strip() for line in args.baseline_from.read_text(encoding="utf-8").splitlines() if line.strip()]
        write_baseline(root, tracked_paths, args.baseline_git_rev)
        return 0

    files = iter_files(root)
    rows: list[tuple[str, Decision, int, str]] = []
    for path in files:
        rel = posix(path, root)
        decision = classify(rel)
        if rel == AUDIT_REL:
            sha = "SELF-EXCLUDED"
        elif rel == BASELINE_REL:
            sha = "CO-GENERATED-EXCLUDED"
        else:
            sha = sha256_file(path)
        rows.append((rel, decision, path.stat().st_size, sha))
    write_external_index(root, rows)

    # Rehash the generated external index before writing the final audit.
    refreshed: list[tuple[str, Decision, int, str]] = []
    for rel, decision, size, sha in rows:
        if rel == EXTERNAL_REL:
            path = root / rel
            refreshed.append((rel, decision, path.stat().st_size, sha256_file(path)))
        else:
            refreshed.append((rel, decision, size, sha))
    rows = refreshed
    write_audit(root, rows)
    write_allowlist(root, rows, root / args.allowlist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
