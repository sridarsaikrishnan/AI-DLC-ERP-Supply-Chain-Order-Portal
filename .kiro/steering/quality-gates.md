---
inclusion: always
---

# Quality gates (format, lint, contracts, tests)

These are mandatory verification gates for the AI-DLC **Construction** phase. They apply
to every Code Generation stage (per unit) and the Build and Test stage. The pre-commit
hook (`.githooks/pre-commit`, installed via `scripts/install-hooks.sh`) enforces the same
checks at commit time — but do not wait for the hook: run these as part of the workflow
and make them pass **before presenting a stage as complete**.

## Before presenting ANY Code Generation or Build-and-Test stage completion

Run, from the repo root, and ensure each passes:

1. **Format** — `python -m ruff format src tests migrations scripts`
   Then confirm it is stable: `python -m ruff format --check src tests migrations scripts`
   (no files would be reformatted).
2. **Lint** — `python -m ruff check src tests migrations scripts` → must print
   `All checks passed!`. Prefer `--fix` for auto-fixable findings; fix the rest by hand.
   Do not weaken `pyproject.toml`'s rule set to make this pass.
3. **Architecture contracts** — `lint-imports` → `Contracts: N kept, 0 broken`.
   A broken contract is a design error (a layer or the framework-free domain boundary was
   violated), not a lint nit — fix the import, never add an exception to silence it.
4. **Tests** — `APP_PROFILE=memory python -m pytest src tests -q` → no failures. Add/adjust
   tests for the behavior you changed; a stage that changes behavior without tests is not
   complete.
5. **UI (only when `ui/` changed)** — `npm --prefix ui run build` (tsc + vite) → clean.

If a required tool is missing, install the pinned versions and continue — do not skip the
gate:
`python -m pip install 'ruff==0.6.9' 'import-linter==2.1' 'mypy==1.11.2'`.

## Rules

- **Never** present a Construction stage as complete, and never commit, with any gate
  failing. If something genuinely cannot pass in this environment (e.g. live Postgres/AWS
  integration tests that self-skip), say so explicitly and state what was and was not
  verified — do not silently ignore it.
- **New or changed code must be clean**, even if the file carried pre-existing debt
  (boy-scout rule). Reducing the project's standards (editing `pyproject.toml`'s ruff
  `select`, adding blanket `# noqa`, or `--no-verify`) is not an acceptable way to make a
  gate pass; it needs the user's explicit approval and a recorded reason.
- Record the gate results in the Build-and-Test summary / `aidlc-docs/aidlc-state.md`
  (e.g. "ruff clean, lint-imports 0 broken, pytest N passed/M skipped, ui build clean"),
  the same way existing increments do.
- Keep `ruff format` as the single source of truth for formatting; do not hand-format
  against it.
