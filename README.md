# 📊 Trading Performance Dashboard
### Full-Stack Institutional Analytics · Medallion Lakehouse Architecture

> **PostgreSQL · Python ETL · Power Query (M) · Power BI · DAX**
> Net P&L · Win Rate · Expectancy (R) · Sharpe · Calmar · Drawdown · Recovery Factor

---

<div align="center">

[![Architecture](https://img.shields.io/badge/Architecture-Medallion%20Lakehouse-1B4F8A?style=for-the-badge)](https://github.com/Datuned)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![BI Tool](https://img.shields.io/badge/BI%20Tool-Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)
[![Language](https://img.shields.io/badge/ETL-Python%203.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 📥 Download

| Asset | Link |
|---|---|
| **Power BI Project Files (RAR)** | [⬇ Download POWER_BI.rar](https://github.com/Datuned/Trading-Operations-Excel-Dashboard/raw/master/DASHBOARD/Trading_Operations_Dashboard.xlsx) |
| **Previous Excel Dashboard** | [⬇ Trading Operations Excel Dashboard](https://github.com/Datuned/Trading-Operations-Excel-Dashboard/raw/master/DASHBOARD/Trading_Operations_Dashboard.xlsx) |

---

## 📸 Dashboard Preview

![Trading Performance Dashboard](dashboard.png)

*1920×1080 dark-canvas dashboard — Live KPI cards, equity curve, drawdown chart, P&L by trade type and day of week.*

---

## 📋 Performance Report

> **Overall Verdict:** This account started at $10,000.00 and has declined to $9,093.37 — a net loss of $906.63 (–9.07%) over 42 trading days across 53 closed trades. Every key risk-adjusted performance metric is below acceptable institutional benchmarks. Immediate attention is required on trade selection, stop-loss discipline, and session timing.

> **Critical Finding — Scalp Trades Are Destroying The Account:** Scalp trades account for 24 of 53 trades and generated –$813.22 in losses. That is 89.7% of the total account loss from a single trade type with a 0% win rate.

> **Silver Lining:** The average win ($61.44) is LARGER than the average loss ($42.63) — a win/loss ratio of 1.44:1. The edge exists but is triggered far too rarely. Improving trade selection to increase win frequency is the primary lever.

---

## 🏗 Architecture — Medallion Lakehouse

This project is built on the **Medallion Lakehouse Architecture**, an industry-proven multi-layer data engineering pattern originally popularized by Databricks and now widely adopted across institutional quantitative desks, hedge funds, and systematic trading firms.

```
┌─────────────────────────────────────────────────────────────────┐
│              MEDALLION LAKEHOUSE PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│  SOURCE          BRONZE           SILVER           GOLD          │
│  trades.xlsx ──▶ bronze.trades ──▶ silver.trades ──▶ gold.*     │
│  (21 columns)    (immutable)      (enriched +       (aggregated) │
│                                   duration type)                 │
│                                                    ▼             │
│                                              POWER BI            │
│                                           (Import Mode)          │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Responsibility |
|---|---|
| **🥉 Bronze** | Exact copy of source data from Excel. Immutable, append-only. No transformations. |
| **🥈 Silver** | Parsed, typed, and enriched. Duration-based session classification, date dimensions, outcome flags. |
| **🥇 Gold** | Aggregated analytical tables: Daily P&L, Equity Curve, Trade Type P&L, Performance Metrics. |
| **💎 Semantic** | Power BI star-schema data model with DAX measures and RLS-ready structure. |

**Why Medallion for Trading Analytics:**
- Full data lineage — every number traceable back to raw source
- Incremental loading — append new trades without full refresh
- Separation of concerns — ETL bugs in Silver never corrupt Bronze
- Power BI performance — Gold tables are pre-aggregated for sub-second visuals
- Audit-ready — prop firms and regulators can verify every calculation

---

## 📁 Project Structure

```
POWER_BI/
├── trades.xlsx                  # Source trade data (21 columns, broker export)
├── trading.sql                  # Schema blueprint — Bronze → Silver → Gold DDL
├── etl_pipeline.py              # Python ETL: dedup, Bronze append, Silver/Gold rebuild
├── POWER_BI.pbix                # Power BI report file
├── Institutional_Trading_
│   PowerBI_Guide_v2.docx        # Full build guide & documentation
└── README.md                    # This file
```

---

## 📊 Data Schema — trades.xlsx (21 Columns)

| Column | Type | Example | Notes |
|---|---|---|---|
| Order ID | TEXT | OID149830292 | Broker order identifier |
| Symbol | TEXT | US100.cash | Instrument |
| Opening direction | TEXT | Buy / Sell | Entry direction |
| Closing direction | TEXT | Sell / Buy | Exit direction |
| Opening time | TIMESTAMP | 12/03/2026 15:00:51 | Used for duration calc |
| Closing time | TIMESTAMP | 13/03/2026 13:45:10 | Close datetime |
| Entry price | NUMERIC | 24669.83 | Open price |
| Closing price | NUMERIC | 24667.25 | Close price |
| Closing Quantity | NUMERIC | 1.00 | Lot size |
| Closing volume (USD) | NUMERIC | 24668.25 | Notional value |
| Swap | NUMERIC | -2.82 | Overnight financing |
| Commission | INTEGER | 0 | Broker commission |
| Gross $ | NUMERIC | 2.58 | Pre-cost P&L |
| Net $ | NUMERIC | -0.24 | Realised P&L |
| Balance $ | NUMERIC | 9999.76 | Running account balance |
| Pips | NUMERIC | 2.58 | Price move in pips |
| Channel | TEXT | cTrader | Platform used |

---

## 🐘 PostgreSQL — Full SQL Schema

### Step 1 — Create Schemas

```sql
-- Three-schema medallion pattern
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
```

---

### Step 2 — Bronze Layer (Raw Ingestion)

```sql
CREATE TABLE IF NOT EXISTS bronze.trades (
    id                  SERIAL PRIMARY KEY,
    order_id            TEXT,
    symbol              TEXT,
    opening_direction   TEXT,
    closing_direction   TEXT,
    opening_time_raw    TEXT,          -- stored as text: preserves ms precision
    closing_time_raw    TEXT,          -- stored as text: preserves ms precision
    entry_price         NUMERIC(12,5),
    closing_price       NUMERIC(12,5),
    closing_quantity    NUMERIC(10,4),
    closing_volume      NUMERIC(10,4),
    closing_volume_usd  NUMERIC(14,4),
    swap                NUMERIC(10,4),
    commission          NUMERIC(10,4),
    gross_pnl           NUMERIC(12,4),
    net_pnl             NUMERIC(12,4),
    balance             NUMERIC(14,4),
    pips                NUMERIC(10,4),
    requested_quantity  NUMERIC(10,4),
    channel             TEXT,
    label               TEXT,
    comment             TEXT,
    loaded_at           TIMESTAMPTZ DEFAULT now(),
    source_file         TEXT DEFAULT 'trades.xlsx'
);
```

---

### Step 3 — Silver Layer (Cleansed & Enriched)

Trade duration is computed from opening → closing timestamps. Session type is classified by hold time — not the hour of day.

| Session Type | Rule | Example |
|---|---|---|
| **Scalp** | ≤ 1 hour | 6 min, 25 min, 59 min |
| **Intra-Day** | > 1 hour and ≤ 24 hours | 1.1 hr, 12 hr, 22.7 hr |
| **Swing** | > 24 hours | 36 hr, 59 hr |

**Trade Outcome Classification (threshold-based):**

| Outcome | Rule |
|---|---|
| **Win** | `net_pnl >= balance × 0.005` (≥ 0.5% of account balance) |
| **Breakeven** | `net_pnl > 0` but below 0.5% threshold |
| **Loss** | `net_pnl ≤ 0` |

```sql
CREATE TABLE IF NOT EXISTS silver.trades AS
SELECT
    id,
    order_id,
    symbol,
    TRIM(opening_direction)                                                              AS direction,
    TRIM(closing_direction)                                                              AS closing_direction,

    -- Parse both timestamps (DD/MM/YYYY HH24:MI:SS.MS format)
    TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ            AS opening_time,
    TO_TIMESTAMP(closing_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ            AS closing_time,

    entry_price, closing_price, closing_quantity, closing_volume,
    closing_volume_usd, swap, commission, gross_pnl, net_pnl, balance, pips, channel,

    -- Date Dimensions (derived from opening_time)
    DATE(TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'))                   AS trade_date,
    EXTRACT(YEAR  FROM TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'))     AS trade_year,
    EXTRACT(MONTH FROM TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'))     AS trade_month,
    TO_CHAR(TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'), 'Month')       AS month_name,
    EXTRACT(DOW   FROM TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'))     AS day_of_week_num,
    TO_CHAR(TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'), 'Day')         AS day_of_week_name,
    EXTRACT(WEEK  FROM TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'))     AS iso_week,
    EXTRACT(QUARTER FROM TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS'))   AS trade_quarter,

    -- Trade Duration in Hours
    ROUND(
        EXTRACT(EPOCH FROM (
            TO_TIMESTAMP(closing_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS') -
            TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS')
        )) / 3600.0, 4
    )                                                                                    AS trade_duration_hours,

    -- Trade Type: DURATION-BASED
    CASE
        WHEN EXTRACT(EPOCH FROM (
            TO_TIMESTAMP(closing_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS') -
            TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS')
        )) / 3600.0 <= 1  THEN 'Scalp'
        WHEN EXTRACT(EPOCH FROM (
            TO_TIMESTAMP(closing_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS') -
            TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS')
        )) / 3600.0 <= 24 THEN 'Intra-Day'
        ELSE 'Swing'
    END                                                                                  AS trade_type,

    -- Trade Outcome (threshold-based: 0.5% of account balance)
    CASE
        WHEN net_pnl >= (balance * 0.005) THEN 'Win'
        WHEN net_pnl > 0                  THEN 'Breakeven'
        ELSE                                   'Loss'
    END                                                                                  AS trade_outcome,

    ABS(closing_price - entry_price)                                                     AS price_move,
    (closing_price - entry_price)                                                        AS price_delta,
    loaded_at,
    source_file

FROM bronze.trades;

-- Primary key and performance indexes
ALTER TABLE silver.trades ADD PRIMARY KEY (id);
CREATE INDEX idx_silver_trade_date       ON silver.trades(trade_date);
CREATE INDEX idx_silver_direction        ON silver.trades(direction);
CREATE INDEX idx_silver_trade_outcome    ON silver.trades(trade_outcome);
CREATE INDEX idx_silver_trade_type       ON silver.trades(trade_type);
CREATE INDEX idx_silver_duration         ON silver.trades(trade_duration_hours);
CREATE INDEX idx_silver_year_month       ON silver.trades(trade_year, trade_month);
```

---

### Step 4 — Gold Layer (Analytical Aggregates)

#### 4a. Daily P&L Summary

```sql
CREATE TABLE gold.daily_pnl AS
SELECT
    trade_date, trade_year, trade_month, month_name,
    day_of_week_name, day_of_week_num, iso_week,
    COUNT(*)                                                    AS total_trades,
    SUM(net_pnl)                                                AS daily_pnl,
    SUM(CASE WHEN trade_outcome = 'Win'       THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN trade_outcome = 'Loss'      THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN trade_outcome = 'Breakeven' THEN 1 ELSE 0 END) AS breakevens,
    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)          AS gross_profit,
    SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)          AS gross_loss,
    MAX(balance)                                                 AS eod_balance
FROM silver.trades
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY trade_date;
```

#### 4b. Running Equity Curve & Drawdown

```sql
CREATE TABLE gold.equity_curve AS
SELECT
    trade_date,
    eod_balance,

    -- High-water mark
    MAX(eod_balance) OVER (
        ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                           AS peak_balance,

    -- Drawdown in $
    eod_balance - MAX(eod_balance) OVER (
        ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                           AS drawdown_abs,

    -- Drawdown %
    ROUND(
        (eod_balance - MAX(eod_balance) OVER (
            ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )) / NULLIF(MAX(eod_balance) OVER (
            ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 0) * 100, 4
    )                                                           AS drawdown_pct,

    -- Cumulative P&L
    SUM(daily_pnl) OVER (
        ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                           AS cumulative_pnl

FROM gold.daily_pnl
ORDER BY trade_date;
```

#### 4c. Trade Type Aggregations

```sql
CREATE TABLE gold.trade_type_pnl AS
SELECT
    trade_type,
    COUNT(*)                                                                AS total_trades,
    SUM(net_pnl)                                                            AS total_pnl,
    SUM(CASE WHEN trade_outcome = 'Win'  THEN 1 ELSE 0 END)                AS wins,
    SUM(CASE WHEN trade_outcome = 'Loss' THEN 1 ELSE 0 END)                AS losses,
    ROUND(SUM(CASE WHEN trade_outcome = 'Win' THEN 1 ELSE 0 END)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2)                                     AS win_rate_pct,
    ROUND(AVG(net_pnl), 4)                                                  AS avg_pnl,
    ROUND(
        SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0),
        4
    )                                                                       AS profit_factor
FROM silver.trades
GROUP BY trade_type
ORDER BY trade_type;
```

#### 4d. Performance Metrics Summary

```sql
CREATE TABLE gold.performance_metrics AS
WITH base AS (
    SELECT
        COUNT(*)                                                    AS total_trades,
        SUM(net_pnl)                                               AS net_pnl,
        SUM(CASE WHEN trade_outcome = 'Win'       THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN trade_outcome = 'Loss'      THEN 1 ELSE 0 END) AS losses,
        SUM(CASE WHEN trade_outcome = 'Breakeven' THEN 1 ELSE 0 END) AS breakevens,
        SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)         AS gross_profit,
        ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END))    AS gross_loss,
        AVG(net_pnl)                                               AS avg_trade_pnl,
        AVG(CASE WHEN net_pnl > 0 THEN net_pnl END)                AS avg_win,
        AVG(CASE WHEN net_pnl < 0 THEN net_pnl END)                AS avg_loss
    FROM silver.trades
),
daily AS (
    SELECT AVG(daily_pnl) AS avg_daily_pnl, STDDEV_SAMP(daily_pnl) AS stddev_daily_pnl
    FROM gold.daily_pnl
),
dd AS (
    SELECT MIN(drawdown_pct) AS max_drawdown_pct, MIN(drawdown_abs) AS max_drawdown_abs
    FROM gold.equity_curve
),
td AS (
    SELECT COUNT(DISTINCT trade_date) AS trading_days FROM silver.trades
),
sb AS (
    SELECT balance AS starting_balance
    FROM silver.trades
    ORDER BY opening_time ASC
    LIMIT 1
)
SELECT
    b.total_trades, b.net_pnl, b.wins, b.losses, b.breakevens,
    b.gross_profit, b.gross_loss,

    -- Win Rate
    ROUND(b.wins::NUMERIC / NULLIF(b.total_trades, 0) * 100, 2)                AS win_rate_pct,

    -- Profit Factor
    ROUND(b.gross_profit::NUMERIC / NULLIF(b.gross_loss::NUMERIC, 0), 4)        AS profit_factor,

    -- Expectancy in R-Multiples
    ROUND(
        ((b.wins::NUMERIC / NULLIF(b.total_trades, 0)) * COALESCE(b.avg_win, 0) / NULLIF(ABS(b.avg_loss), 0))
      + ((b.losses::NUMERIC / NULLIF(b.total_trades, 0)) * COALESCE(b.avg_loss, 0) / NULLIF(ABS(b.avg_loss), 0)),
        4
    )                                                                            AS expectancy_r,

    ROUND(b.avg_trade_pnl::NUMERIC, 4)                                           AS avg_trade_pnl,

    -- Sharpe Ratio (annualised, 252 trading days)
    ROUND(
        (d.avg_daily_pnl::NUMERIC / NULLIF(d.stddev_daily_pnl::NUMERIC, 0))
        * SQRT(252)::NUMERIC, 4
    )                                                                            AS sharpe_ratio,

    -- Calmar Ratio = Annualised Return / |Max Drawdown %|
    ROUND(
        ((b.net_pnl::NUMERIC / NULLIF(sb.starting_balance::NUMERIC, 0)) * 252
         / NULLIF(td.trading_days::NUMERIC, 0))
        / NULLIF(ABS(dd.max_drawdown_pct::NUMERIC) / 100.0, 0),
        4
    )                                                                            AS calmar_ratio,

    -- Recovery Factor = Net P&L / |Max Drawdown $|
    ROUND(b.net_pnl::NUMERIC / NULLIF(ABS(dd.max_drawdown_abs::NUMERIC), 0), 4) AS recovery_factor,

    dd.max_drawdown_pct,
    dd.max_drawdown_abs

FROM base b
CROSS JOIN daily d
CROSS JOIN dd
CROSS JOIN td
CROSS JOIN sb;
```

---

## 🐍 Python ETL Pipeline

### Installation

```bash
pip install pandas psycopg2-binary openpyxl sqlalchemy python-dotenv
```

### Environment Setup

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/trading_analytics
```

### Full ETL Script (`etl_pipeline.py`)

```python
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL not found in the .env file.")

engine = create_engine(DATABASE_URL)

# ── Read Excel source ──────────────────────────────────────────────────────────
df_new = pd.read_excel("trades.xlsx", sheet_name="Records")

df_new.columns = [
    "order_id", "symbol", "opening_direction", "closing_direction",
    "opening_time_raw", "closing_time_raw",
    "entry_price", "closing_price", "closing_quantity",
    "closing_volume", "closing_volume_usd",
    "swap", "commission", "gross_pnl", "net_pnl", "balance",
    "pips", "requested_quantity", "channel", "label", "comment",
]

# ── Deduplication — read existing order_ids from Bronze ───────────────────────
existing   = pd.read_sql("SELECT order_id FROM bronze.trades", engine)
is_new     = ~df_new["order_id"].isin(existing["order_id"])
df_new_only = df_new[is_new]

total_in_file     = len(df_new)
total_in_database = len(existing)
total_new         = len(df_new_only)
total_duplicates  = len(df_new[~is_new])

print("=" * 50)
print("     ETL PIPELINE PRELOAD REPORT")
print("=" * 50)
print(f"Trades in new Excel file   : {total_in_file}")
print(f"Trades already in database : {total_in_database}")
print(f"Genuinely new trades found : {total_new}")
print(f"Duplicates skipped         : {total_duplicates}")
print("=" * 50)

if total_new == 0:
    print("STATUS: No new trades found. Database is up to date.")
else:
    # Preserve datetime strings for PostgreSQL parsing
    df_new_only = df_new_only.copy()
    df_new_only["opening_time_raw"] = df_new_only["opening_time_raw"].astype(str)
    df_new_only["closing_time_raw"]  = df_new_only["closing_time_raw"].astype(str)

    # ── Bronze: APPEND ONLY ────────────────────────────────────────────────────
    df_new_only.to_sql("trades", engine, schema="bronze", if_exists="append", index=False)
    print(f"STATUS: {total_new} new trades loaded into bronze.trades.")

# ── Refresh Silver and Gold ────────────────────────────────────────────────────
with engine.connect() as conn:

    # Silver: full TRUNCATE + rebuild
    conn.execute(text("TRUNCATE silver.trades RESTART IDENTITY CASCADE"))
    conn.execute(text("""
        INSERT INTO silver.trades
        SELECT
            id, order_id, symbol,
            TRIM(opening_direction) AS direction,
            TRIM(closing_direction) AS closing_direction,
            TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ AS opening_time,
            TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ AS closing_time,
            entry_price, closing_price, closing_quantity, closing_volume,
            closing_volume_usd, swap, commission, gross_pnl, net_pnl, balance, pips, channel,
            DATE(TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'))           AS trade_date,
            EXTRACT(YEAR  FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_year,
            EXTRACT(MONTH FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_month,
            TO_CHAR(TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'),'Month')    AS month_name,
            EXTRACT(DOW  FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'))  AS day_of_week_num,
            TO_CHAR(TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'),'Day')      AS day_of_week_name,
            EXTRACT(WEEK FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'))  AS iso_week,
            EXTRACT(QUARTER FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_quarter,
            ROUND(EXTRACT(EPOCH FROM (
                TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS') -
                TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')
            ))/3600.0, 4) AS trade_duration_hours,
            CASE
                WHEN EXTRACT(EPOCH FROM (
                    TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS') -
                    TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')
                ))/3600.0 <= 1  THEN 'Scalp'
                WHEN EXTRACT(EPOCH FROM (
                    TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS') -
                    TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')
                ))/3600.0 <= 24 THEN 'Intra-Day'
                ELSE 'Swing'
            END AS trade_type,
            CASE
                WHEN net_pnl >= (balance * 0.005) THEN 'Win'
                WHEN net_pnl > 0                  THEN 'Breakeven'
                ELSE 'Loss'
            END AS trade_outcome,
            ABS(closing_price - entry_price) AS price_move,
            (closing_price - entry_price)    AS price_delta,
            loaded_at, source_file
        FROM bronze.trades;
    """))

    # Gold: TRUNCATE + rebuild all four tables
    conn.execute(text(
        "TRUNCATE gold.daily_pnl, gold.equity_curve, "
        "gold.trade_type_pnl, gold.performance_metrics RESTART IDENTITY CASCADE;"
    ))

    conn.execute(text("""
        INSERT INTO gold.daily_pnl
        SELECT trade_date, trade_year, trade_month, month_name,
               day_of_week_name, day_of_week_num, iso_week,
               COUNT(*) AS total_trades, SUM(net_pnl) AS daily_pnl,
               SUM(CASE WHEN trade_outcome='Win'       THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN trade_outcome='Loss'      THEN 1 ELSE 0 END) AS losses,
               SUM(CASE WHEN trade_outcome='Breakeven' THEN 1 ELSE 0 END) AS breakevens,
               SUM(CASE WHEN net_pnl>0 THEN net_pnl ELSE 0 END) AS gross_profit,
               SUM(CASE WHEN net_pnl<0 THEN net_pnl ELSE 0 END) AS gross_loss,
               MAX(balance) AS eod_balance
        FROM silver.trades
        GROUP BY 1,2,3,4,5,6,7
        ORDER BY trade_date;
    """))

    conn.execute(text("""
        INSERT INTO gold.equity_curve
        SELECT trade_date, eod_balance,
               MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS peak_balance,
               eod_balance - MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS drawdown_abs,
               ROUND(
                   (eod_balance - MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
                   / NULLIF(MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),0)
                   * 100, 4
               ) AS drawdown_pct,
               SUM(daily_pnl) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_pnl
        FROM gold.daily_pnl ORDER BY trade_date;
    """))

    conn.commit()

print("Silver and Gold layers rebuilt successfully.")
print("=" * 50)
```

---

## 🔤 Power Query M — Silver Enrichment & Date Dimension

### silver_trades Enrichment (Advanced Editor)

```powerquery
let
    Source        = PostgreSQL.Database("localhost", "trading_analytics"),
    silver_trades = Source{[Schema="silver",Item="trades"]}[Data],

    TypedTable = Table.TransformColumnTypes(silver_trades, {
        {"trade_date",           type date},
        {"opening_time",         type datetimezone},
        {"closing_time",         type datetimezone},
        {"trade_year",           Int64.Type},
        {"trade_month",          Int64.Type},
        {"net_pnl",              type number},
        {"balance",              type number},
        {"entry_price",          type number},
        {"closing_price",        type number},
        {"trade_duration_hours", type number}
    }),

    // Day of Week (Mon=1 ... Sun=7)
    AddDOW = Table.AddColumn(TypedTable, "DOW_Number",
        each Date.DayOfWeek([trade_date], Day.Monday) + 1, Int64.Type),

    // Week label for slicers
    AddWeekLabel = Table.AddColumn(AddDOW, "Week_Label",
        each "W" & Text.PadStart(Text.From(Date.WeekOfYear([trade_date])),2,"0"),
        type text),

    // Month-Year label — sorted by Month_Sort to prevent alphabetical ordering
    AddMonthYear = Table.AddColumn(AddWeekLabel, "Month_Year",
        each Date.ToText([trade_date], "MMM yyyy"), type text),

    AddMonthSort = Table.AddColumn(AddMonthYear, "Month_Sort",
        each [trade_year]*100+[trade_month], Int64.Type),

    // Duration cross-check vs PostgreSQL
    AddDuration = Table.AddColumn(AddMonthSort, "Duration_Hours_PQ",
        each Duration.TotalHours(
            DateTimeZone.RemoveZone([closing_time]) -
            DateTimeZone.RemoveZone([opening_time])),
        type number),

    // Trade Type (Duration-Based)
    AddType = Table.AddColumn(AddDuration, "Trade_Type_PQ",
        each if [Duration_Hours_PQ] <= 1  then "Scalp"
             else if [Duration_Hours_PQ] <= 24 then "Intra-Day"
             else "Swing",
        type text),

    // Trade Outcome — threshold-based (matches SQL logic exactly)
    // Win: net_pnl >= balance × 0.005 | Breakeven: net_pnl > 0 | Loss: net_pnl ≤ 0
    AddOutcome = Table.AddColumn(AddType, "Trade_Outcome_PQ",
        each if [net_pnl] >= ([balance] * 0.005) then "Win"
             else if [net_pnl] > 0 then "Breakeven"
             else "Loss",
        type text),

    // Is_Win flag (1 = Win, 0 = not Win)
    AddIsWin = Table.AddColumn(AddOutcome, "Is_Win",
        each if [net_pnl] >= ([balance] * 0.005) then 1 else 0, Int64.Type)

in AddIsWin
```

### Date Dimension Table

```powerquery
let
    StartDate = #date(2026, 1, 1),
    EndDate   = Date.EndOfYear(DateTime.Date(DateTime.LocalNow())),
    DateList  = List.Dates(StartDate, Duration.Days(EndDate-StartDate)+1, #duration(1,0,0,0)),
    DateTable = Table.FromList(DateList, Splitter.SplitByNothing(), {"Date"}),
    TypedDate = Table.TransformColumnTypes(DateTable, {{"Date", type date}}),
    AddYear   = Table.AddColumn(TypedDate, "Year",        each Date.Year([Date]),           Int64.Type),
    AddMonth  = Table.AddColumn(AddYear,   "Month_Num",   each Date.Month([Date]),          Int64.Type),
    AddMName  = Table.AddColumn(AddMonth,  "Month_Name",  each Date.ToText([Date],"MMMM"), type text),
    AddMShort = Table.AddColumn(AddMName,  "Month_Short", each Date.ToText([Date],"MMM"),  type text),
    AddQtr    = Table.AddColumn(AddMShort, "Quarter",     each "Q"&Text.From(Date.QuarterOfYear([Date])), type text),
    AddDOW    = Table.AddColumn(AddQtr,    "Day_Name",    each Date.ToText([Date],"dddd"), type text),
    AddDOWN   = Table.AddColumn(AddDOW,    "Day_Num",     each Date.DayOfWeek([Date],Day.Monday)+1, Int64.Type),
    AddWk     = Table.AddColumn(AddDOWN,   "Week_Num",    each Date.WeekOfYear([Date]),    Int64.Type),
    AddSort   = Table.AddColumn(AddWk,     "Month_Sort",  each [Year]*100+[Month_Num],     Int64.Type)
in AddSort
```

> ⚠️ **Mark as Date Table:** After creating the Date table → Table Tools → Mark as Date Table → select the `Date` column.

---

## 📐 DAX Measures Library

> All measures are stored in a dedicated `_Measures` table. Create it via: Home → Enter Data → name it `_Measures`.
> Color formatting applied via: Format pane → Callout value → Font color → fx → Field value.

### Core KPI Measures

#### Net P&L
```dax
Net P&L =
    CALCULATE(
        SUM(silver_trades[net_pnl]),
        ALLSELECTED(silver_trades)
    )
-- Format: $#,##0.00  |  Color: >= 0 → #2D6A4F (green) | < 0 → #8B1A1A (red)
```

#### Win Rate
```dax
Win Rate =
    VAR _wins  = CALCULATE(COUNTROWS(silver_trades), silver_trades[trade_outcome] = "Win",  ALLSELECTED(silver_trades))
    VAR _total = CALCULATE(COUNTROWS(silver_trades), ALLSELECTED(silver_trades))
    RETURN DIVIDE(_wins, _total, 0)
-- Format: 0.00%  |  Thresholds: >= 55% green | 45-55% amber | < 45% red
-- NOTE: Power BI auto-converts decimals to % in percentage-formatted fields (0.0566 displays as 5.66%)
```

#### Expectancy (R)
```dax
-- 1R = absolute value of the average losing trade (global anchor, unaffected by slicers)
Expectancy (R) =
    VAR _1R = ABS(CALCULATE(
        AVERAGEX(FILTER(silver_trades, silver_trades[trade_outcome] = "Loss"), silver_trades[net_pnl]),
        ALL(silver_trades)))
    VAR _wins    = CALCULATE(COUNTROWS(silver_trades), silver_trades[trade_outcome] = "Win",  ALLSELECTED(silver_trades))
    VAR _losses  = CALCULATE(COUNTROWS(silver_trades), silver_trades[trade_outcome] = "Loss", ALLSELECTED(silver_trades))
    VAR _total   = CALCULATE(COUNTROWS(silver_trades), ALLSELECTED(silver_trades))
    VAR _avgWin  = CALCULATE(AVERAGEX(FILTER(silver_trades, silver_trades[trade_outcome] = "Win"),  silver_trades[net_pnl]), ALLSELECTED(silver_trades))
    VAR _avgLoss = CALCULATE(AVERAGEX(FILTER(silver_trades, silver_trades[trade_outcome] = "Loss"), silver_trades[net_pnl]), ALLSELECTED(silver_trades))
    VAR _winRate  = DIVIDE(_wins,   _total, 0)
    VAR _lossRate = DIVIDE(_losses, _total, 0)
    VAR _avgWinR  = DIVIDE(_avgWin,  _1R, 0)
    VAR _avgLossR = DIVIDE(_avgLoss, _1R, 0)
    RETURN ROUND((_winRate * _avgWinR) + (_lossRate * _avgLossR), 2)
-- Format: #,##0.00"R"  |  > 0 → green | <= 0 → red
```

#### Profit Factor
```dax
Profit Factor =
    VAR _grossProfit = CALCULATE(SUMX(FILTER(silver_trades, silver_trades[net_pnl] > 0), silver_trades[net_pnl]), ALLSELECTED(silver_trades))
    VAR _grossLoss   = ABS(CALCULATE(SUMX(FILTER(silver_trades, silver_trades[net_pnl] < 0), silver_trades[net_pnl]), ALLSELECTED(silver_trades)))
    RETURN ROUND(DIVIDE(_grossProfit, _grossLoss, BLANK()), 2)
-- Format: #,##0.00  |  >= 1.5 green | 1.0-1.5 amber | < 1.0 red
```

#### Avg Trade R
```dax
-- Uses ALL() for a stable 1R denominator unaffected by slicers
-- Green threshold: >= 0.3R
Avg Trade R =
    VAR _1R = ABS(CALCULATE(
        AVERAGEX(FILTER(silver_trades, silver_trades[net_pnl] < 0), silver_trades[net_pnl]),
        ALL(silver_trades)))
    VAR _avgTrade = CALCULATE(AVERAGE(silver_trades[net_pnl]), ALLSELECTED(silver_trades))
    RETURN ROUND(DIVIDE(_avgTrade, _1R, 0), 2)
-- Format: #,##0.00"R"  |  > 0.3 green | 0-0.3 amber | <= 0 red
```

### Risk & Ratio Measures

#### Sharpe Ratio
```dax
-- Daily P&L Sharpe, annualised via √252 (square root of time — random walk of returns)
-- Uses gold_daily_pnl (pre-aggregated rows are faster than row-level silver_trades in STDEVX)
Sharpe Ratio =
    VAR _dailyPnL =
        CALCULATETABLE(
            ADDCOLUMNS(
                VALUES(gold_daily_pnl[trade_date]),
                "DailyPnL", CALCULATE(SUM(gold_daily_pnl[daily_pnl]))
            ),
            ALLSELECTED(gold_daily_pnl)
        )
    VAR _mean  = AVERAGEX(_dailyPnL, [DailyPnL])
    VAR _stdev = STDEVX.S(_dailyPnL, [DailyPnL])
    RETURN ROUND(DIVIDE(_mean, _stdev, BLANK()) * SQRT(252), 2)
-- Format: #,##0.00  |  >= 2 green | 1-2 amber | < 1 red
```

#### Calmar Ratio
```dax
-- Annualised return / Max Drawdown % — return per unit of catastrophic risk
-- Dynamic: looks up the earliest-trade balance rather than using a hardcoded starting value
Calmar Ratio =
    VAR _totalDays = CALCULATE(DISTINCTCOUNT(silver_trades[trade_date]), ALLSELECTED(silver_trades))
    VAR _netPnL    = CALCULATE(SUM(silver_trades[net_pnl]), ALLSELECTED(silver_trades))
    VAR _startBal  =
        CALCULATE(
            FIRSTNONBLANK(silver_trades[balance], 1),
            TOPN(1, ALLSELECTED(silver_trades), silver_trades[opening_time], ASC)
        )
    VAR _annReturn = DIVIDE(_netPnL / _startBal * 252, _totalDays, 0)
    VAR _maxDD =
        CALCULATE(
            ABS(MIN(gold_equity_curve[drawdown_pct])) / 100,
            ALLSELECTED(gold_equity_curve)
        )
    RETURN ROUND(DIVIDE(_annReturn, _maxDD, BLANK()), 2)
-- Format: #,##0.00  |  >= 3 green | 1-3 amber | < 1 red
```

#### Recovery Factor
```dax
Recovery Factor =
    VAR _netPnL = CALCULATE(SUM(silver_trades[net_pnl]), ALLSELECTED(silver_trades))
    VAR _maxDD  = ABS(CALCULATE(MIN(gold_equity_curve[drawdown_abs]), ALLSELECTED(gold_equity_curve)))
    RETURN ROUND(DIVIDE(_netPnL, _maxDD, BLANK()), 2)
-- > 1.0 = net profit exceeded worst drawdown (recovered + earned more)
-- Format: #,##0.00  |  >= 3 green | 1-3 amber | < 1 red
```

### Conditional Color Measures

```dax
-- Consistent three-tier SWITCH(TRUE()) pattern across all color measures
-- Color palette: #2D6A4F (green) | #C9A84C (amber) | #8B1A1A (red)

NetPnL Color =
    IF([Net P&L] >= 0, "#2D6A4F", "#8B1A1A")

WinRate Color =
    SWITCH(TRUE(),
        [Win Rate] >= 0.55, "#2D6A4F",
        [Win Rate] >= 0.45, "#C9A84C",
        "#8B1A1A")

AvgTradeR Color =
    SWITCH(TRUE(),
        [Avg Trade R] >= 0.3, "#2D6A4F",   -- 0.3R = green threshold
        [Avg Trade R] >= 0,   "#C9A84C",
        "#8B1A1A")

DailyPnL Bar Color =
    SWITCH(TRUE(),
        [Daily PnL by DOW] > 0,  "#2D6A4F",
        [Daily PnL by DOW] = 0,  "#C9A84C",
        "#8B1A1A")

RecoveryFactor Color =
    SWITCH(TRUE(),
        [Recovery Factor] >= 3, "#2D6A4F",
        [Recovery Factor] >= 1, "#C9A84C",
        "#8B1A1A")
```

### Dynamic Report Title
```dax
Report Title =
    VAR _minDate = CALCULATE(MIN(silver_trades[trade_date]), ALLSELECTED(silver_trades))
    VAR _maxDate = CALCULATE(MAX(silver_trades[trade_date]), ALLSELECTED(silver_trades))
    RETURN
        "Trading Performance: "
        & FORMAT(_minDate, "DD MMM YYYY")
        & " — "
        & FORMAT(_maxDate, "DD MMM YYYY")
```

---

## 📈 Metric Benchmarks

| Metric | Formula | Good | Excellent |
|---|---|---|---|
| Net P&L | Sum of all net_pnl | > $0 | Consistent monthly |
| Win Rate | Wins / Total Trades | > 45% | > 55% |
| Expectancy (R) | (WR × AvgWin/1R) + (LR × AvgLoss/1R) | > 0R | > 0.25R |
| Profit Factor | Gross Profit / Gross Loss | > 1.0 | > 1.5 |
| Avg Trade (R) | Avg PnL / \|Avg Loss\| | > 0R | > 0.3R |
| Sharpe Ratio | (Avg Daily PnL / StdDev) × √252 | > 1.0 | > 2.0 |
| Calmar Ratio | Ann. Return % / Max Drawdown % | > 1.0 | > 3.0 |
| Max Drawdown | Largest peak-to-trough decline | < 20% | < 10% |
| Recovery Factor | Net P&L / \|Max Drawdown $\| | > 1.0 | > 3.0 |

---

## ⚙️ Power BI Data Model

### Star Schema Relationships

| From Table | From Column | To Table | To Column | Cardinality |
|---|---|---|---|---|
| DimDate | Date | silver_trades | trade_date | 1:N |
| DimDate | Date | gold_daily_pnl | trade_date | 1:N |
| DimDate | Date | gold_equity_curve | trade_date | 1:N |
| silver_trades | trade_date | gold_daily_pnl | trade_date | N:1 |
| silver_trades | trade_type | gold_trade_type_pnl | trade_type | N:1 |

> **Note:** `gold.performance_metrics` is a single-row summary table — connect it as an unrelated table and reference it with `CALCULATE + ALL()` to avoid cross-filtering.

### Canvas & Theme Settings

```
Canvas: 1920 × 1080 px  |  Background: #0D1B2A
Theme Font: Segoe UI    |  Primary: #1B4F8A  |  Accent: #C9A84C
```

---

## 🔄 Refresh Pipeline Checklist

```
1. Export new trades from broker platform → trades.xlsx
2. Run: python etl_pipeline.py
   └── Bronze: append-only (deduplication by order_id)
   └── Silver: TRUNCATE + full rebuild
   └── Gold:   TRUNCATE + full rebuild (all 4 tables)
3. Open Power BI Desktop → Home → Refresh
4. Publish to Power BI Service (optional)
```

> 💡 **Automated Refresh:** Configure a scheduled refresh via Power BI Service using the On-Premises Data Gateway connected to your local PostgreSQL instance (`trading_analytics` database).

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Source Data | Microsoft Excel (trades.xlsx) |
| Database | PostgreSQL 15+ |
| ETL Language | Python 3.x (pandas, SQLAlchemy, psycopg2) |
| Transformation | Power Query M |
| Analytics | DAX (Data Analysis Expressions) |
| Visualisation | Microsoft Power BI Desktop |
| Architecture | Medallion Lakehouse (Bronze / Silver / Gold) |

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 👤 Author

**Isaac Odusanya**
*Trader | Trading Data Analyst*

[![GitHub](https://img.shields.io/badge/GitHub-Datuned-181717?style=flat-square&logo=github)](https://github.com/Datuned)

---

<div align="center">

*Built with precision. Designed for institutional-grade insight.*

</div>
