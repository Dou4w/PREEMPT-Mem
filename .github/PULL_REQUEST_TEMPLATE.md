## Scope

Describe the change and why it belongs in PREEMPT-Mem.

## Scientific boundary

- Claim or protocol affected:
- New evidence, if any:
- Existing frozen run or tag affected (must normally be “none”):
- Does this change a hidden trigger, evaluator, label, severity mapping, or gate? If yes, identify the new version and decision record.

## Verification

- Exact test command(s):
- Result(s):
- New run ID(s), if any:
- Commit/config/model/seed provenance recorded:

## Safety checklist

- [ ] No historical run or audit evidence was overwritten or deleted.
- [ ] No credential, personal data, unredacted sensitive log, or private endpoint was added.
- [ ] No protected data, database snapshot, model weight, cache, virtual environment, or whole third-party checkout was added.
- [ ] Candidate material remains isolated and non-authoritative.
- [ ] New external assets are indexed with hashes and recovery instructions.
- [ ] No expected result is presented as an observed result.
