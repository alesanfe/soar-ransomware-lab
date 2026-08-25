# Devin Rules — SOAR Ransomware Lab

## Git safety (HARD RULES — never violate)

The user works for weeks without committing. The working tree is the source of truth,
NOT the last commit. Treat the working tree as sacred.

### Forbidden without explicit per-session user confirmation

- `git reset` (any mode, any ref)
- `git checkout -- <path>` / `git checkout .` / `git restore`
- `git stash` (push, pop, apply, drop, clear)
- `git clean -fd` / `git clean -x`
- `git rebase` / `git commit --amend` / `git update-ref`
- `git branch -D` / `git push --force` / `git push -f`
- `git rm` / `git revert`
- `git checkout <branch>` when there are uncommitted changes

### Allowed (read-only, safe)

- `git status`, `git diff`, `git log`, `git reflog`, `git show`, `git stash list`
- `git add` (staging is reversible)
- `git commit` (only when user asks; never amend)
- `git push` (only when user explicitly asks; never force)

### If a script broke files

Fix the specific files with `edit`/`write` tools. NEVER use `git checkout` to "restore"
them — that discards the user's unrelated uncommitted changes across the whole repo.

### If you ran a forbidden command by mistake

Tell the user immediately. Do not attempt to hide or quietly repair it. Recovery may be
possible via `git reflog` or `git fsck --lost-found` but only if the user is informed promptly.
