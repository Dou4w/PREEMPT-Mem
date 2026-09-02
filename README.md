# PREEMPT-Mem

PREEMPT-Mem is a research project on retention decisions for explicit, addressable, external long-term agent memory. Its provisional goal is to test whether an agent can generate a candidate-specific future decision witness before a real trigger appears, validate deletion risk through auditable Full/Evicted/Restore interventions, and use that evidence under both memory and testing budgets.

## Current evidence boundary

The project has completed the third-step A-R isolation repair and its independent audit. The next scientific stage is the A-S semantic Mini-Pilot; it has **not** started.

Current evidence supports only a narrow, constructed deterministic selector-channel mechanism smoke test for Full/Evicted/Restore isolation. It does **not** yet establish:

- a naturally occurring rare-but-critical memory phenomenon;
- predictive value of a witness on a hidden future task;
- semantic use of memory content by a real model;
- superiority of PREEMPT-Mem over retention baselines;
- prevalence, cross-model generalization, or full-Pilot readiness.

These boundaries are part of the project record and must not be widened without new evidence and an explicit decision record.

## Repository layout

- `third_step_a/src/`: project-owned controller, memory-store, evaluator, verifier, leakage, manifest, replay, and evidence-integrity code.
- `third_step_a/tests/`: unit, integration, isolation, replay, evaluator-stability, eviction, and restore tests that actually exist.
- `third_step_a/config/`, `third_step_a/prompts/`, `third_step_a/diagnostics/`: frozen experiment inputs and diagnostics.
- `third_step_a/artifacts/`: small, reviewed manifests and evidence summaries. Raw/protected evidence remains external and is indexed in `docs/EXTERNAL_ASSET_INDEX.md`.
- `research/` and `review/`: formal research basis, protocol records, revisions, and independent reviews.
- `research/candidate_inputs/`: non-authoritative candidate material, isolated from the formal project basis.
- `docs/`: collaboration policy, environment notes, repository audit, external-asset index, and repository baseline records.

The vendored AppWorld checkout, protected AppWorld data, local virtual environment, caches, raw database snapshots, and unredacted logs are intentionally excluded from Git.

## Environment

The frozen A-R environment is described by `third_step_a/env-spec-isolated-v1.json`:

- Python 3.12.13;
- AppWorld source commit `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`;
- AppWorld code `0.2.0.dev0` and protected data `0.2.0`;
- no network dependency during the frozen smoke run.

The repository does not contain an unverified lock file. See `docs/ENVIRONMENT.md` for the recorded source, protected-data boundary, and reconstruction caveats.

## Tests

With the recorded local A-R environment available, run:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONWARNINGS = 'ignore'
$env:PYTHONHASHSEED = '0'
& 'third_step_a/.venv/Scripts/python.exe' -m unittest discover -s third_step_a/tests -v
```

The historical reproduction commands are preserved in `third_step_a/README.md`. Do not rerun them with an existing run ID: historical evidence is immutable.

## Evidence protection

- Never overwrite or delete a historical run.
- Every new experiment receives a new run ID and records commit SHA, configuration hash, model version, and seed.
- Raw AppWorld data and derived database snapshots remain outside Git because of redistribution restrictions.
- Unredacted logs, credentials, local environments, and caches remain outside Git.
- Existing manifests are preserved byte-for-byte; excluded files remain verifiable by their existing manifests and the repository content audit.

See `docs/COLLABORATION_AND_FREEZE_POLICY.md` for the full freeze and collaboration policy.

## Candidate reports

Files under `research/candidate_inputs/` are non-authoritative inputs. They cannot redefine the paper story, method, protocol, gates, or project status. Adoption requires an explicit user decision and a separate decision record.

## Contributing

Work should proceed through branches and pull requests. Do not force-push the main branch or rewrite frozen evidence. See `CONTRIBUTING.md` and the pull-request template before proposing changes.
