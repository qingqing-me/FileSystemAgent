"""
Fix data consistency — mark documents that are 'indexed' in SQLite but
missing from the vector store as 'pending' so re-ingestion rebuilds them.

Run: python scripts/fix_consistency.py
"""
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

import os
os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
sys.path.insert(0, ".")

from sqlalchemy import select
from app.db.session import async_session
from app.models.database import DocumentSource, SourceStatus
from app.services.vector_store import vector_store


async def main():
    # Get all file_ids present in the vector store
    coll = vector_store._collection
    got = coll.get(limit=100000)
    vec_file_ids = set()
    for m in got["metadatas"]:
        if m and m.get("file_id"):
            vec_file_ids.add(m["file_id"])

    print(f"向量库中有 {len(vec_file_ids)} 个不同文件")

    async with async_session() as db:
        r = await db.execute(
            select(DocumentSource).where(DocumentSource.status == SourceStatus.indexed)
        )
        indexed = r.scalars().all()
        print(f"SQLite indexed: {len(indexed)}")

        missing = [s for s in indexed if s.file_id not in vec_file_ids]
        ok = [s for s in indexed if s.file_id in vec_file_ids]
        print(f"向量存在:   {len(ok)}")
        print(f"向量缺失:   {len(missing)}")

        if not missing:
            print("\n✅ 数据一致，无需修复")
            return

        # Mark missing as pending so re-ingestion rebuilds them
        for s in missing:
            s.status = SourceStatus.pending
        await db.commit()

        print(f"\n已将 {len(missing)} 个缺失向量的文件标记为 pending")
        print("下一步: 重新运行 ingest 脚本会重建这些文件的向量")
        print()
        print("核心缺失文件样本:")
        for s in missing[:20]:
            print(f"  [{s.file_id}] {s.title[:60]}")


if __name__ == "__main__":
    asyncio.run(main())
