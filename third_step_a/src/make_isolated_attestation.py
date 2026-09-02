from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import secrets
import sys
import warnings
from datetime import datetime
from pathlib import Path

from evidence_integrity import (
    ATTESTATION_SCHEMA,
    manifest_root_sha256,
    git_head_from_metadata,
    nonce_commitment,
    sha256_file,
    tree_entries,
    write_json_new,
)


def relative_record(project_root: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.resolve().relative_to(project_root).as_posix(),
        "sha256": sha256_file(path),
    }


def tree_record(project_root: Path, path: Path) -> dict[str, object]:
    entries = tree_entries(path)
    return {
        "path": path.resolve().relative_to(project_root).as_posix(),
        "file_count": len(entries),
        "total_bytes": sum(item["size"] for item in entries),
        "tree_manifest_root_sha256": manifest_root_sha256(entries),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a non-overwriting pre-run nonce/source/data/environment attestation."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-config", required=True)
    parser.add_argument("--environment-spec", required=True)
    parser.add_argument("--execution-freeze", required=True)
    parser.add_argument("--witnesses", default="third_step_a/artifacts/witnesses.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    run_root = project_root / "third_step_a/artifacts/smoke" / args.run_id
    output_path = (project_root / args.output).resolve()
    if run_root.exists():
        raise FileExistsError(f"Run root already exists; attestation is not pre-run: {run_root}")

    config_path = (project_root / args.case_config).resolve()
    env_path = (project_root / args.environment_spec).resolve()
    freeze_path = (project_root / args.execution_freeze).resolve()
    witnesses_path = (project_root / args.witnesses).resolve()
    precommit_relative = output_path.relative_to(project_root).as_posix()
    common_runner_tail = [
        "--run-id",
        args.run_id,
        "--witnesses",
        witnesses_path.relative_to(project_root).as_posix(),
        "--execution-freeze",
        freeze_path.relative_to(project_root).as_posix(),
        "--precommit-attestation",
        precommit_relative,
    ]
    planned_runner_argv_by_case = {
        case_id: [
            "third_step_a/src/run_isolated_smoke_case.py",
            "--config",
            config_path.relative_to(project_root).as_posix(),
            "--case",
            case_id,
            *common_runner_tail,
        ]
        for case_id in ("workflow", "gotcha", "constraint_permission")
    }
    nonce = secrets.token_hex(32)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import appworld
    appworld_source_path = (project_root / "third_step_a/vendor/appworld_source").resolve()
    appworld_module_path = Path(appworld.__file__).resolve()
    if appworld_source_path not in appworld_module_path.parents:
        raise RuntimeError("Imported AppWorld module is not inside the attested vendor source tree")
    direct_url_text = importlib.metadata.distribution("appworld").read_text("direct_url.json")
    if not direct_url_text:
        raise RuntimeError("AppWorld distribution has no direct_url.json source binding")
    attestation = {
        "schema_version": ATTESTATION_SCHEMA,
        "attestation_role": "pre-run commitment; copy byte-for-byte into the sealed run",
        "created_at": datetime.now().astimezone().isoformat(),
        "run_id": args.run_id,
        "run_relative_path": run_root.relative_to(project_root).as_posix(),
        "nonce": nonce,
        "nonce_commitment_sha256": nonce_commitment(args.run_id, nonce),
        "command_argv": list(sys.argv),
        "planned_runner_argv_by_case": planned_runner_argv_by_case,
        "trees": {
            "harness_source": tree_record(project_root, project_root / "third_step_a/src"),
            "appworld_source": {
                **tree_record(project_root, project_root / "third_step_a/vendor/appworld_source"),
                "git_commit": git_head_from_metadata(
                    project_root / "third_step_a/vendor/appworld_source"
                ),
            },
            "appworld_data": tree_record(
                project_root, project_root / "third_step_a/appworld_root/data"
            ),
        },
        "files": {
            "case_config": relative_record(project_root, config_path),
            "environment_spec": relative_record(project_root, env_path),
            "execution_freeze": relative_record(project_root, freeze_path),
            "witnesses": relative_record(project_root, witnesses_path),
        },
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "python_executable_sha256": sha256_file(Path(sys.executable)),
            "critical_python_distributions": {
                str(name): importlib.metadata.version(str(name))
                for name in sorted(
                    json.loads(env_path.read_text(encoding="utf-8"))[
                        "critical_python_distributions"
                    ]
                )
            },
            "appworld_source_commit": git_head_from_metadata(
                project_root / "third_step_a/vendor/appworld_source"
            ),
            "appworld_code_version": importlib.metadata.version("appworld"),
            "appworld_module_relative_path": appworld_module_path.relative_to(
                project_root
            ).as_posix(),
            "appworld_module_file_sha256": sha256_file(appworld_module_path),
            "appworld_distribution_direct_url_sha256": hashlib.sha256(
                direct_url_text.encode("utf-8")
            ).hexdigest(),
            "appworld_distribution_editable": bool(
                json.loads(direct_url_text).get("dir_info", {}).get("editable")
            ),
            "appworld_data_version": (
                project_root / "third_step_a/appworld_root/data/version.txt"
            ).read_text(encoding="utf-8").strip(),
        },
    }
    write_json_new(output_path, attestation)
    print(output_path)
    print(attestation["nonce_commitment_sha256"])


if __name__ == "__main__":
    main()
