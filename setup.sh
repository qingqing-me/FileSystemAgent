#!/usr/bin/env bash
# GXU Agent 一键初始化 (Linux/macOS)
#
# 用法:
#   ./setup.sh                    # 完整初始化
#   ./setup.sh --skip-frontend    # 只初始化后端
#
# 服务器下载快照需要代理时:
#   HTTPS_PROXY=http://127.0.0.1:7890 ./setup.sh

set -e
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
    echo "❌ 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

exec "$PY" scripts/setup.py "$@"
