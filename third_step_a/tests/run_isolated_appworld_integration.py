from __future__ import annotations

"""Manual one-case integration probe for the isolated structured boundary.

This is intentionally separate from the evidence runner.  It creates a fresh
AppWorld experiment and never targets an existing evidence directory.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path


warnings.filterwarnings("ignore")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "third_step_a/src"
sys.path.insert(0, str(SRC))

from isolated_rpc import PublicAppWorldGateway, run_capability_probes, run_structured_agent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--experiment-name", required=True)
    args = parser.parse_args()

    config = json.loads((PROJECT_ROOT / "third_step_a/config/cases_v3.json").read_text("utf-8"))
    isolated_config = json.loads(
        (PROJECT_ROOT / "third_step_a/config/cases_isolated_v1.json").read_text("utf-8")
    )
    case = next(item for item in config["cases"] if item["case_id"] == args.case)
    candidate = case["candidate_memory"]
    retrieved = [
        {
            "memory_id": candidate["memory_id"],
            "memory_type": candidate["memory_type"],
            "content": candidate["content"],
            "provenance": {"dataset": case["source_episode"]["dataset"]},
            "aliases": candidate["aliases"],
            "retrieval_keys": candidate["retrieval_keys"],
            "metadata": {"policy_id": candidate["policy_id"]},
        }
    ]
    appworld_root = (PROJECT_ROOT / "third_step_a/appworld_root").resolve()
    output = appworld_root / "experiments/outputs" / args.experiment_name
    if output.exists():
        raise FileExistsError(f"refusing to overwrite integration output: {output}")
    os.environ["APPWORLD_ROOT"] = str(appworld_root)
    from appworld import AppWorld, update_root

    update_root(str(appworld_root))
    world = AppWorld(
        task_id=case["target_task"]["task_id"],
        experiment_name=args.experiment_name,
        load_ground_truth=False,
        ground_truth_mode="minimal",
        random_seed=config["global"]["seed"],
        max_interactions=config["global"]["max_interactions"],
        max_api_calls_per_interaction=config["global"]["max_api_calls_per_interaction"],
        timeout_seconds=config["global"]["timeout_seconds"],
    )
    allowed_tools = isolated_config["isolation"]["allowed_tools_by_case"][args.case]
    gateway = PublicAppWorldGateway(world, allowed_tools=allowed_tools)
    with tempfile.TemporaryDirectory(prefix="preempt3ar_agent_") as temporary:
        probes = run_capability_probes(
            gateway,
            worker_path=SRC / "isolated_capability_probe_worker.py",
            sandbox_directory=Path(temporary) / "capability_probe",
        )
        agent = run_structured_agent(
            world=world,
            target_instruction=world.task.instruction,
            retrieval_results=retrieved,
            allowed_tools=allowed_tools,
            redaction_nonce=os.urandom(32).hex(),
            worker_path=SRC / "isolated_agent_worker.py",
            sandbox_directory=Path(temporary) / "agent",
        )
    world.save_state()
    task_completed = world.task_completed()
    raw_requests = list(world.requester.request_tracker.requests)
    ground_truth_absent = world.task.ground_truth is None
    world.close()

    evaluator_results = []
    for _ in range(2):
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                str(SRC / "isolated_evaluator_worker.py"),
                "--appworld-root",
                str(appworld_root),
                "--task-id",
                case["target_task"]["task_id"],
                "--experiment-name",
                args.experiment_name,
            ],
            cwd=Path(temporary).parent,
            env={
                **os.environ,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                "PYTHONWARNINGS": "ignore",
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        evaluator_results.append(json.loads(completed.stdout.strip().splitlines()[-1]))

    summary = {
        "case": args.case,
        "experiment_name": args.experiment_name,
        "agent_world_ground_truth_absent": ground_truth_absent,
        "capability_probes_all_pass": probes["all_pass"],
        "agent_result": agent["result"],
        "agent_tool_call_count": agent["tool_call_count"],
        "task_completed": task_completed,
        "raw_request_count_in_controller_only_memory": len(raw_requests),
        "evaluator_successes": [item["result"]["success"] for item in evaluator_results],
        "evaluator_pids": [item["pid"] for item in evaluator_results],
        "evaluator_stable": evaluator_results[0]["result"] == evaluator_results[1]["result"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not all(
        (
            ground_truth_absent,
            probes["all_pass"],
            task_completed,
            summary["evaluator_stable"],
            all(summary["evaluator_successes"]),
        )
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
