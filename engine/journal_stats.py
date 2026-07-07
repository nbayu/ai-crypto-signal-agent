from collections import Counter

from engine.research_journal import load_journal


def calculate_basic_stats():
    records = load_journal()

    status_counts = Counter(
        record.get("status", "UNKNOWN")
        for record in records
    )

    return {
        "total_calls": len(records),
        "researched": status_counts.get("RESEARCHED", 0),
        "skipped": status_counts.get("SKIPPED", 0),
        "entered": status_counts.get("ENTERED", 0),
        "trade_open": status_counts.get("TRADE_OPEN", 0),
        "trade_closed": status_counts.get("TRADE_CLOSED", 0),
    }


def print_basic_stats():
    stats = calculate_basic_stats()

    print("=" * 50)
    print("JOURNAL STATISTICS")
    print("=" * 50)
    print("Total Research Calls :", stats["total_calls"])
    print("Researched           :", stats["researched"])
    print("Skipped              :", stats["skipped"])
    print("Entered              :", stats["entered"])
    print("Trade Open           :", stats["trade_open"])
    print("Trade Closed         :", stats["trade_closed"])

def calculate_trade_stats():
    records = load_journal()

    decisions = [
        record
        for record in records
        if record.get("decision") is not None
    ]

    entered = [
        record
        for record in decisions
        if record["decision"]["action"] == "ENTRY"
    ]

    skipped = [
        record
        for record in decisions
        if record["decision"]["action"] == "SKIP"
    ]

    closed_trades = [
        record
        for record in records
        if record.get("trader_outcome") is not None
    ]

    wins = sum(
        1
        for record in closed_trades
        if record["trader_outcome"]["result"] == "WIN"
    )

    losses = sum(
        1
        for record in closed_trades
        if record["trader_outcome"]["result"] == "LOSS"
    )

    breakeven = sum(
        1
        for record in closed_trades
        if record["trader_outcome"]["result"] == "BREAKEVEN"
    )

    total_decisions = len(decisions)
    total_closed = len(closed_trades)

    entry_rate = (
        len(entered) / total_decisions * 100
        if total_decisions > 0
        else 0
    )

    win_rate = (
        wins / total_closed * 100
        if total_closed > 0
        else 0
    )

    return {
        "total_decisions": total_decisions,
        "entered": len(entered),
        "skipped": len(skipped),
        "entry_rate": entry_rate,
        "closed_trades": total_closed,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate": win_rate,
    }

def calculate_engine_stats():
    records = load_journal()

    validated = [
        record
        for record in records
        if record.get("engine_outcome") is not None
    ]

    valid = sum(
        1
        for record in validated
        if record["engine_outcome"]["result"] == "VALID"
    )

    invalid = sum(
        1
        for record in validated
        if record["engine_outcome"]["result"] == "INVALID"
    )

    inconclusive = sum(
        1
        for record in validated
        if record["engine_outcome"]["result"] == "INCONCLUSIVE"
    )

    conclusive = valid + invalid

    validation_rate = (
        valid / conclusive * 100
        if conclusive > 0
        else 0
    )

    return {
        "total_validated": len(validated),
        "valid": valid,
        "invalid": invalid,
        "inconclusive": inconclusive,
        "validation_rate": validation_rate,
    }

def calculate_status_performance():
    records = load_journal()

    statuses = [
        "STRONG CANDIDATE",
        "WORTH REVIEWING",
        "LOW PRIORITY",
    ]

    performance = {}

    for status in statuses:
        status_records = [
            record
            for record in records
            if record.get("research", {}).get("status") == status
        ]

        validated = [
            record
            for record in status_records
            if record.get("engine_outcome") is not None
        ]

        valid = sum(
            1
            for record in validated
            if record["engine_outcome"]["result"] == "VALID"
        )

        invalid = sum(
            1
            for record in validated
            if record["engine_outcome"]["result"] == "INVALID"
        )

        conclusive = valid + invalid

        validation_rate = (
            valid / conclusive * 100
            if conclusive > 0
            else 0
        )

        performance[status] = {
            "calls": len(status_records),
            "validated": len(validated),
            "valid": valid,
            "invalid": invalid,
            "validation_rate": validation_rate,
        }

    return performance

def calculate_confidence_performance():
    records = load_journal()

    ranges = {
        "90-100": (90, 100),
        "80-89": (80, 89),
        "70-79": (70, 79),
        "BELOW 70": (0, 69),
    }

    performance = {}

    for label, (minimum, maximum) in ranges.items():
        range_records = []

        for record in records:
            confidence = record.get(
                "research", {}
            ).get("confidence")

            if confidence is None:
                continue

            if minimum <= confidence <= maximum:
                range_records.append(record)

        validated = [
            record
            for record in range_records
            if record.get("engine_outcome") is not None
        ]

        valid = sum(
            1
            for record in validated
            if record["engine_outcome"]["result"] == "VALID"
        )

        invalid = sum(
            1
            for record in validated
            if record["engine_outcome"]["result"] == "INVALID"
        )

        conclusive = valid + invalid

        validation_rate = (
            valid / conclusive * 100
            if conclusive > 0
            else 0
        )

        performance[label] = {
            "calls": len(range_records),
            "validated": len(validated),
            "valid": valid,
            "invalid": invalid,
            "validation_rate": validation_rate,
        }

    return performance

if __name__ == "__main__":
    print_basic_stats()

    trade_stats = calculate_trade_stats()

    print()
    print("=" * 50)
    print("DECISION & TRADE PERFORMANCE")
    print("=" * 50)
    print("Total Decisions :", trade_stats["total_decisions"])
    print("Entered         :", trade_stats["entered"])
    print("Skipped         :", trade_stats["skipped"])
    print(f"Entry Rate      : {trade_stats['entry_rate']:.1f}%")
    print("Closed Trades   :", trade_stats["closed_trades"])
    print("Wins            :", trade_stats["wins"])
    print("Losses          :", trade_stats["losses"])
    print("Breakeven       :", trade_stats["breakeven"])
    print(f"Win Rate        : {trade_stats['win_rate']:.1f}%")

    engine_stats = calculate_engine_stats()

    print()
    print("=" * 50)
    print("ENGINE VALIDATION PERFORMANCE")
    print("=" * 50)
    print("Total Validated :", engine_stats["total_validated"])
    print("Valid           :", engine_stats["valid"])
    print("Invalid         :", engine_stats["invalid"])
    print("Inconclusive    :", engine_stats["inconclusive"])
    print(
        f"Validation Rate : "
        f"{engine_stats['validation_rate']:.1f}%"
    )

    status_performance = calculate_status_performance()

    print()
    print("=" * 50)
    print("PERFORMANCE BY RESEARCH STATUS")
    print("=" * 50)

    for status, stats in status_performance.items():
        print()
        print(status)
        print("Calls           :", stats["calls"])
        print("Validated       :", stats["validated"])
        print("Valid           :", stats["valid"])
        print("Invalid         :", stats["invalid"])
        print(
            f"Validation Rate : "
            f"{stats['validation_rate']:.1f}%"
        )

    confidence_performance = calculate_confidence_performance()

    print()
    print("=" * 50)
    print("PERFORMANCE BY CONFIDENCE RANGE")
    print("=" * 50)

    for label, stats in confidence_performance.items():
        print()
        print(label)
        print("Calls           :", stats["calls"])
        print("Validated       :", stats["validated"])
        print("Valid           :", stats["valid"])
        print("Invalid         :", stats["invalid"])
        print(
            f"Validation Rate : "
            f"{stats['validation_rate']:.1f}%"
        )
