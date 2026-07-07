import json
import os
from datetime import datetime, timezone


JOURNAL_FILE = "data/journal/research_calls.json"


def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return []

    with open(JOURNAL_FILE, "r") as file:
        return json.load(file)


def save_journal(records):
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)

    with open(JOURNAL_FILE, "w") as file:
        json.dump(records, file, indent=2)


def create_research_call(market_data, research):
    records = load_journal()

    timestamp = datetime.now(timezone.utc)

    symbol_code = market_data.get("symbol", "UNKNOWN").split("/")[0]

    call_id = (
        f"RC-{timestamp.strftime('%Y%m%d-%H%M%S-%f')}-"
        f"{symbol_code}"
    )

    record = {
        "call_id": call_id,
        "created_at": timestamp.isoformat(),
        "symbol": market_data.get("symbol"),

        "market_snapshot": {
            "score": market_data.get("score"),
            "entry_score": market_data.get("entry_score"),
            "trend": market_data.get("trend"),
            "bos": market_data.get("bos"),
            "choch": market_data.get("choch"),
            "fvg": market_data.get("fvg"),
            "order_blocks": market_data.get("order_blocks"),
            "liquidity": market_data.get("liquidity"),
            "atr": market_data.get("atr"),
            "distance_ob": market_data.get("distance_ob"),
            "distance_fvg": market_data.get("distance_fvg"),
            "volume_spike": market_data.get("volume_spike"),
            "oi_growth": market_data.get("oi_growth"),
        },

        "research": {
            "status": research.get("research_status"),
            "confidence": research.get("confidence"),
            "strengths": research.get("strengths", []),
            "risks": research.get("risks", []),
        },

        "decision": None,
        "trade": None,
        "engine_outcome": None,
        "trader_outcome": None,
        "status": "RESEARCHED",
    }

    records.append(record)
    save_journal(records)

    return record

def record_decision(call_id, decision, notes=None):
    records = load_journal()

    decision = decision.upper()

    if decision not in ["ENTRY", "SKIP"]:
        raise ValueError("Decision harus ENTRY atau SKIP")

    for record in records:
        if record["call_id"] == call_id:
            record["decision"] = {
                "action": decision,
                "notes": notes,
                "decided_at": datetime.now(timezone.utc).isoformat(),
            }

            record["status"] = (
                "ENTERED" if decision == "ENTRY" else "SKIPPED"
            )

            save_journal(records)
            return record

    raise ValueError(f"Call ID tidak ditemukan: {call_id}")

def record_trade(
    call_id,
    side,
    entry_price,
    stop_loss,
    take_profit,
    notes=None,
):
    records = load_journal()

    side = side.upper()

    if side not in ["LONG", "SHORT"]:
        raise ValueError("Side harus LONG atau SHORT")

    for record in records:
        if record["call_id"] == call_id:

            if record["status"] != "ENTERED":
                raise ValueError(
                    "Trade hanya bisa dicatat setelah decision ENTRY"
                )

            record["trade"] = {
                "side": side,
                "entry_price": float(entry_price),
                "stop_loss": float(stop_loss),
                "take_profit": float(take_profit),
                "notes": notes,
                "entered_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            record["status"] = "TRADE_OPEN"

            save_journal(records)
            return record

    raise ValueError(f"Call ID tidak ditemukan: {call_id}")

def close_trade(
    call_id,
    exit_price,
    result,
    pnl_percent=None,
    notes=None,
):
    records = load_journal()

    result = result.upper()

    if result not in ["WIN", "LOSS", "BREAKEVEN"]:
        raise ValueError(
            "Result harus WIN, LOSS, atau BREAKEVEN"
        )

    for record in records:
        if record["call_id"] == call_id:

            if record["status"] != "TRADE_OPEN":
                raise ValueError(
                    "Trade hanya bisa ditutup jika status TRADE_OPEN"
                )

            record["trader_outcome"] = {
                "result": result,
                "exit_price": float(exit_price),
                "pnl_percent": (
                    float(pnl_percent)
                    if pnl_percent is not None
                    else None
                ),
                "notes": notes,
                "closed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            record["status"] = "TRADE_CLOSED"

            save_journal(records)
            return record

    raise ValueError(f"Call ID tidak ditemukan: {call_id}")

def record_engine_outcome(
    call_id,
    outcome,
    notes=None,
):
    records = load_journal()

    outcome = outcome.upper()

    if outcome not in ["VALID", "INVALID", "INCONCLUSIVE"]:
        raise ValueError(
            "Outcome harus VALID, INVALID, atau INCONCLUSIVE"
        )

    for record in records:
        if record["call_id"] == call_id:
            record["engine_outcome"] = {
                "result": outcome,
                "notes": notes,
                "validated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            save_journal(records)
            return record

    raise ValueError(f"Call ID tidak ditemukan: {call_id}")

def find_latest_call(symbol, status=None):
    records = load_journal()

    symbol = symbol.upper()

    matches = []

    for record in records:
        record_symbol = record.get("symbol", "").split("/")[0].upper()

        if record_symbol != symbol:
            continue

        if status is not None and record.get("status") != status:
            continue

        matches.append(record)

    if not matches:
        return None

    return max(
        matches,
        key=lambda record: record["created_at"]
    )
