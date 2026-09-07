# Contributing to astra-daw-guard

This file is about *doing engineering work on this repository itself*
(policy rules, `policy_engine/`, `enforcement/`, tests, docs) — not
about using the guardrail on a DAW. If you're an agent about to
operate a DAW, read `AGENTS.md` / `SKILL.md` instead.

These are conventions this repo's own history found necessary the hard
way (see the commits/PRs cited below), not aspirational advice.

## Before starting new work: confirm your branch

`git branch --show-current` and `git status` before writing anything.
This session's own history includes at least two cases of new work
starting on top of an unrelated, already-pushed feature branch instead
of `main`, which then had to be untangled with `git stash` +
re-branching. Cheap to avoid, annoying to fix after the fact.

## Batch tightly-coupled changes into one PR

Prefer one PR per *root cause*, not one PR per file or per tiny
feature. This repo went through a stretch of many small, sequential
PRs (roughly PRs #17-#30), each editing the same two spots —
`.github/workflows/checks.yml`'s test-invocation line and
`policy_engine/README.md`'s test-count sentence — purely to
accommodate one more test file. That caused three separate, avoidable
merge conflicts in the same session (see Issue #31, which fixed the
structural cause: CI now uses `unittest discover`, and the README test
list is an append-only bullet list rather than a shared sentence).

The conflict-proneness was a symptom; the root cause was splitting
work more finely than the actual dependency graph required. If two
changes will touch the same paragraph or the same CI line, that's a
signal to do them in one PR, not two.

## Squash-merges and commit message accuracy

If a commit message needs to say something exact (e.g. a specific
attribution line, a specific `Issue #N` reference), don't assume
`git commit`'s message survives a GitHub squash-merge verbatim.
GitHub's squash-merge composes its own message by default and
re-formats `Co-authored-by` trailers into its own canonical form
(lowercased, and it will drop extra text after the name) rather than
preserving your exact casing/wording. If the exact text matters, pass
`commit_title`/`commit_message` explicitly to the merge call instead
of relying on the default.

## Verifying a change is safe

Before merging anything, confirm — don't assume:

- `python3 -m unittest discover -s tests -p "test_*.py" -v` passes
- `git diff origin/main -- policy/ policy_engine/rules.py mcp-reaper/
  mcp-ableton/ mcp-ardour/ enforcement/boundary.py` is empty unless the
  PR is deliberately changing one of those (and if it is, that's
  worth calling out explicitly in the PR body, not just implied by
  the diff)

## Independent review for anything touching `policy_engine/` or `enforcement/`

These are the repo's one authoritative safety gate. Run an actual
review pass (e.g. the `code-review` skill, or equivalent) against
changes here before merging, in addition to the automated test suite
you wrote alongside the change — tests written by the same pass that
wrote the implementation tend to encode the same blind spots as the
implementation. Issue #34 is a concrete example: an actual review pass
(not just running the existing test suite) found three real
fail-closed violations (crashes on malformed input types) that had
gone unnoticed through several prior rounds of feature work on the
same files.
