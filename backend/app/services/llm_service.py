"""LLM service — DeepSeek API client with streaming support."""

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings

_client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

SYSTEM_PROMPT = """你是一个学校政策文件的智能查询助手。你只能根据提供的文档片段回答问题。

## 规则
1. 只根据下方"参考文档"的内容回答，不要使用你的先验知识
2. 如果文档中没有相关信息，请明确说："抱歉，当前文档库中没有找到相关信息。"
3. 回答中必须标注引用来源，格式：[来源: 文件名]
4. 回答要准确、简洁、有条理
5. 如果引用了多个来源，请逐一标注
6. 用中文回答
"""


def build_prompt(question: str, context_chunks: list[dict]) -> tuple[str, str]:
    """
    Build system and user prompts for the LLM.

    Args:
        question: The user's question.
        context_chunks: List of retrieved chunks with 'title' and 'text'.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    # Format context chunks with source labels
    context_parts = []
    for i, chunk in enumerate(context_chunks):
        source_label = f"[来源{i+1}: {chunk.get('title', '未知文件')}]"
        context_parts.append(f"### {source_label}\n{chunk['text']}")

    context_text = "\n\n".join(context_parts)

    user_prompt = f"""## 参考文档

{context_text}

## 用户问题

{question}

请根据以上参考文档回答，并标注引用来源。"""

    return SYSTEM_PROMPT, user_prompt


async def chat_stream(
    question: str,
    context_chunks: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Stream the LLM response token by token.

    Args:
        question: User's question.
        context_chunks: Retrieved context chunks.

    Yields:
        Token strings (may be empty for some chunk types).
    """
    system_prompt, user_prompt = build_prompt(question, context_chunks)

    try:
        response = await _client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.llm_temperature,
            stream=True,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"\n\n[错误: {str(e)}]"
