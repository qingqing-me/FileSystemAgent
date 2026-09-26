#!/usr/bin/env python3
"""
一键初始化 — 装依赖、配置 API Key、导入数据快照

新环境 clone 仓库后跑这一条命令即可开始开发，无需爬取 40 分钟。

用法:
    python scripts/setup.py                  # 完整初始化
    python scripts/setup.py --skip-frontend  # 跳过前端依赖（只做后端）
    python scripts/setup.py --skip-data      # 跳过数据导入

Windows: setup.bat
Linux/macOS: ./setup.sh
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
CHROMA_DIR = BACKEND / "chroma_data"
DB_FILE = BACKEND / "school_rag.db"
ENV_FILE = BACKEND / ".env"
ENV_EXAMPLE = BACKEND / ".env.example"

sys.path.insert(0, str(ROOT / "scripts"))


def log(msg: str, icon: str = "  "):
    print(f"{icon} {msg}")


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> bool:
    """执行外部命令"""
    try:
        subprocess.run(cmd, cwd=cwd, check=check)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        log(f"未找到命令: {cmd[0]}", "❌")
        return False


def has_data() -> bool:
    """检查是否已有数据（向量库非空）"""
    if not CHROMA_DIR.exists() or not DB_FILE.exists():
        return False
    # 向量库里有实际文件才算有数据
    return any(f.is_file() and f.stat().st_size > 1024 for f in CHROMA_DIR.rglob("*"))


# ============ 各步骤 ============

def step_check_python():
    log("检查 Python 环境...", "1️⃣")
    if sys.version_info < (3, 10):
        log(f"Python 版本过低: {sys.version.split()[0]}，需要 3.10+", "❌")
        sys.exit(1)
    log(f"Python {sys.version.split()[0]} ✅", "  ")


def step_install_backend():
    log("安装后端依赖（首次较慢，含 torch/chromadb 约 2-3 GB）...", "2️⃣")
    req = BACKEND / "requirements.txt"
    if not run([sys.executable, "-m", "pip", "install", "-r", str(req)]):
        log("后端依赖安装失败，请检查网络或手动执行:", "❌")
        log(f"  pip install -r {req}", "  ")
        sys.exit(1)
    log("后端依赖安装完成 ✅", "  ")


def step_configure_env():
    log("配置环境变量...", "3️⃣")
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8", errors="replace")
        if "sk-your-api-key-here" in content or "LLM_API_KEY=\n" in content or not re.search(r"LLM_API_KEY=sk-\w{10,}", content):
            log("检测到 .env 中的 API Key 尚未配置", "⚠️")
        else:
            log(".env 已存在且已配置 ✅", "  ")
            return
    else:
        if not ENV_EXAMPLE.exists():
            log("未找到 .env.example，跳过", "⚠️")
            return
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        log("已从 .env.example 创建 .env", "  ")

    print()
    log("需要 DeepSeek API Key 才能使用问答功能", "  ")
    log("获取地址: https://platform.deepseek.com/api_keys", "  ")
    key = input("  请输入 API Key（回车跳过，稍后手动编辑 backend/.env）: ").strip()

    if key:
        content = ENV_FILE.read_text(encoding="utf-8")
        content = re.sub(r"^LLM_API_KEY=.*$", f"LLM_API_KEY={key}", content, flags=re.M)
        ENV_FILE.write_text(content, encoding="utf-8")
        log("API Key 已写入 backend/.env ✅", "  ")
    else:
        log("已跳过，记得稍后编辑 backend/.env 填入 Key", "  ")


def step_import_data():
    log("导入数据快照...", "4️⃣")
    if has_data():
        log("本地已有数据，跳过导入（如需更新: snapshot import）", "  ")
        return

    import snapshot
    try:
        snapshot.download_snapshot(tag=None, force=True)
    except SystemExit:
        log("数据导入失败。可稍后手动执行: snapshot.bat import", "⚠️")
        log("  （不影响代码开发，但问答功能需要数据）", "  ")


def step_install_frontend():
    log("安装前端依赖...", "5️⃣")
    if (FRONTEND / "node_modules").exists():
        log("前端依赖已存在，跳过 ✅", "  ")
        return

    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        log("未找到 npm，请先安装 Node.js: https://nodejs.org/", "⚠️")
        log(f"  手动执行: cd {FRONTEND} && npm install", "  ")
        return

    if not run([npm, "install"], cwd=FRONTEND):
        log("前端依赖安装失败，可手动执行: cd frontend && npm install", "⚠️")
        return
    log("前端依赖安装完成 ✅", "  ")


def step_summary():
    print()
    print("=" * 55)
    log("初始化完成！", "🎉")
    print("=" * 55)
    print()
    log("启动服务:", "  ")
    log("  后端:  cd backend && python -m uvicorn app.main:app --port 8000", "    ")
    log("  前端:  cd frontend && npm run dev          （另一个终端）", "    ")
    log("  访问:  http://localhost:5173", "    ")
    print()
    log("常用命令:", "  ")
    log("  snapshot.bat info     查看数据状态", "    ")
    log("  snapshot.bat import   更新数据快照", "    ")
    log("  sync.bat              同步文件系统新文件", "    ")
    print()


# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description="GXU Agent 一键初始化")
    parser.add_argument("--skip-backend", action="store_true", help="跳过后端依赖安装")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端依赖安装")
    parser.add_argument("--skip-data", action="store_true", help="跳过数据导入")
    args = parser.parse_args()

    print()
    print("=" * 55)
    log("GXU 校园文件智能助手 — 初始化", "🚀")
    print("=" * 55)
    print()

    step_check_python()

    if not args.skip_backend:
        step_install_backend()
    else:
        log("跳过后端依赖安装", "2️⃣")

    step_configure_env()

    if not args.skip_data:
        step_import_data()
    else:
        log("跳过数据导入", "4️⃣")

    if not args.skip_frontend:
        step_install_frontend()
    else:
        log("跳过前端依赖安装", "5️⃣")

    step_summary()


if __name__ == "__main__":
    main()
