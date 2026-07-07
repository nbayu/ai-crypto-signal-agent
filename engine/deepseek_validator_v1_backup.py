import os
import json
from openai import OpenAI

MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """
You are a validation gate for a crypto market scanner.

Your authority is strictly limited.

You MUST:
- evaluate only the numerical and structural data provided
- compare candidates against each other
- detect contradictions and weak confirmations
- identify false-breakout risk
- rank the strongest candidates

You MUST NOT:
- recalculate indicators
- invent missing data
- change Python scores
- give BUY or SELL signals
- determine entry, stop loss, or take profit
- use outside market knowledge

Python is the source of truth.

Return valid JSON only.
"""

def validate_candidates(candidates):
    if not candidates:
        return []

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )

    payload = {
        "task": "Validate these candidates and select the best 5.",
        "rules": {
            "max_selected": 5,
            "preserve_python_score": True,
            "no_trading_signal": True
        },
        "candidates": candidates
    }

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": json.dumps(
                    payload,
                    separators=(",", ":"),
                    default=str
                )
            }
        ],
        temperature=0.1,
        max_tokens=1200
    )

    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cache_hit_tokens": getattr(
                response.usage,
                "prompt_cache_hit_tokens",
                0
            ),
            "cache_miss_tokens": getattr(
                response.usage,
                "prompt_cache_miss_tokens",
                0
            )
        }
    }
