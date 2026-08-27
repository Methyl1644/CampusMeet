#!/bin/bash

set -e
# 导出环境变量

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${DEPLOY_RUN_PORT:-5000}"

usage() {
  echo "用法: $0 -p <端口>"
}

while getopts "p:h" opt; do
  case "$opt" in
    p)
      PORT="$OPTARG"
      ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "无效选项: -$OPTARG"
      usage
      exit 1
      ;;
  esac
done

cd "$PROJECT_DIR"
export COZE_WORKSPACE_PATH="$PROJECT_DIR"
export COZE_PROJECT_TYPE=agent

# 激活 .venv（devbox 环境），deploy 无 .venv 则跳过
if [ -f "${PROJECT_DIR}/.venv/bin/activate" ]; then
  source "${PROJECT_DIR}/.venv/bin/activate"
fi

python "${PROJECT_DIR}/src/main.py" -m http -p "$PORT"
