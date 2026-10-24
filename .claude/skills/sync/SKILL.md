---
name: sync
description: Take the latest from origin main into the local project folder - fetch, check for local changes and unpushed commits, fast-forward pull only, then summarise what came in. Use when the user says "sync", "pull the latest", "take the latest from origin main", "update the skills", or wants the newest skills and scripts from the shared repo before starting QA work.
---

# sync

Brings the local project up to date with `origin/main` without losing anything. Run every command from the project folder (the one that holds `.claude/` and `work/`). Never force: no `--force`, no `reset --hard`, no `checkout -- .`, no stash drops.

## Steps

1. **Fetch and compare**
   ```
   git fetch origin
   git status -sb
   git log --oneline HEAD..origin/main
   git log --oneline origin/main..HEAD
   ```
   The first log lists what is new on origin; the second lists local commits that are not pushed. Say which branch you are on (it should be `main`; if it is not, say so and ask before switching).

2. **Decide**
   - Nothing new on origin: say "already up to date" and stop.
   - Local commits not on origin (ahead) and new commits on origin (behind) at the same time: the branches have diverged. Do not merge or rebase on your own. Show both lists and ask how to proceed.
   - Uncommitted changes to tracked files: list them (`git status --short`). If any of them is a file that the incoming commits also change (`git diff --name-only HEAD..origin/main`), stop and ask: commit, or stash and restore, or leave. If they do not overlap, the pull can go ahead.
   - Untracked files and folders (for example `work/`, `reports/`, `artifact-*/`) are not touched by a pull; leave them alone.

3. **Pull, fast-forward only**
   ```
   git pull --ff-only origin main
   ```
   If it refuses, report the reason; do not try another way.

4. **Report what came in**, short: the new commits (one line each), the files changed (`git diff --stat ORIG_HEAD..HEAD`), and anything the person should act on, for example:
   - a skill or script changed under `.claude/skills/` (the next run uses the new version);
   - `artifact-special/` or `qa-artifact-from-findings/tracker/` changed (artifacts already published do not change until they are rebuilt and republished);
   - a new dependency in a SKILL.md (for example `pip install pillow`).

## Notes
- Pushing is a separate step and only on request; this skill never pushes.
- If the remote has other branches the user cares about, `git fetch origin` already has them; ask before switching.
