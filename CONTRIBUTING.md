# Contributing to PREEMPT-Mem

This is a private research repository with evidence-preservation requirements.

## Workflow

1. Create a focused branch from the current default branch.
2. Keep scientific protocol changes separate from implementation-only changes.
3. Add or update tests for project-owned code where applicable.
4. Run the lightest relevant test suite and record the exact command and result.
5. Open a pull request using the repository template.

Do not force-push the default branch, rewrite published branch history, move a frozen tag, or overwrite an existing run directory.

## Experiment changes

Every new run must use a new run ID and record:

- commit SHA;
- configuration hash;
- model/provider version, if any;
- seed or deterministic setting;
- environment and dependency versions;
- invocation command;
- evidence manifest.

Changes to a frozen protocol, evaluator, hidden trigger, label, or gate require a new version and an explicit decision record. Results already observed under an older version must remain available and must not be silently relabeled.

## Data, secrets, and third-party code

Never commit credentials, private endpoints, cookies, personal data, unredacted sensitive logs, protected AppWorld data, local virtual environments, caches, model weights, checkpoints, or whole third-party source checkouts. Add only reviewed project-owned files and small, sanitized evidence summaries. Update `docs/EXTERNAL_ASSET_INDEX.md` when an excluded asset is required for reproduction.

The project has not selected a repository license or final author order. Do not add either without explicit approval.
