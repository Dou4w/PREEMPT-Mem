# External Asset Index

These assets remain at their existing local paths and were not moved, renamed, regenerated, or deleted during repository onboarding. Tree SHA-256 values hash the sorted sequence `relative-path NUL size NUL file-sha256 LF`; individual file hashes are in `REPOSITORY_CONTENT_AUDIT_2026-09-02.md`.

| Asset | Existing location | Files | Bytes | Tree SHA-256 | Run/version | Recovery or replay | Why outside Git |
|---|---|---:|---:|---|---|---|---|
| AppWorld third-party source checkout | `third_step_a/vendor/appworld_source` | 834 | 31135250 | `64215ff02da93fd5b429e4a1f370deea8dbb85cc2a9197f80e08fed9b6034c17` | commit a072b7a86e7c1d5b1d7175659d750ebb9b79f10a (local checkout dirty) | Clone https://github.com/StonyBrookNLP/appworld.git and check out the recorded commit; review any compatibility patch separately. | Whole third-party checkout is reproducible from upstream and must not be copied wholesale into the project repository. |
| AppWorld protected data and experiment outputs | `third_step_a/appworld_root` | 19666 | 181548118 | `14f7a7ff018909adab9f1cae50c355c22f4323a48f94d30327372ad86f544c77` | AppWorld data 0.2.0; includes protected/derived database material | Obtain through the authorized AppWorld distribution; use APPWORLD_ROOT and the commands in third_step_a/README.md. | Redistribution restriction and protected-data derivatives. |
| Local Python environment | `third_step_a/.venv` | 15206 | 152812612 | `27e1bf96e28917b1d7521f971e0404b6ba1320698f228cce9878b6113824bbd8` | Python 3.12.13; package versions in third_step_a/env-spec-isolated-v1.json | Recreate a virtual environment and install the recorded AppWorld source/dependency versions. | Platform-specific, regenerable local environment. |
| Historical and raw smoke evidence | `third_step_a/artifacts/smoke` | 4724 | 18368764 | `22a031e8f5c996d508d630647abd1c9d493da11fe4f48417a6d1509045bef05a` | Includes run_reproduction_001, run_isolated_001, prior and failed development runs | Use existing immutable local paths; verify with each run's artifact_manifest.json and the per-file audit hashes. | Protected snapshots, unredacted/raw payloads, and bulk historical packages; selected manifests and summaries are tracked. |
| Local ARIS traces and host state | `.aris` | 26 | 55774 | `7ca9433395a7ef6f23edd20229d3a98bef96b0bd08251f9cd5b48da66f2ebe8a` | Local audit runtime records | Use the existing local .aris directory; formal audit reports are tracked separately. | Raw prompts/responses and host-local metadata were not cleared for repository sharing. |

## Historical run commands

The authoritative A-R replay sequence is preserved in `third_step_a/README.md`. Existing run IDs are immutable and must not be reused. A replay must choose a new run ID, record the repository commit/configuration/model/seed provenance, and produce a new manifest.

## Storage status

No new external storage service was created during onboarding. The indexed assets remain only at their existing local locations. Loss of those locations would prevent complete raw-evidence reconstruction even though tracked manifests would still expose integrity drift.
