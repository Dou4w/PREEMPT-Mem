from __future__ import annotations

import argparse
from pathlib import Path

from evidence_integrity import build_manifest, write_json_new


PRE_AGGREGATE_EXCLUSIONS = (
    "aggregate_gate.json",
    "artifact_manifest.json",
    "pre_aggregate_artifact_manifest.json",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seal all pre-aggregate evidence without trusting case summaries."
    )
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    run_root = (project_root / args.run_root).resolve()
    if project_root != run_root and project_root not in run_root.parents:
        raise ValueError("Run root escapes project")
    if not run_root.is_dir():
        raise FileNotFoundError(run_root)
    manifest = build_manifest(
        run_root,
        scope="pre_aggregate_evidence",
        exclude_relative_paths=PRE_AGGREGATE_EXCLUSIONS,
    )
    output = run_root / "pre_aggregate_artifact_manifest.json"
    write_json_new(output, manifest)
    print(output)
    print(manifest["manifest_root_sha256"])


if __name__ == "__main__":
    main()

