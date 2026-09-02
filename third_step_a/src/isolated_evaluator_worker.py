from __future__ import annotations

"""One-shot official AppWorld evaluator process for a frozen Agent DB."""

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _db_tree(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise FileNotFoundError(f"Evaluator input DB directory is missing: {path}")
    entries: list[dict[str, Any]] = []
    for file_path in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        if not file_path.is_file():
            continue
        data = file_path.read_bytes()
        entries.append(
            {
                "path": file_path.relative_to(path).as_posix(),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    serialized = json.dumps(
        entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return {
        "directory": path.name,
        "file_count": len(entries),
        "total_bytes": sum(item["size"] for item in entries),
        "tree_manifest_root_sha256": hashlib.sha256(serialized).hexdigest(),
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--appworld-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--experiment-name", required=True)
    args = parser.parse_args()

    appworld_root = Path(args.appworld_root).resolve()
    os.environ["APPWORLD_ROOT"] = str(appworld_root)
    # Freeze the actual process-launch capability surface before importing
    # AppWorld.  AppWorld adds APPWORLD_CACHE and TERMINAL_WIDTH as internal
    # runtime conveniences; reporting the post-import mapping as though it were
    # inherited from the controller makes the environment attestation false.
    launch_environment_key_names = sorted(os.environ)
    input_db_directory = (
        appworld_root
        / "experiments/outputs"
        / args.experiment_name
        / "tasks"
        / args.task_id
        / "dbs"
    )
    input_db_before = _db_tree(input_db_directory)
    # Keep stdout machine-readable even if a dependency emits informational text.
    with contextlib.redirect_stdout(sys.stderr):
        import appworld
        from appworld import update_root
        from appworld.evaluator import evaluate_task

        update_root(str(appworld_root))
        tracker = evaluate_task(
            task_id=args.task_id,
            experiment_name=args.experiment_name,
            suppress_errors=True,
            save_report=False,
        )
        result: dict[str, Any] = tracker.to_dict(stats_only=False)
    input_db_after = _db_tree(input_db_directory)
    if input_db_before != input_db_after:
        raise RuntimeError("Official evaluator mutated its frozen input DB tree")

    appworld_module_path = Path(appworld.__file__).resolve()
    direct_url_text = importlib.metadata.distribution("appworld").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        raise RuntimeError("Evaluator AppWorld distribution has no direct_url.json")
    output = {
        "worker_protocol": "preempt3a-isolated-evaluator-v1",
        "pid": os.getpid(),
        "task_id": args.task_id,
        "experiment_name": args.experiment_name,
        "appworld_version": appworld.__version__,
        "appworld_module_file": appworld_module_path.as_posix(),
        "appworld_module_file_sha256": _sha256_file(appworld_module_path),
        "appworld_distribution_direct_url_sha256": hashlib.sha256(
            direct_url_text.encode("utf-8")
        ).hexdigest(),
        "ground_truth_loaded_only_in_evaluator": True,
        "evaluation_entrypoint": "appworld.evaluator.evaluate_task",
        "save_report": False,
        "environment_key_names": launch_environment_key_names,
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "deterministic_environment": {
            key: os.environ.get(key)
            for key in (
                "PYTHONHASHSEED",
                "PYTHONIOENCODING",
                "PYTHONUTF8",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONWARNINGS",
            )
        },
        "input_db_path_role": "live experiment DB frozen by controller before evaluator start",
        "input_db_tree_before": input_db_before,
        "input_db_tree_after": input_db_after,
        "input_db_unchanged": True,
        "result": result,
        "worker_sha256": _sha256_file(Path(__file__).resolve()),
    }
    # Emit one ASCII-only framed protocol record.  AppWorld and transitive
    # dependencies may write locale-encoded diagnostics directly to inherited
    # Windows pipes, so the controller must not treat the entire stdout stream
    # as UTF-8 text.
    print(
        "PREEMPT_MEM_EVALUATOR_RESULT\t"
        + json.dumps(output, ensure_ascii=True, sort_keys=True)
    )


if __name__ == "__main__":
    main()
