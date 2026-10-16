#!/usr/bin/env bash
# Run every suite and keep the results in reports/ and sql/ as evidence.
#   ./run_tests.sh            (uses ENV=local unless ENV is set)
set -u
cd "$(dirname "$0")"
PYTEST=.venv/bin/pytest

rm -rf reports && mkdir -p reports

{
  echo "=== $(date -u '+%Y-%m-%d %H:%M:%S') UTC | ENV=${ENV:-local} ==="
  echo
  status=0  # any failing step fails the whole run

  echo "### 1. Main suite: UI + API + SQL"
  $PYTEST -rxXf || status=1

  echo
  echo "### 2. Self-healing, healer OFF: the broken locators are expected to fail (xfail)"
  # each run gets its own --output: pytest-playwright empties that folder at session start
  # --tracing=on: these scenarios xfail, so keep their traces as evidence of the broken locators
  $PYTEST -m self_healing -rxX --tracing=on --output=reports/artifacts-self-healing-broken \
    --html=reports/self-healing-broken.html --junitxml=reports/self-healing-broken.xml || status=1

  echo
  echo "### 3. Self-healing, healer ON: broken locators healed at runtime"
  SELF_HEAL=true $PYTEST -m self_healing --output=reports/artifacts-self-healing-healed \
    --html=reports/self-healing-healed.html --junitxml=reports/self-healing-healed.xml || status=1

  echo
  echo "### 4. SQL scenario outputs"
  .venv/bin/python -m sql.sql_runner || status=1

  echo
  echo "### 5. Evidence screenshots (app screens and report summaries)"
  .venv/bin/python -m tools.capture_evidence || status=1

  echo "Overall exit code: $status"
  exit $status
} 2>&1 | tee reports/console.log
status="${PIPESTATUS[0]}"

# Keep the committed log free of local machine paths
sed -i "s|$PWD|.|g" reports/console.log
exit "$status"
