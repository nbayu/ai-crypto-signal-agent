import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def format_watchlist(results):

    lines = []

    for r in results[:5]:
        lines.append(
            f"{r['symbol']} | "
            f"Score {r['score']} | "
            f"{r['trend']} | "
            f"Q{r['quality']} | "
            f"BOS:{r['bos']} | "
            f"CHOCH:{r['choch']} | "
            f"FVG:{r['fvg']} | "
            f"OB:{r['order_blocks']} | "
            f"LQ:{r['liquidity']}"
        )

    prompt = (
        "Ringkas watchlist berikut untuk Telegram.\n"
        "Jangan menghitung ulang indikator.\n"
        "Jangan mengubah skor.\n"
        "Jangan menjelaskan teori.\n"
        "Gunakan maksimal 120 kata.\n\n"
        + "\n".join(lines)
    )

    response = client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=180,
        temperature=0.2
    )

    return response.choices[0].message.content
