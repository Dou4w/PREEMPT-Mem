# Collaboration and Freeze Policy

## Historical evidence is immutable

- Do not directly overwrite, rename, delete, or regenerate a historical run.
- Every experiment uses a new run ID, including failed development runs.
- Existing manifests, evaluator outputs, verifier outputs, gates, and audit reports remain byte-preserved.
- Corrections are appended as a new report or version; they do not alter the original record.

## Required run provenance

Every run must record the repository commit SHA, configuration hash, model/provider version, seed or deterministic setting, dependency/environment versions, exact command, and artifact manifest. Evidence that cannot enter Git must be recorded in `docs/EXTERNAL_ASSET_INDEX.md` with a content hash and recovery method.

## Protocol and evaluation freeze

- A frozen protocol is changed only by creating a new, explicitly versioned protocol.
- Hidden triggers, evaluators, labels, severity mappings, and gates must not be edited in place after results are inspected.
- Any post-result correction requires a new version, an explanation, and a new run ID.
- Successful seeds must not be selected while failed seeds are discarded. Seed inclusion and exclusion rules must be fixed before result inspection.
- The current A-R evidence remains limited to a constructed deterministic selector-channel mechanism smoke. It must not be presented as semantic, natural, or comparative method evidence.

## Git collaboration

- Continue work through focused branches and pull requests.
- Do not force-push the default branch.
- Do not delete or move a frozen tag.
- Keep protocol changes, implementation changes, and evidence additions reviewable as separate commits when practical.
- Pull requests must state the scientific claim boundary, affected frozen artifacts, tests, and secret/license review.

## Candidate material

`research/candidate_inputs/` contains non-authoritative candidate inputs. Candidate text, including internal labels such as `USER_CONFIRMED` or “统一冻结”, is not a PREEMPT-Mem fact. Adoption requires explicit user approval and a separate decision record identifying exactly what was accepted.

## Protected and sensitive material

Credentials, personal data, unredacted sensitive prompts/logs, protected AppWorld data, database snapshots derived from protected data, local virtual environments, and third-party source checkouts remain outside Git. Their absence from Git does not authorize deletion from local storage.
