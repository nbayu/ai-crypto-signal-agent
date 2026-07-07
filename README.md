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
