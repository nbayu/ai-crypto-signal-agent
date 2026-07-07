import json
import requests
from engine.scanner import scan_market
from engine.research_journal import create_research_call
from engine.ai_research import research_market


def get_funding(symbol):
    try:
        sym = symbol.replace("/", "").replace(":USDT", "")
        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}"
        data = requests.get(url, timeout=5).json()
        return float(data.get("lastFundingRate", 0)) * 100
    except Exception:
        return None


def get_fear_greed():
    try:
        data = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5).json()
        item = data["data"][0]
        return int(item["value"]), item["value_classification"]
    except Exception:
        return None, None


results = scan_market()

if len(results) == 0:
    print("NO_RESULTS")
else:
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    fg_value, fg_label = get_fear_greed()

    output = []
    for r in results[:5]:
        research = research_market(r)
        journal_record = create_research_call(r, research)
        funding = get_funding(r["symbol"])
        row = dict(r)
        row["research"] = research
        row["call_id"] = journal_record["call_id"]
        row["funding_rate_pct"] = funding
        row["fear_greed_value"] = fg_value
        row["fear_greed_label"] = fg_label
        output.append(row)

    print(json.dumps(output, default=str, indent=2))
