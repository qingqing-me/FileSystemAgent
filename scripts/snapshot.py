#!/usr/bin/env python3
"""
数据快照工具 — 导出 / 发布 / 导入 RAG 数据快照

把 SQLite 元数据 + ChromaDB 向量库打包成快照，发布到 GitHub Release，
其他环境（本地开发、服务器部署）直接下载即可，无需重新爬取和 embedding。

用法:
    python scripts/snapshot.py export              # 导出快照到 snapshots/
    python scripts/snapshot.py publish             # 导出并发布到 GitHub Release
    python scripts/snapshot.py import              # 下载并恢复最新快照
    python scripts/snapshot.py import --tag xxx    # 恢复指定版本
    python scripts/snapshot.py list                # 列出所有可用快照
    python scripts/snapshot.py info                # 查看当前数据状态

注意:
    - 导出前请先停止后端服务（避免 ChromaDB 写入不一致）
    - 发布/下载需要 gh CLI 已登录，且网络能访问 GitHub（可能需要代理）
"""

import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

# Windows 终端默认 GBK，重配置为 UTF-8 以支持 emoji 输出
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ============ 路径 ============

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DB_FILE = BACKEND / "school_rag.db"
CHROMA_DIR = BACKEND / "chroma_data"
SNAPSHOT_DIR = ROOT / "snapshots"

MANIFEST_NAME = "manifest.json"
BACKEND_PORT = 8000


# ============ 工具函数 ============

def log(msg: str, icon: str = "  "):
    print(f"{icon} {msg}")


def is_backend_running() -> bool:
    """检查后端是否在运行（端口 8000 是否被监听）"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(("127.0.0.1", BACKEND_PORT))
    s.close()
    return result == 0


def get_doc_count() -> int:
    """从 SQLite 读取文档数"""
    try:
        con = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        cur = con.execute("SELECT COUNT(*) FROM document_sources")
        count = cur.fetchone()[0]
        con.close()
        return count
    except Exception:
        return 0


def get_chromadb_version() -> str:
    """读取已安装的 chromadb 版本"""
    try:
        import chromadb
        return chromadb.__version__
    except Exception:
        return "unknown"


def run_gh(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """调用 gh CLI"""
    try:
        return subprocess.run(
            ["gh"] + args,
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except FileNotFoundError:
        log("未找到 gh CLI，请先安装: https://cli.github.com/", "❌")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "").strip() if capture else str(e)
        log(f"gh 命令失败: {msg}", "❌")
        sys.exit(1)


def get_repo() -> str:
    """获取当前仓库的 owner/name"""
    result = run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], capture=True)
    return result.stdout.strip()


# ============ 导出 ============

def export_snapshot(skip_running_check: bool = False) -> Path:
    """打包数据成快照文件，返回快照路径"""
    log("开始导出数据快照...", "📦")

    # 数据检查
    if not DB_FILE.exists():
        log(f"未找到数据库文件: {DB_FILE}", "❌")
        sys.exit(1)
    if not CHROMA_DIR.exists():
        log(f"未找到向量库目录: {CHROMA_DIR}", "❌")
        sys.exit(1)

    # 一致性检查：后端运行时 ChromaDB 可能正在写入
    if is_backend_running() and not skip_running_check:
        log("后端服务正在运行，导出可能不一致！", "⚠️")
        log("请先停止后端，或加 --force 强制导出", "  ")
        sys.exit(1)

    SNAPSHOT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_path = SNAPSHOT_DIR / f"gxu-rag-snapshot-{stamp}.tar.gz"

    # 元信息
    manifest = {
        "exported_at": datetime.now().isoformat(),
        "doc_count": get_doc_count(),
        "chromadb_version": get_chromadb_version(),
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "files": ["school_rag.db", "chroma_data/"],
    }

    # 打包
    log("正在打包（数据库 + 向量库）...", "  ")
    tmp_manifest = SNAPSHOT_DIR / MANIFEST_NAME
    tmp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        with tarfile.open(snapshot_path, "w:gz") as tar:
            tar.add(DB_FILE, arcname="school_rag.db")
            tar.add(CHROMA_DIR, arcname="chroma_data")
            tar.add(tmp_manifest, arcname=MANIFEST_NAME)
    finally:
        tmp_manifest.unlink(missing_ok=True)

    size_mb = snapshot_path.stat().st_size / 1024 / 1024
    log(f"快照已生成: {snapshot_path.name} ({size_mb:.1f} MB)", "✅")
    log(f"包含 {manifest['doc_count']} 个文档", "  ")
    return snapshot_path


# ============ 发布 ============

def publish_snapshot(snapshot_path: Path, tag: str | None = None):
    """发布快照到 GitHub Release"""
    repo = get_repo()
    log(f"目标仓库: {repo}", "🎯")

    if tag is None:
        tag = "data-" + datetime.now().strftime("%Y%m%d")

    log(f"创建 Release: {tag}", "🚀")
    manifest_note = (
        f"数据快照 · {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"包含 SQLite 元数据 + ChromaDB 向量库，下载后解压到 `backend/` 即可使用。\n\n"
        f"导入命令: `python scripts/snapshot.py import`"
    )

    # 已存在的 tag 需要处理
    result = subprocess.run(
        ["gh", "release", "view", tag],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode == 0:
        log(f"Release {tag} 已存在，改为上传到该 Release", "⚠️")
        run_gh(["release", "upload", tag, str(snapshot_path), "--clobber"])
    else:
        run_gh([
            "release", "create", tag, str(snapshot_path),
            "--title", f"数据快照 {datetime.now().strftime('%Y-%m-%d')}",
            "--notes", manifest_note,
        ])

    log(f"发布成功: https://github.com/{repo}/releases/tag/{tag}", "✅")


# ============ 导入 ============

def list_snapshots():
    """列出所有已发布的数据快照"""
    log("查询可用快照...", "🔍")
    result = run_gh(
        ["release", "list", "--limit", "20", "--json", "tagName,publishedAt,name,isLatest",
         "-q", '.[] | select(.tagName | startswith("data-")) | "\\(.tagName)  \\(.publishedAt)  \\(.name)"'],
        capture=True,
    )
    out = result.stdout.strip()
    if not out:
        log("暂无已发布的数据快照", "  ")
    else:
        print()
        for line in out.splitlines():
            log(line, "  ")


def download_snapshot(tag: str | None = None, force: bool = False):
    """从 GitHub Release 下载并恢复快照"""
    if tag is None:
        # 找最新的 data-* release
        result = run_gh(
            ["release", "list", "--limit", "50", "--json", "tagName",
             "-q", '[.[] | select(.tagName | startswith("data-"))][0].tagName'],
            capture=True,
        )
        tag = result.stdout.strip()
        if not tag:
            log("未找到任何数据快照，请先在有数据的机器上运行 publish", "❌")
            sys.exit(1)

    log(f"下载快照: {tag}", "⬇️")

    with tempfile.TemporaryDirectory() as tmpdir:
        run_gh(["release", "download", tag, "--pattern", "*.tar.gz", "--dir", tmpdir])

        archives = list(Path(tmpdir).glob("*.tar.gz"))
        if not archives:
            log("Release 中未找到快照文件", "❌")
            sys.exit(1)
        archive = archives[0]

        # 覆盖检查
        if (DB_FILE.exists() or CHROMA_DIR.exists()) and not force:
            log("本地已有数据，导入会覆盖！", "⚠️")
            answer = input("  确认覆盖？(y/N): ").strip().lower()
            if answer != "y":
                log("已取消", "  ")
                return

        # 备份旧数据
        if DB_FILE.exists() or CHROMA_DIR.exists():
            backup_dir = ROOT / "snapshots" / f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            if DB_FILE.exists():
                shutil.copy2(DB_FILE, backup_dir / "school_rag.db")
            if CHROMA_DIR.exists():
                shutil.copytree(CHROMA_DIR, backup_dir / "chroma_data")
            log(f"旧数据已备份到 {backup_dir.relative_to(ROOT)}", "  ")

        # 解压恢复
        log("正在解压...", "  ")
        with tarfile.open(archive, "r:gz") as tar:
            # 安全检查：防止路径穿越
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    log(f"快照包含非法路径: {member.name}", "❌")
                    sys.exit(1)
            tar.extractall(BACKEND)

    # 读取元信息
    manifest_path = BACKEND / MANIFEST_NAME
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        log(f"快照时间: {manifest.get('exported_at', '?')}", "  ")
        log(f"文档数:   {manifest.get('doc_count', '?')}", "  ")
        manifest_path.unlink()  # 清理，不属于运行数据

    log(f"导入完成！数据已恢复到 backend/", "✅")
    log("现在可以直接启动服务，无需重新爬取", "  ")


# ============ 状态 ============

def show_info():
    """显示当前数据状态"""
    log("当前数据状态:", "📊")
    print()
    if DB_FILE.exists():
        size_mb = DB_FILE.stat().st_size / 1024 / 1024
        log(f"数据库:   {DB_FILE.relative_to(ROOT)}  ({size_mb:.1f} MB)", "  ")
        log(f"文档数:   {get_doc_count()}", "  ")
    else:
        log("数据库:   未找到", "  ")

    if CHROMA_DIR.exists():
        total = sum(f.stat().st_size for f in CHROMA_DIR.rglob("*") if f.is_file())
        size_mb = total / 1024 / 1024
        log(f"向量库:   {CHROMA_DIR.relative_to(ROOT)}  ({size_mb:.1f} MB)", "  ")
    else:
        log("向量库:   未找到", "  ")

    log(f"后端服务: {'运行中' if is_backend_running() else '已停止'}", "  ")

    # 本地快照文件
    local = sorted(SNAPSHOT_DIR.glob("*.tar.gz")) if SNAPSHOT_DIR.exists() else []
    if local:
        print()
        log("本地快照文件:", "  ")
        for f in local:
            log(f"{f.name}  ({f.stat().st_size / 1024 / 1024:.1f} MB)", "    ")


# ============ CLI ============

def main():
    parser = argparse.ArgumentParser(
        description="RAG 数据快照工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="导出快照到 snapshots/")
    p_export.add_argument("--force", action="store_true", help="后端运行时也强制导出")

    p_publish = sub.add_parser("publish", help="导出并发布到 GitHub Release")
    p_publish.add_argument("--tag", help="指定 release tag（默认 data-YYYYMMDD）")
    p_publish.add_argument("--force", action="store_true", help="后端运行时也强制导出")

    p_import = sub.add_parser("import", help="下载并恢复快照")
    p_import.add_argument("--tag", help="指定 release tag（默认最新）")
    p_import.add_argument("--force", action="store_true", help="覆盖本地数据不询问")

    sub.add_parser("list", help="列出所有已发布快照")
    sub.add_parser("info", help="查看当前数据状态")

    args = parser.parse_args()

    if args.command == "export":
        export_snapshot(skip_running_check=args.force)

    elif args.command == "publish":
        path = export_snapshot(skip_running_check=args.force)
        publish_snapshot(path, args.tag)

    elif args.command == "import":
        download_snapshot(args.tag, args.force)

    elif args.command == "list":
        list_snapshots()

    elif args.command == "info":
        show_info()


if __name__ == "__main__":
    main()
