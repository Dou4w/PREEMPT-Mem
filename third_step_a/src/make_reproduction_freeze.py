from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-freeze", required=True)
    parser.add_argument("--new-run-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    base_path = (project_root / args.base_freeze).resolve()
    output_path = (project_root / args.output).resolve()
    run_root = project_root / "third_step_a/artifacts/smoke" / args.new_run_id
    if output_path.exists() or run_root.exists():
        raise FileExistsError("Refusing to overwrite an existing freeze or run")
    freeze = json.loads(base_path.read_text(encoding="utf-8"))
    freeze["execution_freeze_id"] = f"PREEMPT-Mem-3A-{args.new_run_id}-reproduction"
    freeze["frozen_at"] = datetime.now().astimezone().isoformat()
    freeze["must_precede_run"] = f"third_step_a/artifacts/smoke/{args.new_run_id}"
    freeze["primary_evidence_run"] = args.new_run_id
    freeze["status"] = f"FROZEN_BEFORE_{args.new_run_id.upper()}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
