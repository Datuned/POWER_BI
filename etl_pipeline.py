import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine(
    "postgresql://postgres:skaihawk@localhost:5432/trading_analytics"
)

# Read new Excel file
df_new = pd.read_excel("trades.xlsx", sheet_name="Records")

# Map all 21 source columns

df_new.columns = [
    "order_id",
    "symbol",
    "opening_direction",
    "closing_direction",
    "opening_time_raw",
    "closing_time_raw",
    "entry_price",
    "closing_price",
    "closing_quantity",
    "closing_volume",
    "closing_volume_usd",
    "swap",
    "commission",
    "gross_pnl",
    "net_pnl",
    "balance",
    "pips",
    "requested_quantity",
    "channel",
    "label",
    "comment",
]

# Read order_ids already in bronze (already loaded trades)
existing = pd.read_sql("SELECT order_id FROM bronze.trades", engine)

# Separate new trades from duplicates
is_duplicate = df_new["order_id"].isin(existing["order_id"])
is_new = ~is_duplicate

df_new_only = df_new[is_new]
df_duplicates = df_new[is_duplicate]

# Counts-----------------------
total_in_file = len(df_new)
total_in_database = len(existing)
total_new = len(df_new_only)
total_duplicates = len(df_duplicates)

# -----------Detailed Report---------------------
print("=" * 50)
print("     ETL PIPELINE PRELOAD REPORT")
print("=" * 50)
print(f"Trades in  new Excel file   : {total_in_file}")
print(f"Trades already in database  : {total_in_database}")
print(f"Genuinely new trade found   : {total_new}")
print(f"Duplicates skipped          : {total_duplicates}")
print("=" * 50)

# Guard If nothing new to load----------------
if total_new == 0:
    print("STATUS: No new trades found.")
    print("        Database is already up to date.")
    print("        Nothing was loaded.")
    print("=" * 50)
# ---Guard all trades are new 0 duplicates--------------------
elif total_duplicates == 0:
    print("STATUS: All trades in the file are new")
    print("        No duplicates detected.")

    df_new_only = df_new_only.copy()

    df_new_only["opening_time_raw"] = df_new_only["opening_time_raw"].astype(str)

    df_new_only["closing_time_raw"] = df_new_only["closing_time_raw"].astype(str)

    df_new_only.to_sql(
        "trades", engine, schema="bronze", if_exists="append", index=False
    )
    print(f"        {total_new} trades loaded into bronze.trades.")
    print("=" * 50)
else:
    print("STATUS: Mix of new and duplicate trades detected.")
    df_new_only["opening_time_raw"] = df_new_only["opening_time_raw"].astype(str)
    df_new_only["closing_time_raw"] = df_new_only["closing_time_raw"].astype(str)

    df_new_only.to_sql(
        "trades", engine, schema="bronze", if_exists="append", index=False
    )
    print(f"        {total_new} trades loaded into bronze.trades.")
    print(f"        {total_duplicates} duplicates safely skipped.")
    print("=" * 50)

# Final database count confirmation.
final_count = pd.read_sql("SELECT COUNT(*) AS total FROM bronze.trades", engine)
print(f"Bronze total after load     : {final_count['total'].values[0]}")
print("=" * 50)

# Refresh Silver and Gold.
with engine.connect() as conn:
    conn.execute(text("TRUNCATE silver.trades RESTART IDENTITY CASCADE"))

    # -----Rebuild Silver from Bronze.
    conn.execute(text("""
        INSERT INTO silver.trades
                      SELECT
                      id,
                      order_id,
                      symbol,
                      TRIM(opening_direction) AS direction,
                      TRIM(closing_direction) AS closing_direction,

                      TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ AS opening_time,
                      TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ AS closing_time,

                      entry_price,
                      closing_price,
                      closing_quantity,
                      closing_volume,
                      closing_volume_usd,
                      swap,
                      commission,
                      gross_pnl,
                      net_pnl,
                      balance,
                      pips,
                      channel,
                      DATE(TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ))                                               AS trade_date,

                EXTRACT(YEAR FROM TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ))                                               AS trade_year,

                EXTRACT(MONTH FROM TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ))                                               AS trade_month,

                TO_CHAR(TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ),'Month')                                       AS month_name,

                EXTRACT(DOW FROM TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ))                                               AS day_of_week_num,

                TO_CHAR(TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ),'Day')                                         AS day_of_week_name,

                EXTRACT(WEEK FROM TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ))                                               AS iso_week,

                EXTRACT(QUARTER FROM TO_TIMESTAMP(
                    closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                ))                                               AS trade_quarter,

                -- Trade Duration in Hours
                ROUND(
                    EXTRACT(EPOCH FROM (
                        TO_TIMESTAMP(
                            closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                        ) -
                        TO_TIMESTAMP(
                            opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                        )
                    )) / 3600.0, 4
                )                                                AS trade_duration_hours,

                -- Session Type: Duration-Based
                CASE
                    WHEN EXTRACT(EPOCH FROM (
                        TO_TIMESTAMP(
                            closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                        ) -
                        TO_TIMESTAMP(
                            opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                        )
                    )) / 3600.0 <= 1  THEN 'Scalp'
                    WHEN EXTRACT(EPOCH FROM (
                        TO_TIMESTAMP(
                            closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                        ) -
                        TO_TIMESTAMP(
                            opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'
                        )
                    )) / 3600.0 <= 24 THEN 'Intra-Day'
                    ELSE 'Swing'
                END                                              AS session_type,

                -- Outcome Flag 
                CASE
                    WHEN net_pnl >= (balance * 0.005) THEN 'Win'
                    WHEN net_pnl > 0                  THEN 'Breakeven'
                    ELSE                                   'Loss'
                END                                              AS outcome,

                ABS(closing_price - entry_price)                 AS price_move,
                (closing_price - entry_price)                    AS price_delta,
                loaded_at,
                source_file

            FROM bronze.trades;

                   
"""))
    # ── Step 3: Erase all Gold tables ─────────────────────────────
    conn.execute(
        text(
            "TRUNCATE gold.daily_pnl, gold.equity_curve, "
            "gold.session_pnl, gold.performance_metrics "
            "RESTART IDENTITY CASCADE;"
        )
    )

    # ── Step 4: Rebuild gold.daily_pnl ────────────────────────────
    conn.execute(text("""
            INSERT INTO gold.daily_pnl
            SELECT
                trade_date,
                trade_year,
                trade_month,
                month_name,
                day_of_week_name,
                day_of_week_num,
                iso_week,
                COUNT(*)                                         AS total_trades,
                SUM(net_pnl)                                     AS daily_pnl,
                SUM(CASE WHEN outcome = 'Win'
                    THEN 1 ELSE 0 END)                           AS wins,
                SUM(CASE WHEN outcome = 'Loss'
                    THEN 1 ELSE 0 END)                           AS losses,
                SUM(CASE WHEN outcome = 'Breakeven'
                    THEN 1 ELSE 0 END)                           AS breakevens,
                SUM(CASE WHEN net_pnl > 0
                    THEN net_pnl ELSE 0 END)                     AS gross_profit,
                SUM(CASE WHEN net_pnl < 0
                    THEN net_pnl ELSE 0 END)                     AS gross_loss,
                MAX(balance)                                     AS eod_balance
            FROM silver.trades
            GROUP BY 1,2,3,4,5,6,7
            ORDER BY trade_date;
        """))

    # ── Step 5: Rebuild gold.equity_curve ─────────────────────────
    conn.execute(text("""
            INSERT INTO gold.equity_curve
            SELECT
                trade_date,
                eod_balance,
                MAX(eod_balance) OVER (
                    ORDER BY trade_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )                                                AS peak_balance,
                eod_balance - MAX(eod_balance) OVER (
                    ORDER BY trade_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )                                                AS drawdown_abs,
                ROUND(
                    (eod_balance - MAX(eod_balance) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )) / NULLIF(MAX(eod_balance) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ), 0) * 100, 4
                )                                                AS drawdown_pct,
                SUM(daily_pnl) OVER (
                    ORDER BY trade_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )                                                AS cumulative_pnl
            FROM gold.daily_pnl
            ORDER BY trade_date;
        """))

    # ── Step 6: Rebuild gold.session_pnl ──────────────────────────
    conn.execute(text("""
            INSERT INTO gold.session_pnl
            SELECT
                session_type,
                COUNT(*)                                         AS total_trades,
                SUM(net_pnl)                                     AS total_pnl,
                SUM(CASE WHEN outcome = 'Win'
                    THEN 1 ELSE 0 END)                           AS wins,
                SUM(CASE WHEN outcome = 'Loss'
                    THEN 1 ELSE 0 END)                           AS losses,
                ROUND(
                    SUM(CASE WHEN outcome = 'Win'
                        THEN 1 ELSE 0 END)::NUMERIC
                    / NULLIF(COUNT(*), 0) * 100, 2
                )                                                AS win_rate_pct,
                ROUND(AVG(net_pnl), 4)                           AS avg_pnl,
                ROUND(
                    SUM(CASE WHEN net_pnl > 0
                        THEN net_pnl ELSE 0 END) /
                    NULLIF(ABS(SUM(CASE WHEN net_pnl < 0
                        THEN net_pnl ELSE 0 END)), 0), 4
                )                                                AS profit_factor
            FROM silver.trades
            GROUP BY session_type
            ORDER BY session_type;
        """))

    # ── Step 7: Rebuild gold.performance_metrics ──────────────────
    conn.execute(text("""
            INSERT INTO gold.performance_metrics
            WITH base AS (
                SELECT
                    COUNT(*)                                     AS total_trades,
                    SUM(net_pnl)                                 AS net_pnl,
                    SUM(CASE WHEN outcome = 'Win'
                        THEN 1 ELSE 0 END)                       AS wins,
                    SUM(CASE WHEN outcome = 'Loss'
                        THEN 1 ELSE 0 END)                       AS losses,
                    SUM(CASE WHEN outcome = 'Breakeven'
                        THEN 1 ELSE 0 END)                       AS breakevens,
                    SUM(CASE WHEN net_pnl > 0
                        THEN net_pnl ELSE 0 END)                 AS gross_profit,
                    ABS(SUM(CASE WHEN net_pnl < 0
                        THEN net_pnl ELSE 0 END))                AS gross_loss,
                    AVG(net_pnl)                                 AS avg_trade_pnl,
                    AVG(CASE WHEN net_pnl > 0
                        THEN net_pnl END)                        AS avg_win,
                    AVG(CASE WHEN net_pnl < 0
                        THEN net_pnl END)                        AS avg_loss
                FROM silver.trades
            ),
            daily AS (
                SELECT
                    AVG(daily_pnl)         AS avg_daily_pnl,
                    STDDEV_SAMP(daily_pnl) AS stddev_daily_pnl
                FROM gold.daily_pnl
            ),
            dd AS (
                SELECT
                    MIN(drawdown_pct) AS max_drawdown_pct,
                    MIN(drawdown_abs) AS max_drawdown_abs
                FROM gold.equity_curve
            ),
            td AS (
                SELECT COUNT(DISTINCT trade_date) AS trading_days
                FROM silver.trades
            )
            SELECT
                b.total_trades,
                b.net_pnl,
                b.wins,
                b.losses,
                b.breakevens,
                b.gross_profit,
                b.gross_loss,

                -- Win Rate
                ROUND(
                    b.wins::NUMERIC / NULLIF(b.total_trades, 0) * 100, 2
                )                                                AS win_rate_pct,

                -- Profit Factor
                ROUND(
                    b.gross_profit::NUMERIC /
                    NULLIF(b.gross_loss::NUMERIC, 0), 4
                )                                                AS profit_factor,

                -- Expectancy (R-Multiples)
                ROUND(
                    (
                        (b.wins::NUMERIC / NULLIF(b.total_trades, 0))
                        * COALESCE(b.avg_win::NUMERIC, 0)
                        / NULLIF(ABS(b.avg_loss::NUMERIC), 0)
                    )
                    +
                    (
                        (b.losses::NUMERIC / NULLIF(b.total_trades, 0))
                        * COALESCE(b.avg_loss::NUMERIC, 0)
                        / NULLIF(ABS(b.avg_loss::NUMERIC), 0)
                    ), 4
                )                                                AS expectancy_r,

                -- Average Trade P&L
                ROUND(b.avg_trade_pnl::NUMERIC, 4)               AS avg_trade_pnl,

                -- Sharpe Ratio (annualised, 252 trading days)
                ROUND(
                    (d.avg_daily_pnl::NUMERIC /
                    NULLIF(d.stddev_daily_pnl::NUMERIC, 0))
                    * SQRT(252)::NUMERIC, 4
                )                                                AS sharpe_ratio,

                -- Calmar Ratio
                ROUND(
                    (
                        (b.net_pnl::NUMERIC / 10000.0)
                        * 252
                        / NULLIF(td.trading_days::NUMERIC, 0)
                    )
                    / NULLIF(ABS(dd.max_drawdown_pct::NUMERIC) / 100.0, 0),
                    4
                )                                                AS calmar_ratio,

                -- Recovery Factor
                ROUND(
                    b.net_pnl::NUMERIC /
                    NULLIF(ABS(dd.max_drawdown_abs::NUMERIC), 0), 4
                )                                                AS recovery_factor,

                dd.max_drawdown_pct,
                dd.max_drawdown_abs

            FROM base b
            CROSS JOIN daily d
            CROSS JOIN dd
            CROSS JOIN td;
        """))

    # ── Commit all changes ─────────────────────────────────────────
    conn.commit()

    # ── Final confirmation ─────────────────────────────────────────────
    print("=" * 50)
    print("        ETL PIPELINE — POST-LOAD REPORT")
    print("=" * 50)

    bronze_count = pd.read_sql("SELECT COUNT(*) AS total FROM bronze.trades", engine)
    silver_count = pd.read_sql("SELECT COUNT(*) AS total FROM silver.trades", engine)
    gold_daily_count = pd.read_sql(
        "SELECT COUNT(*) AS total FROM gold.daily_pnl", engine
    )

    print(f"Bronze total after load     : {bronze_count['total'].values[0]}")
    print(f"Silver total after rebuild  : {silver_count['total'].values[0]}")
    print(f"Gold daily_pnl rows         : {gold_daily_count['total'].values[0]}")
    print("Silver and Gold layers rebuilt successfully.")
    print("=" * 50)
