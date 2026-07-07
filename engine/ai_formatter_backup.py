import json
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="ISI_API_KEY_OPENROUTER"
)

def format_watchlist(results):

    top = results[:5]

    data = []

    for r in top:
        data.append({
            "symbol": r["symbol"],
            "score": r["score"],
            "trend": r["trend"],
            "quality": r["quality"],
            "bos": r["bos"],
            "choch": r["choch"],
            "fvg": r["fvg"],
            "orderblock": r["order_blocks"],
            "liquidity": r["liquidity"]
        })

    prompt = f"""
Kamu adalah formatter Telegram.

Data JSON:

{json.dumps(data)}

Tugas:
- Jangan menghitung ulang.
- Jangan mengubah score.
- Jangan menjelaskan teori.
- Maksimal 180 kata.
- Output format Telegram.
"""

    response = client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {"role":"user","content":prompt}
        ],
        max_tokens=250
    )

    return response.choices[0].message.content
