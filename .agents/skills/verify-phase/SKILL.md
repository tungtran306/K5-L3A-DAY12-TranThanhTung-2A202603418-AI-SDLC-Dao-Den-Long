---
name: verify-phase
description: Run the full build, Phase 1 regression + Phase 2 scenario tests, Nights 1-3 determinism check, and 21,600-tick performance benchmark for Dao Den Long before committing or tagging.
---

# Verify Phase Skill (Updated for Phase 2 / Contract v1.1)

Use this skill before committing or tagging `phase-2` (and subsequent phases).

## Steps
1. Run `python3 scripts/verify.py` from the repository root.
2. Confirm exit code is `0` and all Phase 1 regression tests + Phase 2 scenario tests in `tests/` pass.
3. Confirm determinism SHA-256 passes for Nights 1, 2, and 3, and full Night 3 (21,600 ticks) finishes in `<= 30s`.
4. Inspect `docs/proof/phase-2/verify_summary.json` and `docs/proof/phase-2/unittest_output.txt` to ensure proof matches the current commit.
5. Verify `git status` has no `.env`, secrets, or temporary scratch files before tagging.
