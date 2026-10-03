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
| **ruff** | staged `*.py` | lint errors against `pyproject.toml`'s rule set |
| **import-linter** | whole repo (when Python is staged) | a broken architecture contract (layering, domain-is-framework-free) |
| **tsc** | `ui/` (when `ui/**/*.ts[x]` is staged) | TypeScript type errors |
| **mypy** | `src` (opt-in: `RUN_MYPY=1`) | type errors — off by default; declared in `pyproject.toml` |

Design choices:
- **ruff runs only on the files you're committing** (boy-scout rule). The repo carries
  pre-existing lint debt in untouched files; that is deliberately not your commit's
  problem. Clean up a legacy file's warnings when you touch it.
- A tool that is **installed but failing blocks** the commit. A tool that is **not
  installed is reported and skipped** (except ruff/import-linter, which are required dev
  deps and will block if missing), so a missing optional toolchain never wedges a commit.

## Fixing / bypassing

```bash
python -m ruff check --fix <files>   # auto-fix most ruff findings, then re-stage
git commit --no-verify               # emergency bypass — explain why in the message
SKIP_LINT=1 git commit ...           # same, honored by the hook
RUN_MYPY=1 git commit ...            # also run mypy this time
```

## Dependencies

```bash
python -m pip install 'ruff==0.6.9' 'import-linter==2.1' 'mypy==1.11.2'
npm --prefix ui install   # for the UI typecheck
```
