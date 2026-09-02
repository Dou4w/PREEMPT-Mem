# Repository Establishment Report — 2026-09-02

## Repository state

- Confirmed project root: `E:\科研\ICLR2027-PREEMPT-Mem`.
- GitHub repository: `Dou4w/PREEMPT-Mem`.
- Visibility: `PRIVATE`, verified before push and again from the fresh-clone workflow.
- Remote: `origin`.
- Default branch: `main`.
- Initial onboarding commit: `7e0c17c0b709044920adb870e1bdea814bc51e05`.
- Effective collaboration baseline tag after metadata repair: `pre-collaboration-baseline-2026-09-02-2`.
- The earlier tag `pre-collaboration-baseline-2026-09-02` remains immutable at the initial onboarding commit; it was not moved or overwritten after fresh-clone validation exposed a checkout-normalization issue in the first checksum baseline.

The final commit SHA is intentionally not embedded in this tracked report because doing so would make the report self-referential. Resolve the effective annotated tag to obtain the authoritative final baseline commit.

## Content selection

The final intended set contains 307 tracked files. It includes:

- project-owned controller, memory-store, retrieval, eviction, restore, evaluator, verifier, leakage, manifest, replay, severity, and evidence-integrity code;
- existing configurations, prompts, environment records, diagnostics, and tests;
- formal literature, feasibility, story, protocol, review, A-R repair, independent-audit, and optimized paper-structure documents;
- selected small structured manifests and evidence summaries for `run_reproduction_001` and `run_isolated_001`;
- repository collaboration, issue, pull-request, environment, audit, and freeze-policy files.

No lock file was invented. The recorded environment and its remaining reconstruction gap are documented in `docs/ENVIRONMENT.md`.

## Historical evidence and external assets

Historical runs were not moved, renamed, regenerated, overwritten, or deleted. Existing artifact manifests remain byte-preserved. Protected/raw snapshots and bulk evidence remain at their original local locations and are described by tree hash in `docs/EXTERNAL_ASSET_INDEX.md`:

- AppWorld third-party checkout at recorded commit `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a` (local checkout is dirty and excluded);
- AppWorld protected data 0.2.0 and derived experiment outputs;
- local Python 3.12.13 virtual environment;
- raw and historical smoke packages, including unredacted legacy API logs and protected database snapshots;
- local ARIS reviewer traces and host metadata.

The existing local locations are currently the only storage locations for the excluded raw assets. Loss of those locations would prevent complete raw-evidence reconstruction, although tracked manifests and the content audit would still reveal integrity drift.

## Candidate isolation

The candidate comparison report was copied byte-for-byte to `research/candidate_inputs/` and classified as `CANDIDATE_NON_AUTHORITATIVE`. Source and archived copy both hash to:

`c8a17c83b9957549d8ffc32865ef043321f0270919a134f2d294918124c57bec`

The historical source path remains untouched and ignored. `research/candidate_inputs/STATUS.md` prevents candidate assertions such as `USER_CONFIRMED` or “统一冻结” from becoming project facts.

## Secret, privacy, license, and size controls

- `gitleaks` was not installed; an equivalent high-confidence filename-only pattern scan was run over the exact tracked allowlist and again over the fresh clone.
- Secret-scan file hits: 0.
- No `.env`, private-key format, virtual environment, package cache, AppWorld source checkout, AppWorld protected-data path, or raw ARIS trace is tracked.
- No tracked file exceeds 100 MB; Git LFS was not needed.
- The AppWorld protected-data license notice was reviewed. Protected data and derived database snapshots remain outside Git.
- No repository `LICENSE` or author-order file was created.

## Verification

Local pre-commit suite:

- command: `third_step_a/.venv/Scripts/python.exe -m unittest discover -s third_step_a/tests -v`;
- result: 36/36 passed.

Fresh-clone verification:

- clone succeeded from the private remote;
- visibility `PRIVATE`, default branch `main`, remote commit, and tag resolution matched;
- 307 tracked files are expected after the metadata repair;
- required source, configuration, test, formal research, manifests, and candidate-status files were present;
- candidate material existed only in the non-authoritative directory;
- forbidden paths and high-confidence secret patterns: 0;
- files over 100 MB: 0;
- checkout-stable Git-blob checksum baseline is required to match with zero mismatches;
- `git fsck --full`: passed;
- pure-repository tests: 25/25 passed.

The full 36-test suite in the fresh clone has one expected external-asset error because `test_agent_request_contains_exact_case_tool_allowlist_and_no_branch` reads AppWorld protected task data that is deliberately absent from Git. This is not repaired by copying protected data into the repository. With the authorized external AppWorld data mounted, the same full suite passed 36/36 in the source workspace.

## Confirmed non-actions

- The repository was not made public.
- No collaborator, release, Pages site, or anonymous submission repository was added.
- No GitHub link was written into the ICLR paper materials.
- A-S, the 40-memory Pilot, training, paid models, and GPU work were not started.
- No paper core definition, method gate, or frozen scientific conclusion was changed.
- No historical experiment or audit evidence was deleted, overwritten, or rewritten.
