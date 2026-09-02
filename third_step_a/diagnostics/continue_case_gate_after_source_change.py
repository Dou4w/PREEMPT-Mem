from __future__ import annotations

"""Development-only, read-only continuation of per-case aggregate checks.

Use this only after a fail-closed development run exposed a gate bug and the
gate source was patched.  It deliberately does not validate the now-stale
execution freeze and never writes into the run.  Final evidence must always use
``aggregate_smoke.py`` without this helper.
"""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "third_step_a/src"))

import aggregate_smoke as gate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if args.run_id == "run_isolated_001":
        raise ValueError("This development bypass is forbidden for final evidence")

    run_root = PROJECT_ROOT / "third_step_a/artifacts/smoke" / args.run_id
    precommit_path = (
        PROJECT_ROOT / f"third_step_a/artifacts/precommit_{args.run_id}.json"
    )
    attestation = gate.read_json(precommit_path)
    workflow_invocation = gate.read_json(
        run_root / "cases/workflow/controller_invocation.json"
    )
    freeze_result = workflow_invocation["execution_freeze"]
    frozen_contract = gate.load_frozen_contract(
        project_root=PROJECT_ROOT,
        config_path=PROJECT_ROOT / attestation["files"]["case_config"]["path"],
        witnesses_path=PROJECT_ROOT / attestation["files"]["witnesses"]["path"],
    )
    results: dict[str, bool] = {}
    for case_id in gate.CASE_IDS:
        result = gate.recompute_case(
            run_root / "cases" / case_id,
            project_root=PROJECT_ROOT,
            case_id=case_id,
            nonce_commitment_sha256=attestation["nonce_commitment_sha256"],
            run_nonce=attestation["nonce"],
            freeze_result=freeze_result,
            freeze_id=freeze_result["freeze_id"],
            freeze_sha256=freeze_result["freeze_sha256"],
            planned_runner_argv=attestation["planned_runner_argv_by_case"][case_id],
            case_contract=frozen_contract["contracts"][case_id],
        )
        results[case_id] = bool(result["case_pass_recomputed"])
    print(json.dumps(results, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
