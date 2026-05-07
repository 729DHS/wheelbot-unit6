#!/bin/bash
# quick_status.sh — 快速获取 Unit5 电机状态
# 用法: ./scripts/quick_status.sh [/dev/ttyACM0]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${1:-/dev/ttyACM0}"

echo "[quick_status] 查询 ${PORT} ..."
python3 "${PROJECT_DIR}/tools/serial_test.py" --port "${PORT}" --cmd "motor status" --timeout 2
