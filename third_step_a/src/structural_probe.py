from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import warnings
from pathlib import Path
from typing import Any


warnings.filterwarnings("ignore", category=DeprecationWarning)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(repo: Path) -> str:
    git_dir = repo / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    ref_name = head.removeprefix("ref: ")
    loose_ref = git_dir / Path(ref_name)
    if loose_ref.exists():
        return loose_ref.read_text(encoding="utf-8").strip()
    packed_refs = (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines()
    for line in packed_refs:
        if line and not line.startswith(("#", "^")):
            commit, name = line.split(" ", 1)
            if name == ref_name:
                return commit
    raise RuntimeError(f"Could not resolve Git HEAD for {repo}")


def tracker_dict(tracker: Any) -> dict[str, Any]:
    return tracker.to_dict(stats_only=False)


def amazon_card_count(world: Any) -> int:
    supervisor = world.models.supervisor.Supervisor.all()[0]
    user = world.models.amazon.User.find_one(email=supervisor.email)
    return len(user.payment_cards)


def delete_all_amazon_cards(world: Any) -> int:
    supervisor = world.models.supervisor.Supervisor.all()[0]
    password = next(
        item.password for item in supervisor.account_passwords if item.account_name == "amazon"
    )
    access_token = world.apis.amazon.login(
        username=supervisor.email, password=password
    )["access_token"]
    cards = world.apis.amazon.show_payment_cards(access_token=access_token)
    for card in cards:
        world.apis.amazon.delete_payment_card(
            payment_card_id=card["payment_card_id"], access_token=access_token
        )
    world.save_state()
    return len(cards)


def relationship_probe(task_ids: list[str]) -> dict[str, Any]:
    from appworld.task import Task, task_id_to_generator_id, task_id_to_number

    rows: list[dict[str, Any]] = []
    for task_id in task_ids:
        task = Task.load(task_id=task_id)
        rows.append(
            {
                "task_id": task.id,
                "generator_or_scenario_id": task_id_to_generator_id(task.id),
                "variation_number": task_id_to_number(task.id),
                "supervisor_email": task.supervisor.email,
                "datetime": task.datetime.isoformat(),
                "task_input_db_home": task.models_from_db_home_path,
                "instruction_sha256": hashlib.sha256(task.instruction.encode("utf-8")).hexdigest(),
            }
        )
        task.close()
    return {
        "rows": rows,
        "same_generator": len({row["generator_or_scenario_id"] for row in rows}) == 1,
        "different_variations": len({row["variation_number"] for row in rows}) == len(rows),
        "different_supervisors": len({row["supervisor_email"] for row in rows}) == len(rows),
        "task_specific_db_paths": len({row["task_input_db_home"] for row in rows}) == len(rows),
    }


def checkpoint_and_reset_probe(config: dict[str, Any]) -> dict[str, Any]:
    from appworld import AppWorld

    task_id = config["checkpoint_task_id"]
    seed = config["seed"]
    common = {
        "random_seed": seed,
        "ground_truth_mode": "full",
        "max_interactions": config["max_interactions"],
        "max_api_calls_per_interaction": config["max_api_calls_per_interaction"],
    }
    world = AppWorld(task_id=task_id, experiment_name="preempt_3a_structural_checkpoint", **common)
    initial_supervisor = world.task.supervisor.email
    initial_db_home = world.output_db_home_path_in_memory
    initial_count = amazon_card_count(world)
    world.save_state("initial")
    deleted_count = delete_all_amazon_cards(world)
    mutated_count = amazon_card_count(world)
    world.save_state("mutated")
    world.load_state("initial")
    # AppWorld 0.2.0.dev0 load_state() calls AppWorld.close_all(), which stops
    # the world's time freezer but does not re-arm it. Re-arm before any later
    # close/new-world operation to avoid a second freezegun stop on Windows.
    world._set_datetime()
    restored_initial_count = amazon_card_count(world)
    world.load_state("mutated")
    world._set_datetime()
    restored_mutated_count = amazon_card_count(world)
    checkpoint_root = Path(world.output_checkpoints_directory)
    checkpoint_files = sorted(
        str(path.relative_to(checkpoint_root)).replace("\\", "/")
        for path in checkpoint_root.rglob("*")
        if path.is_file()
    )
    world.close()

    fresh_same = AppWorld(
        task_id=task_id, experiment_name="preempt_3a_structural_fresh_same", **common
    )
    fresh_same_count = amazon_card_count(fresh_same)
    fresh_same.close()

    other_task_id = config["relationship_task_ids"][1]
    other = AppWorld(
        task_id=other_task_id, experiment_name="preempt_3a_structural_other_task", **common
    )
    other_supervisor = other.task.supervisor.email
    other_db_home = other.output_db_home_path_in_memory
    other.close()

    return {
        "task_id": task_id,
        "initial_supervisor": initial_supervisor,
        "initial_db_home": initial_db_home,
        "initial_card_count": initial_count,
        "deleted_card_count": deleted_count,
        "mutated_card_count": mutated_count,
        "load_initial_card_count": restored_initial_count,
        "load_mutated_card_count": restored_mutated_count,
        "checkpoint_files": checkpoint_files,
        "compatibility_workaround": "re-arm _set_datetime() after load_state() before close/new world",
        "round_trip_pass": bool(
            initial_count > 0
            and deleted_count == initial_count
            and mutated_count == 0
            and restored_initial_count == initial_count
            and restored_mutated_count == 0
        ),
        "fresh_same_task_resets_to_task_input": fresh_same_count == initial_count,
        "other_task_id": other_task_id,
        "other_supervisor": other_supervisor,
        "other_db_home": other_db_home,
        "new_task_closes_and_rebinds_db": bool(
            other_supervisor != initial_supervisor and other_db_home != initial_db_home
        ),
    }


def evaluator_and_collateral_probe(config: dict[str, Any]) -> dict[str, Any]:
    from appworld import AppWorld

    task_id = config["evaluator_task_id"]
    common = {
        "random_seed": config["seed"],
        "ground_truth_mode": "full",
        "max_interactions": config["max_interactions"],
        "max_api_calls_per_interaction": config["max_api_calls_per_interaction"],
    }

    noop = AppWorld(task_id=task_id, experiment_name="preempt_3a_structural_eval_noop", **common)
    noop_first = tracker_dict(noop.evaluate())
    noop_second = tracker_dict(noop.evaluate())
    noop.close()

    clean = AppWorld(task_id=task_id, experiment_name="preempt_3a_structural_eval_clean", **common)
    ground_truth = clean.task.ground_truth
    if ground_truth is None:
        raise RuntimeError("The neutral structural task has no ground truth.")
    code = ground_truth.compiled_solution_code + "\nsolution(apis, requester)"
    clean_execute_output = clean.execute(code)
    clean_tracker = tracker_dict(clean.evaluate())
    clean.close()

    collateral = AppWorld(
        task_id=task_id, experiment_name="preempt_3a_structural_eval_collateral", **common
    )
    ground_truth = collateral.task.ground_truth
    if ground_truth is None:
        raise RuntimeError("The neutral structural task has no ground truth.")
    code = ground_truth.compiled_solution_code + "\nsolution(apis, requester)"
    collateral_execute_output = collateral.execute(code)
    clean_before_collateral = tracker_dict(collateral.evaluate())
    delete_all_amazon_cards(collateral)
    collateral_first = tracker_dict(collateral.evaluate())
    collateral_second = tracker_dict(collateral.evaluate())
    collateral.close()

    return {
        "task_id": task_id,
        "noop_first": noop_first,
        "noop_second": noop_second,
        "noop_stable": noop_first == noop_second,
        "clean": clean_tracker,
        "clean_execute_output": clean_execute_output,
        "clean_success": clean_tracker["success"],
        "clean_before_collateral": clean_before_collateral,
        "collateral_execute_output": collateral_execute_output,
        "collateral_first": collateral_first,
        "collateral_second": collateral_second,
        "collateral_stable": collateral_first == collateral_second,
        "collateral_detected": bool(
            clean_before_collateral["success"]
            and not collateral_first["success"]
            and any(
                "model changes" in failure["requirement"].lower()
                for failure in collateral_first["failures"]
            )
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    config_path = (project_root / args.config).resolve()
    output_path = (project_root / args.output).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    appworld_root = (project_root / config["appworld_root"]).resolve()
    source_repo = (project_root / config["source_repo"]).resolve()

    os.environ["APPWORLD_ROOT"] = str(appworld_root)
    from appworld import update_root

    update_root(str(appworld_root))
    import appworld

    result = {
        "probe_version": "preempt-3a-structural-probe-v1",
        "python": sys.version,
        "platform": platform.platform(),
        "appworld_version": getattr(appworld, "__version__", "unknown"),
        "appworld_source_commit": git_commit(source_repo),
        "appworld_data_version": (appworld_root / "data" / "version.txt")
        .read_text(encoding="utf-8")
        .strip(),
        "config_sha256": sha256_file(config_path),
        "relationship": relationship_probe(config["relationship_task_ids"]),
        "checkpoint_and_reset": checkpoint_and_reset_probe(config),
        "evaluator_and_collateral": evaluator_and_collateral_probe(config),
    }
    result["all_required_checks_pass"] = bool(
        result["relationship"]["same_generator"]
        and result["relationship"]["different_variations"]
        and result["relationship"]["task_specific_db_paths"]
        and result["checkpoint_and_reset"]["round_trip_pass"]
        and result["checkpoint_and_reset"]["fresh_same_task_resets_to_task_input"]
        and result["checkpoint_and_reset"]["new_task_closes_and_rebinds_db"]
        and result["evaluator_and_collateral"]["noop_stable"]
        and result["evaluator_and_collateral"]["clean_success"]
        and result["evaluator_and_collateral"]["collateral_stable"]
        and result["evaluator_and_collateral"]["collateral_detected"]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_required_checks_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
