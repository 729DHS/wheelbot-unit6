#!/bin/bash
# connect_unit5.sh — 连接 Unit5 串口 Shell
# 用法: ./scripts/connect_unit5.sh [/dev/ttyACM0]

set -euo pipefail

PORT="${1:-/dev/ttyACM0}"
BAUD="${BAUD:-115200}"

echo "[connect_unit5] 连接 ${PORT} @ ${BAUD} ...

if command -v picocom &>/dev/null; then
    picocom -b "${BAUD}" "${PORT}"
elif command -v minicom &>/dev/null; then
    minicom -D "${PORT}" -b "${BAUD}"
elif command -v screen &>/dev/null; then
    screen "${PORT}" "${BAUD}"
else
    echo "[ERROR] 未找到 picocom/minicom/screen，请安装其中之一"
    exit 1
fi
