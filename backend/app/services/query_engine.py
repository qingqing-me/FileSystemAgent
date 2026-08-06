"""Query engine — routes simple queries to Workflow, complex queries to Agent."""

from collections.abc import AsyncGenerator

from app.services.embedder import embedder
from app.services.vector_store import vector_store, SearchResult
from app.services.llm_service import chat_stream
from app.services.agent import agent_query, is_complex_query


# ============ 同义词扩展 ============
# 用户用口语提问，但学校文件用官方术语。检索前把常见口语词映射成
# 多个检索变体，分别搜索后合并结果，弥补 embedding 的术语鸿沟。
SYNONYM_EXPANSIONS: dict[str, list[str]] = {
    "保研": ["推免", "免试攻读", "推荐免试"],
    "绩点": ["加权平均成绩", "成绩排名", "平均分"],
    "GPA": ["加权平均成绩", "成绩排名", "学业成绩"],
    "奖学金": ["奖学金", "奖助学金", "国家奖学金"],
    "挂科": ["不及格", "补考", "课程考核"],
    "重修": ["补考", "课程考核"],
    "处分": ["违纪处理", "违纪处分", "处分规定"],
    "作弊": ["考试违规", "违纪", "考试作弊"],
    "转专业": ["转专业", "专业调整"],
    "勤工俭学": ["勤工助学", "助学"],
    "助学金": ["助学金", "资助"],
    "学费": ["学费", "收费"],
    "毕业证": ["毕业证书", "学位证书", "毕业"],
    "双学位": ["辅修", "辅修学士学位"],
    "出国": ["国（境）外交流", "国际合作交流", "出国留学"],
    "保研率": ["推免名额", "推免工作"],
}


def _chunks_to_dicts(results: list[SearchResult]) -> list[dict]:
    return [
        {
            "text": r.text,
            "title": r.title,
            "department": r.department,
            "date": r.date,
            "file_id": r.file_id,
        }
        for r in results
    ]


def expand_query(question: str) -> list[str]:
    """Generate query variants by replacing colloquial terms with official ones."""
    variants = [question]
    for word, replacements in SYNONYM_EXPANSIONS.items():
        if word in question:
            for repl in replacements:
                variant = question.replace(word, repl)
                if variant not in variants:
                    variants.append(variant)
    return variants


def _multi_search(question: str, top_k: int) -> list[SearchResult]:
    """Search with query expansion, merge results deduplicated by file_id,
    keeping the highest-scoring chunk per file."""
    variants = expand_query(question)

    best_by_file: dict[int, SearchResult] = {}
    for variant in variants:
        q_vec = embedder.embed_query(variant)
        results = vector_store.search(q_vec, top_k=top_k * 6)
        for r in results:
            if r.file_id == 0:
                continue
            if r.file_id not in best_by_file or r.score > best_by_file[r.file_id].score:
                best_by_file[r.file_id] = r

    # Sort by score, take top_k distinct files
    merged = sorted(best_by_file.values(), key=lambda r: r.score, reverse=True)
    return merged[:top_k]


async def query(question: str, top_k: int = 5, force_mode: str | None = None) -> AsyncGenerator[str, None]:
    """
    Smart query: routes to Workflow or Agent based on question complexity.

    Args:
        question: User's natural language question.
        top_k: Number of chunks for workflow mode.
        force_mode: 'workflow', 'agent', or None (auto-detect).
    """
    if force_mode == "agent" or (force_mode is None and is_complex_query(question)):
        async for token in agent_query(question):
            yield token
    else:
        async for token in _workflow_query(question, top_k):
            yield token


async def _workflow_query(question: str, top_k: int) -> AsyncGenerator[str, None]:
    """Simple RAG with query expansion: multi-search → merge → LLM."""
    results = _multi_search(question, top_k)

    if not results:
        yield "抱歉，当前文档库中没有找到相关信息。"
        return

    context_chunks = _chunks_to_dicts(results)
    async for token in chat_stream(question, context_chunks):
        yield token


def get_sources(question: str, top_k: int = 5) -> list[SearchResult]:
    """Retrieve source chunks (for the SSE sources event)."""
    return _multi_search(question, top_k)
