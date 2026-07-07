import os
import json
from openai import OpenAI

MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """
You are a strictly bounded validation gate for a crypto market scanner.

Python is the source of truth.

YOUR ONLY JOB:
Evaluate every candidate provided using only its supplied data.

YOU MAY:
- detect conflicts between structure and confirmation data
- assess false-breakout risk
- assess confluence quality
- flag weak participation or overextension when supported by data

YOU MUST NOT:
- select candidates
- remove candidates
- rank candidates
- change or recalculate Python scores
- invent missing data
- use outside market knowledge
- give BUY or SELL signals
- determine entry, stop loss, or take profit

Evaluate EVERY candidate exactly once.
Use each symbol exactly as provided.

Allowed values:

status:
- CLEAR
- CONFLICT
- HIGH_RISK

false_breakout_risk:
- LOW
- MEDIUM
- HIGH

confluence:
- STRONG
- MODERATE
- WEAK

reason_code:
- ALIGNED
- STRUCTURE_REVERSAL_CONFLICT
- WEAK_VOLUME
- WEAK_OI
- WEAK_PARTICIPATION
- BREAKOUT_UNCONFIRMED
- OVEREXTENDED
- MULTIPLE_CONFLICTS

Return valid JSON only.

Required schema:
{
  "validations": [
    {
      "symbol": "SYMBOL",
      "status": "CLEAR|CONFLICT|HIGH_RISK",
      "false_breakout_risk": "LOW|MEDIUM|HIGH",
      "confluence": "STRONG|MODERATE|WEAK",
      "reason_code": "ALLOWED_CODE"
    }
  ]
}

No explanations.
No markdown.
No extra keys.
"""

def validate_candidates(candidates):
    if not candidates:
        return {
            "content": '{"validations":[]}',
            "usage": {}
        }

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )

    payload = {
        "task": "Validate every candidate exactly once.",
        "candidate_count": len(candidates),
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
        temperature=0.0,
        max_tokens=700,
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}}
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
