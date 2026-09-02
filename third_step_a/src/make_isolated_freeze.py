from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from evidence_integrity import sha256_file, write_json_new


def _inside(project_root: Path, relative: str) -> Path:
    path = (project_root / relative).resolve()
    if path != project_root and project_root not in path.parents:
        raise ValueError(f"Path escapes project root: {relative}")
    return path


def _relative(project_root: Path, paths: Iterable[Path]) -> list[str]:
    return sorted(path.resolve().relative_to(project_root).as_posix() for path in paths)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze all 3A-R harness/config/prompt files before a new isolated run."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-config", required=True)
    parser.add_argument("--environment-spec", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    run_root = project_root / "third_step_a/artifacts/smoke" / args.run_id
    if run_root.exists():
        raise FileExistsError(f"Run root already exists; cannot make a pre-run freeze: {run_root}")

    config_path = _inside(project_root, args.case_config)
    environment_path = _inside(project_root, args.environment_spec)
    output_path = _inside(project_root, args.output)
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    base_config = _inside(project_root, overlay["base_config_path"])
    source_files = list((project_root / "third_step_a/src").glob("*.py"))
    test_files = list((project_root / "third_step_a/tests").glob("*.py"))
    prompt_files = list((project_root / "third_step_a/prompts").glob("*.txt"))
    fixed_files = [
        config_path,
        base_config,
        environment_path,
        project_root / "third_step_a/README.md",
        project_root / "third_step_a/artifacts/witnesses.json",
        *source_files,
        *test_files,
        *prompt_files,
    ]
    relative_files = _relative(project_root, (path for path in fixed_files if path.is_file()))
    files = {relative: sha256_file(project_root / relative) for relative in relative_files}
    freeze = {
        "schema_version": "preempt-mem-3a-r-execution-freeze-v1",
        "status": "FROZEN_BEFORE_RUN_ISOLATED",
        "created_at": datetime.now().astimezone().isoformat(),
        "execution_freeze_id": f"{args.run_id}-freeze-v1",
        "primary_evidence_run": args.run_id,
        "must_precede_run": f"third_step_a/artifacts/smoke/{args.run_id}",
        "case_config": config_path.relative_to(project_root).as_posix(),
        "base_config": base_config.relative_to(project_root).as_posix(),
        "environment_spec": environment_path.relative_to(project_root).as_posix(),
        "files": files,
        "file_count": len(files),
        "planned_order": [
            "create pre-run source/data/environment attestation and nonce",
            "create fresh run root and copy precommit attestation byte-for-byte",
            "run target+distractor probe",
            "run workflow/gotcha/constraint_permission Full/Evicted/Restore with no-GT Agent worlds",
            "freeze DB and exit Agent before two independent official evaluator processes",
            "seal pre-aggregate evidence",
            "recompute aggregate gate and final artifact manifest",
            "stop before 3B/Pilot",
        ],
        "claim_scope": "constructed deterministic selector-channel mechanism smoke",
        "pilot_started": False,
    }
    write_json_new(output_path, freeze)
    print(output_path)
    print(f"frozen_file_count={len(files)}")
    print(f"freeze_sha256={sha256_file(output_path)}")


if __name__ == "__main__":
    main()
