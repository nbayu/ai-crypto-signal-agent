import os
import json
from openai import OpenAI

MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """
You are a strictly bounded validation gate for a crypto market scanner.

Python is the source of truth.

YOUR ONLY JOB:
Evaluate every candidate provided using only its supplied data.

SEMANTIC CONTRACT — THESE DEFINITIONS ARE AUTHORITATIVE:

- trend=UPTREND means bullish market structure.
- trend=DOWNTREND means bearish market structure.
- UPTREND and DOWNTREND are both valid structures. Trend direction alone is NEVER a risk or conflict.

- bos=True means a structure breakout is confirmed.
- bos=False means breakout confirmation is absent.
- BOS must be interpreted in the context of the existing trend direction.

- choch=True means evidence of a possible structure reversal.
- choch=True is ALWAYS a structural conflict.
- A candidate with choch=True MUST NOT receive status=CLEAR.
- A candidate with choch=True MUST NOT receive reason_code=ALIGNED.

- volume_spike is a 0-100 confirmation score.
- volume_spike >= 80 means strong volume confirmation.
- volume_spike 60-79 means moderate volume confirmation.
- volume_spike < 60 means weak volume confirmation.

- oi_growth is a 0-100 participation score.
- oi_growth >= 80 means strong open-interest expansion.
- oi_growth 21-79 means neutral or moderate participation.
- oi_growth <= 20 means weak open-interest support.

- Weak volume together with weak OI means WEAK_PARTICIPATION and materially increases false-breakout risk.

- bos=False with otherwise positive evidence means breakout confirmation is absent. Do not invent a breakout.

VALIDATION PRECEDENCE:

1. If choch=True:
   status must be CONFLICT or HIGH_RISK.
   reason_code must not be ALIGNED.

2. If volume_spike < 60 AND oi_growth <= 20:
   status must be HIGH_RISK.
   false_breakout_risk must be HIGH.
   confluence must be WEAK.
   reason_code must be WEAK_PARTICIPATION or MULTIPLE_CONFLICTS.

3. If bos=False:
   false_breakout_risk must not be LOW.
   reason_code may be BREAKOUT_UNCONFIRMED.

4. If trend is valid, bos=True, choch=False, volume_spike>=80, and oi_growth>=80:
   status may be CLEAR.
   false_breakout_risk may be LOW.
   confluence may be STRONG.
   reason_code may be ALIGNED.

Do not reinterpret or override this semantic contract.

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
