#!/usr/bin/env bash
#
# One-time setup: point git at the version-controlled hooks in .githooks/.
# Run once per clone:
#
#     bash scripts/install-hooks.sh
#
# This sets `core.hooksPath` (a local, per-clone git setting — it is not committed and
# affects only your working copy). Undo with: git config --unset core.hooksPath
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

chmod +x .githooks/* 2>/dev/null || true
git config core.hooksPath .githooks

echo "Installed git hooks from .githooks/ (core.hooksPath=.githooks)."
echo "Pre-commit linting is now active. Bypass once with: git commit --no-verify"
