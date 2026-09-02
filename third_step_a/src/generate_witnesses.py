from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


WITNESS_BY_POLICY: dict[str, dict[str, Any]] = {
    "workflow_export_notes_v1": {
        "hypothetical_unseen_trigger_family": "A later task requests a complete cross-app export of notes into a newly named backup directory with a deterministic filename convention.",
        "executable_intervention_family": "From one frozen future-task state, compare execution with the candidate available, with that exact item effectively evicted, and after exact restoration; run a state evaluator over created paths, contents, and collateral changes.",
        "falsifiable_deletion_prediction": "If the item is needed and fully removed, the export will be absent or incomplete and the required file-state tests will fail; exact restoration should recover a functionally equivalent file state.",
    },
    "gotcha_prefix_before_move_v1": {
        "hypothetical_unseen_trigger_family": "A later file-maintenance task requires date-derived renaming plus conditional movement while preserving untouched files.",
        "executable_intervention_family": "From one frozen file-system state, run the same deterministic agent under Full, item-evicted, and exact-restore conditions; compare path/content maps and unrelated-file invariants.",
        "falsifiable_deletion_prediction": "If the ordering gotcha is needed and fully removed, required renames/moves will be missing or wrong; exact restoration should recover the intended path/content map without collateral changes.",
    },
    "constraint_exact_reimbursement_v1": {
        "hypothetical_unseen_trigger_family": "A later reimbursement task requires resolving one person and one amount from communication history before one financial action and one follow-up message.",
        "executable_intervention_family": "From one frozen transactional state, run identical Full, item-evicted, and exact-restore branches and inspect transaction/message records plus collateral invariants.",
        "falsifiable_deletion_prediction": "If the constraint item is needed and fully removed, the agent will fail closed or violate an exact transaction/message requirement; exact restoration should recover the intended records without extra actions.",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[2]
    input_path = (project_root / args.input).resolve()
    prompt_path = (project_root / args.prompt).resolve()
    output_path = (project_root / args.output).resolve()
    inputs = json.loads(input_path.read_text(encoding="utf-8"))

    witnesses = []
    for item in inputs["cases"]:
        candidate = item["candidate_memory"]
        policy_id = candidate["policy_id"]
        witness = {
            "case_id": item["case_id"],
            "candidate_memory_id": candidate["memory_id"],
            "policy_id": policy_id,
            **WITNESS_BY_POLICY[policy_id],
            "generator_self_assessment_used_by_evaluator": False,
            "target_information_seen": False,
        }
        witnesses.append(witness)

    output = {
        "generator": inputs["generator"],
        "decoding": {
            "temperature": 0,
            "top_p": 1,
            "sampling": False,
            "seed": 314159,
        },
        "visible_information_only": inputs["visible_information_only"],
        "input_sha256": sha256(input_path),
        "prompt_sha256": sha256(prompt_path),
        "witnesses": witnesses,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
