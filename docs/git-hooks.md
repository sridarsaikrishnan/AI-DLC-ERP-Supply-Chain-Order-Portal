# Git hooks

A pre-commit hook enforces linting so broken code doesn't get committed. The hook is
version-controlled in `.githooks/` (not `.git/hooks/`, which git never shares), so the
whole team runs the same checks.

## Install (once per clone)

```bash
bash scripts/install-hooks.sh
```

This sets `core.hooksPath=.githooks` (a local, per-clone git setting — not committed).
Undo with `git config --unset core.hooksPath`.

## What the pre-commit hook checks

| Check | Scope | Blocks on |
|---|---|---|
| **ruff** | staged `*.py` | auto-fixes + formats first (`ruff check --fix` + `ruff format`, re-staged), then blocks on anything left (e.g. undefined names) |
| **import-linter** | whole repo (when Python is staged) | a broken architecture contract (layering, domain-is-framework-free) |
| **tsc** | `ui/` (when `ui/**/*.ts[x]` is staged) | TypeScript type errors |
| **mypy** | `src` (opt-in: `RUN_MYPY=1`) | type errors — off by default; declared in `pyproject.toml` |

Design choices:
- **Auto-format on commit.** The hook runs `ruff check --fix` + `ruff format` on the
  staged Python files and re-stages them, so your commit lands already-clean. It only
  touches *fully* staged files — a file with both staged and unstaged edits is left alone
  (re-adding it would pull the unstaged hunks into your commit); fix those by hand.
  Disable with `NO_FIX=1` to only check.
- **ruff runs only on the files you're committing** (boy-scout rule). The repo carries
  pre-existing lint debt in untouched files; that is deliberately not your commit's
  problem. Clean up a legacy file's warnings when you touch it.
- A tool that is **installed but failing blocks** the commit. A tool that is **not
  installed is reported and skipped** (except ruff/import-linter, which are required dev
  deps and will block if missing), so a missing optional toolchain never wedges a commit.

## Fixing / bypassing

```bash
# the hook already runs these on staged files and re-stages the result:
python -m ruff check --fix <files>   # auto-fix lint findings
python -m ruff format <files>        # auto-format

NO_FIX=1 git commit ...              # check only; don't auto-fix/format
git commit --no-verify               # emergency bypass — explain why in the message
SKIP_LINT=1 git commit ...           # same, honored by the hook
RUN_MYPY=1 git commit ...            # also run mypy this time
```

## Dependencies

```bash
python -m pip install 'ruff==0.6.9' 'import-linter==2.1' 'mypy==1.11.2'
npm --prefix ui install   # for the UI typecheck
```
