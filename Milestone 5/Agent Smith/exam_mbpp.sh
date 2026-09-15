#!/usr/bin/env bash
# ./exam_mbpp.sh --student-path ./student --moulinette-path ./moulinette --env-file /path/to/.env
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/exam_runner.py" mbpp "$@"
