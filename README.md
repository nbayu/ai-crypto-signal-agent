# Trading OS v2

Owner: Sayang

Purpose:
Mencari coin futures yang memiliki probabilitas tinggi berdasarkan kombinasi:

- Market Structure
- Trendline Direction
- Trendline Breakout
- Smart Money Concept
- Volume Confirmation
- Open Interest
- Funding Rate
- Fear & Greed
- Multi Timeframe Confirmation

Bot tidak menentukan entry.

Bot hanya melakukan screening dan ranking.

Keputusan entry menggunakan metode Fibonacci milik user.

Priority:

1. Protect Capital
2. High Probability Setup
3. Quality over Quantity

Workflow:

Market Scan
↓

Liquidity Filter
↓

Trend Filter
↓

Market Structure
↓

Trendline
↓

SMC
↓

Derivative
↓

Score
↓

Watchlist

## Production Execution

Current production execution is manual.

Official command:

    ./run_scanner.sh

Run the scanner no earlier than 10 minutes after a 4H candle close.

UTC launch times:

    00:10
    04:10
    08:10
    12:10
    16:10
    20:10

WIB launch times:

    07:10
    11:10
    15:10
    19:10
    23:10
    03:10

The scanner does not need to run at every 4H window. Run it only when a new production screening is required.

Automatic scheduling is not enabled in the current production workflow.

## Forward Test Execution

Forward Test execution is manual.

Official command:

    .venv/bin/python -m engine.run_forward_test_v4 \
      data/v4_outcomes/outcome_entry_v4_<timestamp>.json

The command requires one explicit outcome entry artifact.

Do not use automatic latest-file discovery. The operator must select the exact `outcome_entry_v4_*.json` artifact to resolve and validate.

Forward Test horizons are:

    H4
    H8
    H12

A horizon becomes eligible when its target time has been reached.

Operationally, run the command no earlier than 10 minutes after an eligible horizon target so the required closed 4H candle data is available.

The runner is safe to execute repeatedly for the same entry artifact.

Already resolved horizons are skipped. Only eligible unresolved horizons are added. If no new horizon is eligible, the resolution remains unchanged.

The same explicit entry artifact may therefore be run after H4, again after H8, and again after H12.

Automatic scheduling and automatic artifact discovery are not enabled in the current Forward Test workflow.

## Pre-Delivery Validation

Each successful production scanner run first preserves the raw Top 5 scanner artifact:

    data/top5_watchlist_v4/latest.json

Before delivery, every setup is validated against current closed 4H candles.

A setup remains delivery eligible only when:

- its historical lifecycle is still actionable
- it has not been superseded by a replacement swing pair

The filtered delivery artifact is written to:

    data/pre_delivery_v4/latest.json

The raw Top 5 artifact remains unchanged as scanner evidence.

Pre-delivery validation does not change scanner logic, scoring, ranking, quality thresholds, Golden Zone logic, or Forward Test behavior.

## TradingView Watchlist Export

Each successful production scanner run automatically exports only delivery-eligible setups to TradingView.

Source artifact:

    data/pre_delivery_v4/latest.json

TradingView import file:

    data/top5_watchlist_v4/tradingview_watchlist.txt

The export preserves the original scanner ranking order among eligible setups. It does not rerank the filtered results.

Binance USDT perpetual symbols are normalized to TradingView format:

    BTC/USDT:USDT -> BINANCE:BTCUSDT.P

## V4 Master Engine Boundary

The canonical production orchestration entrypoint is:

    ./run_scanner.sh

The script delegates to:

    python -m engine.run_validated_dry_v4

`engine.run_validated_dry_v4` is intentionally a thin CLI wrapper around:

    engine.master_engine_v4.run_master_engine_v4()

`run_master_engine_v4()` is the canonical production orchestration boundary for the V4 scanner delivery path. It owns the ordered production flow:

1. scan the market through the scanner facade;
2. run the validated V4 pipeline;
3. save the validated snapshot;
4. save the forward outcome entry snapshot;
5. save the raw Top 5 watchlist artifact;
6. run the pre-delivery validation and TradingView/Pine bridge artifact flow;
7. save immutable production evidence;
8. return all generated paths and the validated output.

Production callers such as Telegram commands, future schedulers, or other operator interfaces must call the master engine boundary instead of reimplementing the production flow or calling lower-level artifact writers directly.

`engine.v4_baseline_collector` remains a separate baseline-analysis tool. It may call `scan_market()` directly because it does not run the production delivery path, does not create production evidence, and has separate semantic-rejection capture behavior.

The scanner remains a public facade and orchestration boundary for scanner-level responsibilities. Production integration must not bypass or duplicate scanner internals.
