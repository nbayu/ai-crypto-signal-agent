from engine.research_journal import (
    find_latest_call,
    record_decision,
    record_trade,
    close_trade,
)


def process_command(command):
    parts = command.strip().upper().split()

    if not parts:
        raise ValueError("Perintah kosong")

    action = parts[0]

    if action in ["ENTRY", "SKIP"]:
        if len(parts) != 2:
            raise ValueError(
                "Format: ENTRY XRP atau SKIP XRP"
            )

        symbol = parts[1]

        record = find_latest_call(
            symbol,
            status="RESEARCHED",
        )

        if record is None:
            raise ValueError(
                f"Tidak ada research call aktif untuk {symbol}"
            )

        return record_decision(
            record["call_id"],
            action,
        )

    if action == "OPEN":
        if len(parts) != 6:
            raise ValueError(
                "Format: OPEN XRP LONG 100 95 110"
            )

        symbol = parts[1]
        side = parts[2]
        entry_price = parts[3]
        stop_loss = parts[4]
        take_profit = parts[5]

        record = find_latest_call(
            symbol,
            status="ENTERED",
        )

        if record is None:
            raise ValueError(
                f"Tidak ada decision ENTRY aktif untuk {symbol}"
            )

        return record_trade(
            record["call_id"],
            side,
            entry_price,
            stop_loss,
            take_profit,
        )

    if action == "CLOSE":
        if len(parts) != 5:
            raise ValueError(
                "Format: CLOSE XRP 110 WIN 10"
            )

        symbol = parts[1]
        exit_price = parts[2]
        result = parts[3]
        pnl_percent = parts[4]

        record = find_latest_call(
            symbol,
            status="TRADE_OPEN",
        )

        if record is None:
            raise ValueError(
                f"Tidak ada trade aktif untuk {symbol}"
            )

        return close_trade(
            record["call_id"],
            exit_price,
            result,
            pnl_percent,
        )

    raise ValueError(
        "Perintah harus ENTRY, SKIP, OPEN, atau CLOSE"
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Gunakan: ENTRY, SKIP, OPEN, atau CLOSE"
        )
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    try:
        record = process_command(command)

        print("Call ID :", record["call_id"])
        print("Symbol  :", record["symbol"])
        print("Status  :", record["status"])

        if record["decision"] is not None:
            print(
                "Decision:",
                record["decision"]["action"]
            )

        if record["trade"] is not None:
            print(
                "Trade   :",
                record["trade"]["side"]
            )

        if record["trader_outcome"] is not None:
            print(
                "Result  :",
                record["trader_outcome"]["result"]
            )
            print(
                "PnL     :",
                record["trader_outcome"]["pnl_percent"],
                "%"
            )

    except Exception as e:
        print("Error:", e)
