#!/usr/bin/env bash
# GXU 数据快照工具 (Linux/macOS)
#
# 用法:
#   ./snapshot.sh export     导出快照
#   ./snapshot.sh publish    导出并发布到 GitHub Release
#   ./snapshot.sh import     下载并恢复最新快照
#   ./snapshot.sh list       列出已发布的快照
#   ./snapshot.sh info       查看当前数据状态
#
# 如果服务器访问 GitHub 需要代理:
#   HTTPS_PROXY=http://127.0.0.1:7890 ./snapshot.sh publish

set -e
cd "$(dirname "$0")"

# 优先用 python3，回退到 python
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
    echo "❌ 未找到 Python，请先安装"
    exit 1
fi

exec "$PY" scripts/snapshot.py "$@"
