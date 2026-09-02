# Environment Record

The repository intentionally does not contain a generated lock file because no clean lock reconstruction was verified during repository onboarding.

## Frozen A-R environment

The authoritative installed-environment record is `third_step_a/env-spec-isolated-v1.json`:

- Windows 11;
- CPython 3.12.13;
- AppWorld source `https://github.com/StonyBrookNLP/appworld.git` at commit `a072b7a86e7c1d5b1d7175659d750ebb9b79f10a`;
- AppWorld code version `0.2.0.dev0`;
- protected AppWorld data version `0.2.0`;
- recorded critical Python distribution versions and deterministic environment variables.

The local AppWorld checkout was dirty at onboarding, with modifications limited to third-party test files. It is excluded from this repository and must not be treated as an exact clean source archive. Reconstruct from the recorded upstream commit, then apply only separately reviewed and documented compatibility changes if they are genuinely required.

## Protected data

`third_step_a/appworld_root/data` is intentionally absent from Git. Its own license notice states that the protected portion and derivatives may be publicly redistributed only in encrypted form. The repository is private, but the safer project policy is still to keep the protected data and derived database snapshots out of GitHub.

Obtain AppWorld data through its authorized distribution mechanism, verify version `0.2.0`, and place it at the path expected by `APPWORLD_ROOT`. Do not upload the data bundle or decrypted derivatives to this repository.

## Local reconstruction outline

1. Install CPython 3.12.13.
2. Create a local virtual environment at `third_step_a/.venv`.
3. Clone the official AppWorld repository outside Git tracking and check out the recorded commit.
4. Install the source in editable mode as recorded by `third_step_a/env-spec.json`.
5. Obtain the protected data through the authorized channel and set `APPWORLD_ROOT`.
6. Compare installed package versions to `third_step_a/env-spec-isolated-v1.json` before attempting reproduction.

This outline is a provenance record, not a claim that a clean-room installation was validated during repository onboarding.
