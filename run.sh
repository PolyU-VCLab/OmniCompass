#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$ROOT/code/run_eval.py" ]]; then
  exec "${PYTHON:-python3}" "$ROOT/code/run_eval.py" "$@"
fi
export PYTHONPATH="$ROOT/..${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python3}" "$ROOT/run_eval.py" "$@"
