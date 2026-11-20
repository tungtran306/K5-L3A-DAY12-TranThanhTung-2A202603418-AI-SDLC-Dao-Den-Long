---
name: verify-phase
description: Run the full build, unit tests, Test Contract headless scenarios, and determinism check for Dao Den Long, saving real proof artifacts before tagging a phase.
---

# Verify Phase Skill

Use this skill before committing or tagging any phase (`phase-1` .. `phase-4`).

## Steps
1. Run `python3 scripts/verify.py` from the repository root.
2. Confirm exit code is `0` and all tests in `tests/` passed without skipping.
3. Inspect `docs/proof/phase-1/verify_summary.json` and `unittest_output.txt` to verify the proof matches the current working tree.
4. Verify `git status` contains no `.env`, secrets, or temporary scratch files.
5. Only after all checks are green, commit and tag the phase.
