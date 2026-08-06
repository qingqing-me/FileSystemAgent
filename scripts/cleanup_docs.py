"""
Clean up ingested documents:
1. Remove temporary/transient notifications (停电、施工、具体名单、通报...)
2. For policies with multiple versions, keep only the LATEST one

Run: python scripts/cleanup_docs.py
"""
import asyncio
import re
from collections import defaultdict

import httpx
from sqlalchemy import select

import os, sys
# Switch to backend directory so SQLite path resolves correctly
os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
sys.path.insert(0, ".")

from app.db.session import async_session
from app.models.database import DocumentSource, SourceStatus
from app.services.vector_store import vector_store

BACKEND = "http://localhost:8000"

# ============ RULES ============

# Title patterns that indicate TEMPORARY/TRANSIENT docs → DISCARD
DISCARD_PATTERNS = [
    # 基建后勤临时通知
    r"停电", r"停水", r"施工", r"消杀", r"病虫害", r"道路封闭",
    r"临时(占用|管控|封闭)", r"倒闸", r"错峰用电", r"限制使用",
    r"短时停电", r"停气", r"交通管制", r"占道", r"封闭道路",
    r"封闭.*道路", r"路灯运行", r"空调(清洗|消毒|限)", r"物业费",
    r"封闭.*(路段|车道|道路)", r"临时封闭",

    # 特定考试的准考证/报名（一次性考务）
    r"(四、六级|四六级)考试.*(准考证|报名|听力|测试)",
    r"英语四、六级.*(准考证|报名)",

    # 征文、作品征集
    r"征文",
    r"关于征集.*作品",
    r"关于.*作品征集",

    # 具体选拔运动员
    r"关于选拔.*运动员",

    # 针对具体人的行政决定（非政策）
    r"关于准予.*(退学|毕业|结业|自动退学)的决定",
    r"关于授予.*(学士|硕士|博士)学位的决定",
    r"关于给予.*退学处理的决定",
    r"关于给予.*(记过|严重警告|警告|留校察看|开除学籍)处分的决定",
    r"关于解除.*(记过|严重警告|警告|留校察看|开除学籍)处分的决定",
    r"关于给予.*(记过|严重警告|警告|留校察看|开除学籍)的处分",
    r"关于解除.*处分的决定",
    r"关于撤销.*处分的决定",
    r"关于同意办理.*(复学|休学|保留学籍)的决定",
    r"关于同意办理.*的决定",
    r"关于表彰.*的决定",
    r"关于聘任.*的通知",
    r"关于.*换届任职",
    r"关于公布.*名单",
    r"关于公布.*获奖名单",
    r"关于.*评选结果的公示",
    r"关于.*推荐名单",
    r"关于.*拟推荐",
    r"关于.*名单的公示",

    # 宿舍日常通报
    r"学生宿舍未按时熄灯",
    r"学生宿舍安全.*抽检",
    r"宿舍.*情况通报",

    # 转发（非本校制定政策）
    r"转发.*的通知$",

    # 临时活动、短期比赛
    r"关于举办.*大赛",
    r"关于举办.*比赛",
    r"关于举行.*比赛",
    r"关于举办.*活动",
    r"关于组织参加.*大赛",
    r"关于组织参加.*竞赛",
    r"关于组织.*参赛",

    # 党建通讯、简报
    r"党建通讯",
    r"简报",

    # 节假日调课安排
    r"关于调整.*放假.*教学安排",
    r"关于.*元旦.*放假",
    r"关于.*劳动节.*放假",

    # 短期培训、讲座
    r"关于举办.*讲座",
    r"关于举办.*培训",
    r"关于举办.*报告会",
    r"关于举办.*训练营",

    # 具体学期的课程相关
    r"关于.*学期.*考试安排",  # 特定学期的考务
    r"关于.*学期.*晚自习",

    # 用能巡查、用电通报
    r"用能(巡查|抽查)",
    r"用电情况",

    # 公示认领废弃车
    r"废弃车",

    # 烟花爆竹
    r"烟花爆竹",

    # 具体项目的立项/结题名单
    r"关于公布.*项目.*名单",
    r"关于公布.*立项",

    # 学生组织具体人事
    r"关于同意共青团.*选举结果",
    r"关于.*团委.*更名",

    # 运动会具体赛事
    r"关于举行.*校运会",
    r"关于举行.*篮球赛",
    r"关于举行.*气排球",
    r"关于举行.*足球",
    r"关于举行.*网球",
    r"关于举行.*羽毛球",
    r"关于举行.*跳绳",

    # 临时征集作品
    r"关于征集.*作品",
    r"关于.*作品征集",

    # 毕业生离校具体安排
    r"关于.*毕业生.*办理",
    r"关于.*毕业.*离校",

    # 军训、征兵
    r"关于.*征兵",

    # 新生入学教育（特定年份）
    r"新生.*入馆教育",

    # 团支部评优具体名单
    r"关于表彰.*共青团",
    r"关于表彰.*团员",
    r"关于表彰.*志愿",

    # 学生资助具体名单公示
    r"(奖学金|助学金|资助).*评选结果公示",
    r"(奖学金|助学金|资助).*推荐名单公示",
    r"关于颁发.*奖学金的决定$",     # 具体颁发决定
    r"关于颁发.*助学金的决定$",
    r"关于颁发.*基金的决定$",
]

# Keep patterns — policies, regulations, long-term documents
KEEP_PATTERNS = [
    r"实施办法",
    r"管理办法",
    r"管理规定",
    r"工作办法",
    r"条例",
    r"制度",
    r"规定$",
    r"办法$",
    r"细则",
    r"指导意见",
    r"实施方案",
    r"实施办法",
    r"评审办法",
    r"评定办法",
    r".*奖学金.*评审",
    r".*助学金.*评审",
    r"推荐.*免试.*研究生",
    r"推免",
    r"保研",
    r"培养方案",
    r"教学计划",
    r"校历",
    r"学籍.*规定",
    r"学位.*办法",
    r"导师制",
    r"毕业论文.*规定",
    r"创新创业.*学分",
    r"交流生.*办法",
    r"本研一体化",
    r"学生资助政策",
    r"国家奖助学金.*评审管理",
    r"学生奖励办法",
    r"学生处分规定",
    r"转专业.*办法",
    r"转专业.*通知$",
    r"专业分流.*通知",
    r"辅修.*办法",
    r"微专业",
    r"免试认定",
]


def should_keep(title: str) -> tuple[bool, str]:
    """Classify a document. Returns (keep, reason)."""
    # First check KEEP patterns (explicit policy documents)
    for pat in KEEP_PATTERNS:
        if re.search(pat, title):
            return True, f"KEEP: matched '{pat}'"

    # Then check DISCARD patterns
    for pat in DISCARD_PATTERNS:
        if re.search(pat, title):
            return False, f"DISCARD: matched '{pat}'"

    # Default: keep if unsure (conservative)
    return True, "KEEP: default (no match)"


def extract_policy_base_name(title: str) -> str:
    """Extract base policy name for dedup, stripping version markers and prefixes."""
    # Remove common prefixes
    base = title
    for prefix in ["关于印发《", "关于印发", "关于", "《"]:
        if base.startswith(prefix):
            base = base[len(prefix):]
    # Remove common suffixes
    for suffix in ["》的通知", "》", "的通知", "通知"]:
        if base.endswith(suffix):
            base = base[:-len(suffix)]

    # Remove version markers for grouping
    base = re.sub(r"[（(]\d{4}年\d{0,2}月修订[）)]", "", base)
    base = re.sub(r"[（(]\d{4}年修订[）)]", "", base)
    base = re.sub(r"[（(]修订征求意见稿[）)]", "", base)
    base = re.sub(r"[（(]征求意见稿[）)]", "", base)
    base = re.sub(r"[（(]试行[）)]", "", base)

    return base.strip()


def normalize_date(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD for comparison."""
    if not date_str:
        return "0000-00-00"
    # Handle various date formats
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
    return "0000-00-00"


async def cleanup():
    print("=" * 60)
    print("Document Cleanup — Remove transient + Dedup policies")
    print("=" * 60)

    keep_docs = []
    discard_docs = []

    async with async_session() as db:
        result = await db.execute(
            select(DocumentSource).order_by(DocumentSource.date.desc())
        )
        sources = result.scalars().all()

        print(f"\nTotal sources in DB: {len(sources)}")

        # First pass: classify
        for s in sources:
            keep, reason = should_keep(s.title)
            if keep:
                keep_docs.append(s)
            else:
                discard_docs.append(s)

        print(f"  KEEP:   {len(keep_docs)}")
        print(f"  DISCARD: {len(discard_docs)}")

        # Second pass: dedup policies within keep_docs
        # Group by base name, keep only latest version
        policy_groups: dict[str, list] = defaultdict(list)
        standalone_docs = []

        for s in keep_docs:
            base_name = extract_policy_base_name(s.title)
            # Only dedup if there are 2+ docs with same base name
            policy_groups[base_name].append(s)

        final_keep = []
        duplicates_removed = []

        for base_name, docs in policy_groups.items():
            if len(docs) > 1:
                # Keep the one with latest date
                docs.sort(key=lambda d: normalize_date(d.date), reverse=True)
                final_keep.append(docs[0])
                duplicates_removed.extend(docs[1:])
            else:
                final_keep.append(docs[0])

        print(f"\nDedup policy versions:")
        print(f"  Final keep:       {len(final_keep)}")
        print(f"  Duplicates removed: {len(duplicates_removed)}")

        # ============ DRY RUN REPORT ============
        print("\n" + "=" * 60)
        print("DISCARD SAMPLES (first 30):")
        print("=" * 60)
        for s in discard_docs[:30]:
            print(f"  [{s.date}] {s.title[:80]}")
            print(f"    → {s.department}")

        print(f"\n  ... and {max(0, len(discard_docs) - 30)} more discards")

        if duplicates_removed:
            print("\n" + "=" * 60)
            print("DUPLICATE POLICIES REMOVED:")
            print("=" * 60)
            for s in duplicates_removed[:20]:
                print(f"  [{s.date}] {s.title[:80]}")

        # ============ CONFIRM ============
        total_to_delete = len(discard_docs) + len(duplicates_removed)
        total_kept = len(final_keep)

        print(f"\n{'=' * 60}")
        print(f"SUMMARY:")
        print(f"  Original:    {len(sources)}")
        print(f"  To DELETE:   {total_to_delete} ({len(discard_docs)} transient + {len(duplicates_removed)} dup)")
        print(f"  To KEEP:     {total_kept}")
        print(f"{'=' * 60}")

        response = input("\nProceed with deletion? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. No changes made.")
            return

        # ============ EXECUTE ============
        all_to_delete = discard_docs + duplicates_removed
        print(f"\nDeleting {len(all_to_delete)} documents...")

        deleted_count = 0
        for s in all_to_delete:
            # Remove from vector store
            try:
                vector_store.delete_by_file_id(s.file_id)
            except Exception as e:
                print(f"  WARN: vector delete failed for {s.file_id}: {e}")

            # Remove from DB
            await db.delete(s)
            deleted_count += 1

            if deleted_count % 50 == 0:
                await db.commit()
                print(f"  ... {deleted_count}/{len(all_to_delete)}")

        await db.commit()

        # Final count
        result = await db.execute(select(DocumentSource))
        remaining = len(result.scalars().all())
        print(f"\nDone! {remaining} documents remaining in DB.")
        print(f"Vector store chunks: {vector_store.count()}")


if __name__ == "__main__":
    asyncio.run(cleanup())
