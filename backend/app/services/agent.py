"""
Agent Loop — ReAct-style multi-step reasoning for complex queries.

When a simple RAG search isn't enough (comparisons, multi-hop questions),
the agent can: search → read results → decide to search more → synthesize answer.

Uses DeepSeek function calling (OpenAI-compatible format).
"""

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.embedder import embedder
from app.services.vector_store import vector_store, SearchResult

_client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

# ============ Tool Definitions ============

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "搜索学校文件库。当你需要查找某个政策、规定、办法的具体内容时调用此工具。输入自然语言查询，返回最相关的文件片段。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，用中文自然语言描述你要找的内容",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_detail",
            "description": "获取某个具体文件的完整内容。当你发现某个搜索结果很重要，需要阅读全文时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "integer",
                        "description": "文件的唯一ID",
                    }
                },
                "required": ["file_id"],
            },
        },
    },
]

AGENT_SYSTEM_PROMPT = """你是一个学校政策文件的智能查询助手。你可以使用以下工具来查找信息：

## 工具
- search_documents(query): 在文件库中搜索相关内容
- get_file_detail(file_id): 获取某个文件的完整内容

## 工作流程
1. 分析用户问题，确定需要查找哪些信息
2. 如果问题涉及多个方面（如对比两个政策），分别搜索每个方面
3. 如果搜索结果不够详细，获取完整文件内容
4. 基于找到的所有文档片段，给出准确答案

## 规则
- 只基于搜索到的文档内容回答，不要编造
- 如果文档中找不到相关信息，明确告知用户
- 回答中标注引用来源，格式：[来源: 文件名]
- 用中文回答
- 对比类问题要清晰列出异同点
"""


@dataclass
class CollectedSource:
    file_id: int
    title: str
    department: str
    date: str
    snippet: str


async def agent_query(question: str) -> AsyncGenerator[str, None]:
    """
    Agent-based query: LLM decides which tools to use, iteratively collects
    information, then synthesizes a final answer.

    Yields token strings, same interface as query_engine.query().
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    collected_sources: dict[int, CollectedSource] = {}
    max_turns = 8

    for turn in range(max_turns):
        response = await _client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=settings.llm_temperature,
        )

        choice = response.choices[0]
        msg = choice.message

        # If the model wants to call tools
        if msg.tool_calls:
            # Record the assistant's tool call request
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each tool call
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)

                if tool_name == "search_documents":
                    result_text = _execute_search(tool_args["query"], collected_sources)
                elif tool_name == "get_file_detail":
                    result_text = _execute_get_detail(tool_args["file_id"], collected_sources)
                else:
                    result_text = f"未知工具: {tool_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

        else:
            # Model is done — stream the final answer
            # But first, yield collected sources info
            sources_list = [
                {
                    "file_id": s.file_id,
                    "title": s.title,
                    "department": s.department,
                    "date": s.date,
                    "snippet": s.snippet,
                }
                for s in collected_sources.values()
            ]
            yield f"__SOURCES__:{json.dumps(sources_list, ensure_ascii=False)}"

            # Now stream the final answer via a second call.
            # tool_choice="none" forces pure text — prevents the model from
            # re-emitting tool-call markup inside the answer.
            stream = await _client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=settings.llm_temperature,
                tool_choice="none",
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            return

    # Max turns exceeded — force final answer
    yield "__SOURCES__:[]"
    yield "抱歉，在查找信息时遇到了困难。请尝试更具体的提问方式。"


def _execute_search(query: str, collected: dict[int, CollectedSource]) -> str:
    """Execute a document search and return formatted results."""
    q_vec = embedder.embed_query(query)
    results = vector_store.search(q_vec, top_k=5)

    if not results:
        return "未找到相关文档。"

    parts = []
    for r in results:
        if r.file_id and r.file_id not in collected:
            collected[r.file_id] = CollectedSource(
                file_id=r.file_id,
                title=r.title,
                department=r.department,
                date=r.date,
                snippet=r.text[:300],
            )
        parts.append(f"--- [file_id={r.file_id}] {r.title} ({r.date}) ---\n{r.text[:1000]}")

    return "\n\n".join(parts)


def _execute_get_detail(file_id: int, collected: dict[int, CollectedSource]) -> str:
    """Get full text of a specific file from vector store chunks."""
    # Search by file_id filter via vector store
    q_vec = embedder.embed_query("")  # dummy embedding
    all_results = vector_store.search(q_vec, top_k=50)

    file_chunks = [r for r in all_results if r.file_id == file_id]
    if not file_chunks:
        return f"未找到 file_id={file_id} 的内容。"

    file_chunks.sort(key=lambda r: r.chunk_index)
    full_text = "\n\n".join(r.text for r in file_chunks)

    # Track source
    if file_id not in collected and file_chunks:
        r = file_chunks[0]
        collected[file_id] = CollectedSource(
            file_id=r.file_id,
            title=r.title,
            department=r.department,
            date=r.date,
            snippet=r.text[:300],
        )

    return f"=== {file_chunks[0].title} 全文 ===\n{full_text[:4000]}"


def is_complex_query(question: str) -> bool:
    """
    Heuristic to decide if a question needs agent mode.

    Complex indicators: comparison words, multi-aspect questions.
    Simple: direct factual lookup.
    """
    complex_keywords = [
        "对比", "比较", "区别", "哪个更", "有什么不同", "有什么差别",
        "分别", "各自", "同时", "除了.*还要", "以及",
        "还有哪些", "其他", "和.*比", "有哪些不同",
        "更高", "更好", "更强", "更严格", "更容易",
        "两者", "两个", "两者之间", "二选一", "选哪个",
        "A.*B.*哪个", "和.*哪个",
    ]

    import re
    for kw in complex_keywords:
        if re.search(kw, question):
            return True

    # Also check if question contains multiple question marks or long length
    if question.count("？") + question.count("?") >= 2:
        return True

    if len(question) > 80:
        return True

    return False
