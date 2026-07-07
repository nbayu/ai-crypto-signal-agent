import json
from pathlib import Path


def build_tradingview_symbol(symbol):
    if (
        not isinstance(symbol, str)
        or not symbol.endswith("/USDT:USDT")
        or symbol.count(":") != 1
    ):
        raise ValueError(
            "unsupported Binance perpetual symbol"
        )

    market_symbol = symbol.split(":")[0]
    normalized = market_symbol.replace("/", "")

    return f"BINANCE:{normalized}.P"


def build_tradingview_watchlist(artifact):
    setups = artifact["setups"]

    if artifact["setup_count"] != len(setups):
        raise ValueError(
            "setup_count does not match setups length"
        )

    return [
        build_tradingview_symbol(setup["symbol"])
        for setup in setups
    ]


def export_tradingview_watchlist(
    source_path,
    output_path,
):
    source_path = Path(source_path)
    output_path = Path(output_path)

    artifact = json.loads(source_path.read_text())
    watchlist = build_tradingview_watchlist(artifact)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = "".join(
        f"{symbol}\n"
        for symbol in watchlist
    )

    output_path.write_text(content)

    return output_path
