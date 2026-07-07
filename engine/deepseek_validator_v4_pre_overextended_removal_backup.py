import os
import json
from openai import OpenAI

MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """
You are a strictly bounded validation gate for a crypto market scanner.

Python is the source of truth.

YOUR ONLY JOB:
Evaluate every candidate exactly once using only its supplied data.

AUTHORITY BOUNDARY:

Python already:
- calculates market structure
- calculates raw volume_ratio
- calculates raw oi_change_pct
- classifies volume evidence
- classifies open-interest evidence
- classifies combined participation

You MUST NOT:
- recalculate thresholds
- create new thresholds
- override Python evidence classifications
- infer missing data
- use outside market knowledge

STRUCTURE CONTRACT:

- trend=UPTREND is a valid bullish structure.
- trend=DOWNTREND is a valid bearish structure.
- Trend direction alone is NEVER a risk or conflict.

- bos=True means structure breakout is confirmed.
- bos=False means breakout confirmation is absent.

- choch=True means possible structure reversal.
- choch=True is ALWAYS a structural conflict.
- A candidate with choch=True MUST NOT receive status=CLEAR.
- A candidate with choch=True MUST NOT receive reason_code=ALIGNED.

EVIDENCE CONTRACT:

volume_class is authoritative:
- WEAK
- NORMAL
- SUPPORTIVE
- STRONG
- UNKNOWN

oi_class is authoritative:
- WEAK
- SOFT
- SUPPORTIVE
- STRONG
- UNKNOWN

participation is authoritative:
- WEAK
- NEUTRAL
- MIXED
- SUPPORTIVE
- STRONG
- UNKNOWN

Interpretation:

- participation=STRONG means participation strongly supports the structure.
- participation=SUPPORTIVE means participation supports the structure.
- participation=NEUTRAL means evidence is neither confirmation nor material conflict.
- participation=MIXED means confirmation evidence conflicts and requires caution.
- participation=WEAK means participation is materially weak.
- participation=UNKNOWN means data is unavailable or invalid. UNKNOWN is NEVER equivalent to WEAK.

RAW EVIDENCE:

- volume_ratio and oi_change_pct are audit evidence only.
- Do not create new thresholds from raw evidence.
- Do not override volume_class, oi_class, or participation.

CANDIDATE-LEVEL CONSTRAINTS:

- Each candidate may include semantic_constraints.
- semantic_constraints are deterministic Python-owned restrictions.
- You MUST obey every forbidden_reason_code supplied for that candidate.
- You MUST NOT return a forbidden reason_code for that candidate.
- Candidate-level constraints do not change Python evidence.

VALIDATION PRECEDENCE:

1. If choch=True:
   status must be CONFLICT or HIGH_RISK.
   reason_code must not be ALIGNED.

2. If participation=WEAK:
   status must be HIGH_RISK.
   false_breakout_risk must be HIGH.
   confluence must be WEAK.
   reason_code must be WEAK_PARTICIPATION or MULTIPLE_CONFLICTS.

3. If participation=MIXED:
   status must not be CLEAR.
   false_breakout_risk must not be LOW.
   reason_code must reflect the supplied conflict.

4. If participation=UNKNOWN:
   status must not be HIGH_RISK solely because data is unavailable.
   reason_code must not be WEAK_VOLUME, WEAK_OI, or WEAK_PARTICIPATION solely because evidence is UNKNOWN.

5. If bos=False:
   false_breakout_risk must not be LOW.
   reason_code may be BREAKOUT_UNCONFIRMED.

6. If bos=True:
   reason_code must not be BREAKOUT_UNCONFIRMED.

7. If trend is valid, bos=True, choch=False, and participation is SUPPORTIVE or STRONG:
   status may be CLEAR.
   false_breakout_risk may be LOW.
   confluence may be STRONG.
   reason_code may be ALIGNED.

YOU MAY:
- detect conflicts between structure and supplied evidence
- assess false-breakout risk
- assess confluence quality
- interpret MIXED participation in structure context

YOU MUST NOT:
- select candidates
- remove candidates
- rank candidates
- change or recalculate Python scores
- change Python evidence classifications
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
- MIXED_PARTICIPATION
- DATA_UNAVAILABLE
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

    constrained_candidates = []

    for candidate in candidates:
        ai_candidate = dict(candidate)

        forbidden_reason_codes = []

        # BOS reverse invariant.
        if candidate.get("bos") is True:
            forbidden_reason_codes.append(
                "BREAKOUT_UNCONFIRMED"
            )

        # CHOCH reverse invariant.
        if candidate.get("choch") is not True:
            forbidden_reason_codes.append(
                "STRUCTURE_REVERSAL_CONFLICT"
            )

        participation = candidate.get(
            "participation"
        )

        # MIXED reverse invariant.
        if participation != "MIXED":
            forbidden_reason_codes.append(
                "MIXED_PARTICIPATION"
            )

        # WEAK reverse invariant.
        if participation != "WEAK":
            forbidden_reason_codes.append(
                "WEAK_PARTICIPATION"
            )

        # ALIGNED reverse contracts.
        if participation in {
            "MIXED",
            "WEAK",
            "UNKNOWN",
        }:
            forbidden_reason_codes.append(
                "ALIGNED"
            )

        ai_candidate["semantic_constraints"] = {
            "forbidden_reason_codes":
                forbidden_reason_codes
        }

        constrained_candidates.append(
            ai_candidate
        )

    payload = {
        "task": "Validate every candidate exactly once.",
        "candidate_count": len(candidates),
        "candidates": constrained_candidates
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
