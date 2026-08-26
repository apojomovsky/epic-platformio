# AGENTS.md

`platform-pic8` is the PlatformIO platform for the open-source 8-bit PIC
ecosystem: `platform.json`, the SCons builder, and board definitions that make
`pio run` compile a project with [epic-cc](https://github.com/apojomovsky/epic-cc)
instead of Microchip's licence-gated XC8. It is the PlatformIO glue only. The
compiler is epic-cc, the HAL is epic-hal, and this repository is neither.

## The decomposition of record

The map and the decisions that constrain every piece of this repository live in
[`epic-cc/docs/31-ecosystem-integration-design.md`](https://github.com/apojomovsky/epic-cc/blob/master/docs/31-ecosystem-integration-design.md).
Read it before touching code. This repo's sub-projects are PIO-1 (platform
core), PIO-2 (package plumbing) and PIO-3 (registry and examples), section 3
of that document.

**Why this repository exists (D-6).** PlatformIO's registry model is one
repository per platform, referencing toolchain and framework packages by URL.
Folding the platform into either existing repo would weld that repo's release
tags to PlatformIO package versions, which goes wrong the first time a board
JSON needs a fix that no compiler change justifies. Board-definition fixes land
here without needing a compiler release; that is the point.

## Picking up work

Work across epic-cc, epic-hal and epic-platformio is coordinated by
[epic-tasks](https://github.com/apojomovsky/epic-tasks). Several agents, from
different providers and on different machines, share one GitHub account, so the
board is the only place that knows what is already taken. **Do not choose a
ticket by reading the issue list.**

Run once per machine (and after any env change):

0. `epic-tasks doctor`: checks `EPIC_AGENT_ID`, `EPIC_TASKS_PROJECT`,
   `gh` auth with `project` scope, and board reachability. Fix what it
   reports before claiming.

For every ticket:

1. `epic-tasks next` to see what you may take, `epic-tasks claim <repo>#<n>` to
   take it. Exit 2 means another agent won the race, so go back to `next`.
   Exit 3 means the board is unreachable: do the work and say so in the pull
   request. Exit 4 means stop and ask.
2. Create a worktree under `.worktrees/` and branch as
   `<type>/<issue>-<slug>`, for example `feat/1-repo-bootstrap`
   (see Worktrees below, never work on `master`).
3. Work, then run the takeoff ritual (`epic-tasks takeoff`).
4. Open the pull request with `Closes #N`, then
   `epic-tasks review <repo>#<n> --pr <url>`. The body must use real newlines:
   copy-paste-safe ``gh pr create --body-file - <<'EOF'`` (or
   ``cat <<'EOF' > /tmp/pr_body.md`` + ``gh pr create --body-file /tmp/pr_body.md``),
   NEVER ``gh pr create --body "a\nb"``, the shell never expands ``\n`` so GitHub
   renders literal ``\n`` as text and the bullets collapse to one line (epic-cc#129):
   ```bash
   cat <<'EOF' > /tmp/pr_body.md
   Closes #N

   Summary of the change.

   - bullet one
   - bullet two
   EOF
   gh pr create --title "feat(scope): summary" --body-file /tmp/pr_body.md
   # - or inline: gh pr create --title "..." --body-file - <<'EOF'
   ```
   Heal an existing PR with ``gh pr edit --body-file - <<'EOF'`` or
   ``python3 -c 'from epic_tasks.gh import normalize_pr_body; print(normalize_pr_body(open("body.txt").read()))'``.
   The local ``check_pr_body`` gate (``epic_tasks/takeoff.py``) warns (advisory);
   the ``pr-body.yml`` CI workflow that fails on literal ``\n``/``\r`` exists in
   epic-cc and epic-hal, not here yet, so CI does not enforce it.
5. After the PR merges, remove the worktree:
   `git worktree remove .worktrees/<name>`. Never remove a worktree before
   merge, the branch must stay reachable for review.

Set `EPIC_AGENT_ID` (`<runtime>@<host>`) and `EPIC_TASKS_PROJECT` once per
runtime and machine. `claim` refuses to act without an identity, because an
anonymous claim tells the other agents nothing.

An issue also carries `area:*` labels naming the surfaces it touches. Two
tickets sharing an area cannot be worked at the same time even when neither
blocks the other, which is why selection goes through the tool: what is
blocked, taken, or conflicting is decided there, not in this file.

## Worktrees

**All feature work happens in a worktree under `.worktrees/`**, never on
`master`, and worktrees are removed only after the PR merges:

```bash
git fetch origin master
git worktree add .worktrees/<name> -b <branch> origin/master
# ... work, PR, merge ...
git worktree remove .worktrees/<name>
```

Branch names are conventional: `feat/<description>`, `fix/<description>`,
`chore/<description>`, `docs/<description>`. The worktree keeps your
master checkout clean and lets several tasks run in parallel without
touching each other's trees. Squash merging keeps master plan-free.
The default base is the latest `origin/master`; branching off a different
branch is the exception, reserved for multi-step work other tasks build on
in parallel.

Worktree discipline is enforced by the takeoff ritual (`epic-tasks takeoff`
checks you are in a `.worktrees/` worktree and not on `master`).

## Takeoff ritual (before every PR)

Run `epic-tasks takeoff` before opening a PR. It is the shared skeleton used
by every epic repository (canonical checks live in
`epic-tasks/epic_tasks/takeoff.py`). It checks:

1. Working tree clean, branch not behind `origin/master` (or `$BASE_REF`).
2. **You are in a `.worktrees/` worktree**, not on `master`.
3. **No plan files in the PR's final diff.** Plans live through
   development; the final commit distills load-bearing decisions into
   the living docs and `git rm`s the plan. Squash merging then keeps master
   plan-free.
4. Commit hygiene: conventional single-line subjects, no trailers,
   no em-dashes, no whitespace errors.
5. **Comment and doc prose review.** `epic-tasks prose --verify` (part of
   this ritual) fails it on the mechanical rules: the 8-line block cap, no
   `@file`/`@brief` decoration, no iteration or verification narrative, no
   em-dashes. Content judgment stays the agent's: read the listing the
   script prints and fix what does not hold up against the conventions
   (why, not what; a comment must earn its lines).
6. **PR body hygiene: real newlines only.** PR descriptions must use
   actual newlines (``gh pr create --body-file <file>`` or a heredoc),
   never an inline ``"a\n\n- b"`` that renders literally as ``\n`` on
   GitHub (epic-cc#129). The takeoff ritual (``check_pr_body`` in
   ``epic_tasks/takeoff.py`` + ``epic_tasks.gh:normalize_pr_body``) warns (advisory);
   the ``pr-body.yml`` CI workflow that fails on literal ``\n``/``\r`` exists in
   epic-cc and epic-hal, not here yet, so CI does not enforce it. Heal with
   ``gh pr edit --body-file``.

The ritual exits 1 with the exact fix list while blocking items are
outstanding. Don't skip it; the CI gate does not cover the ritual. The
prose step is a hard gate: a block that violates the mechanical rules
fails the ritual and blocks the push.

## Commit hygiene

- **Conventional Commits, single line, <= 3 lines.**
  `feat(scope): summary`, `fix(...)`, `chore(...)`, `docs(...)`,
  `build(...)`, `ci(...)`, `test(...)`. Scope is usually the crate
  (`builder`, `boards`) or `ci`.
- **Never `Co-Authored-By:` or any other trailer, and no em-dashes
  (,).** The commit-msg hook from epic-tasks (installed via
  `make setup-hooks` in the epic-tasks clone) rejects both. Use a
  comma, a colon, or a period instead. Git history is the record; the
  commit message is yours.
- **PR bodies use real newlines.** ``gh pr create --body-file`` or a
  heredoc, never ``--body "line\nnext"``. Literal ``\n`` is rejected by
  takeoff (epic-cc#129).
- Commit whenever a piece of work is finished; don't batch unrelated
  changes.
- Update the docs a change touches before calling it done.

## Ground rules

- **Approval gates are real.** Brainstorm → design → approve →
  implement. Present a design and stop until you get a yes, even for
  work that looks small.
- **No force pushes.** Rewriting a branch that already exists on the
  remote drops it for every other agent and clone; the pre-push hook
  from epic-tasks (installed via `make setup-hooks` in the epic-tasks
  clone) refuses it. If the guard is triggered, rebase onto master and
  get the human's explicit go-ahead before re-running with
  `EPIC_FORCE_PUSH_APPROVED=1 git push --force-with-lease`.

## Expression conventions (comments and docs)

1. **Why, not what.** Code says what it does; comments carry the
   non-obvious reason, the datasheet fact, the invariant. A comment
   that restates the line below it is deleted.
2. **A comment must earn its lines.** More comment lines than code is a
   smell. The block ladder is 1 to 8 lines: 2 to 3 lines for a compact
   reason, 4 to 8 only when the reason genuinely needs the room, over 8
   is a hard failure of the prose gate.
3. **No decoration.** No `/* --- name --- */` separators, no
   `@file`/`@brief` boilerplate repeating the filename.
4. **No narrative.** No "fixed X by doing Y", no iteration or session
   prose. Verification claims about a change belong in the PR and
   commit, not in the tree, where they go stale.
5. `TODO`/`FIXME` carry a concrete reason or do not exist.
6. **No em-dashes (,) in prose.** Not in comments, docs, or commit
   messages: use a comma, a colon, or a period and a new sentence.
   The exception is ascii-art diagrams, where alignment may force
   them. The takeoff ritual and the commit-msg hook enforce this.
   Replacing an em-dash is a judgment call, not a swap: pick the
   replacement (and split or reorder the sentence when needed) so
   the result reads as prose.

## CI

`.github/workflows/ci.yml` runs on every push/PR: it lints the JSON
manifests (`platform.json`, `boards/*.json`) and byte-compiles the
`builder/` Python, so the platform skeleton lands against a gate rather
than adding one later. The gate is deliberately minimal until PIO-1
brings a real build to gate on.
