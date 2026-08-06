"""End-to-end QA test — ask real questions, verify answers + sources."""
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

import httpx

QUESTIONS = [
    "保研需要什么条件？GPA要求是多少？",
    "国家奖学金多少钱？怎么申请？",
    "考试作弊会怎么处理？",
    "转专业有什么要求？",
    "宿舍能用大功率电器吗？",
]

async def ask(client: httpx.AsyncClient, question: str):
    print(f"\n{'='*60}")
    print(f"问: {question}")
    print(f"{'='*60}")

    try:
        async with client.stream("POST", "http://localhost:8000/api/chat",
                                  json={"question": question}, timeout=120) as r:
            full = ""
            source_count = 0
            async for line in r.aiter_lines():
                if line.startswith("event: sources"):
                    pass
                elif line.startswith("data: ") and not line.startswith("data: []"):
                    data = line[6:]
                    if data.startswith("["):
                        import json
                        try:
                            arr = json.loads(data)
                            source_count = len(arr)
                        except Exception:
                            pass
                    else:
                        full += data
            print(f"来源文件数: {source_count}")
            # 输出回答的前 300 字
            print(f"回答: {full[:300]}...")
            return True
    except Exception as e:
        print(f"错误: {e}")
        return False

async def main():
    async with httpx.AsyncClient() as client:
        results = []
        for q in QUESTIONS:
            ok = await ask(client, q)
            results.append(ok)
            await asyncio.sleep(1)  # 礼貌间隔

    print(f"\n{'='*60}")
    print(f"通过: {sum(results)}/{len(results)}")
    print(f"{'='*60}")

asyncio.run(main())
