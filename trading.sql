--Three schema medallion pattern
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS bronze.trades(
    id  SERIAL PRIMARY KEY,
    order_id    TEXT,
    symbol  TEXT,
    opening_direction   TEXT,
    closing_direction   TEXT,
    opening_time_raw    TEXT, --stored as text: preserves ms precision.
    closing_time_raw    TEXT, --stored as text: preserves ms precision.
    entry_price NUMERIC(12,5),
    closing_price   NUMERIC(12,5),
    closing_quantity    NUMERIC(10,4),
    closing_volume  NUMERIC(10,4),
    closing_volume_usd  NUMERIC(14,4),
    swap    NUMERIC(10,4),
    commission   NUMERIC(10,4),
    gross_pnl   NUMERIC(12,4),
    net_pnl NUMERIC(12,4),
    balance NUMERIC(14,4),
    pips    NUMERIC(10,4),
    requested_quantity   NUMERIC(10,4),
    channel TEXT,
    label   TEXT,
    comment TEXT,
    loaded_at   TIMESTAMPTZ DEFAULT NOW(),
    source_file TEXT DEFAULT 'trades.xlsx'
);

CREATE TABLE IF NOT EXISTS silver.trades AS 
SELECT
    id,
    order_id,
    symbol,
    TRIM(opening_direction) AS direction,
    TRIM(closing_direction) AS closing_direction,

    --Parse both timestamps (DD/MM/YYYY HH24:MI:SS.MS format)
    TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ
    AS opening_time,
    TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')::TIMESTAMPTZ
    AS closing_time,
    entry_price,
    closing_price,
    closing_quantity,
    closing_volume,
    swap,
    commission,
    gross_pnl,
    net_pnl,
    balance,
    pips,
    channel,

    --DATE DIMENSIONS (From opening time)

    DATE(TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_date,
    EXTRACT(YEAR FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_year,
    EXTRACT(MONTH FROM TO_TIMESTAMP(opening_time_raw, 'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_month,
    TO_CHAR(TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'),'Month') AS month_name,
    EXTRACT(DOW FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS day_of_week_num,--0=Sun
    TO_CHAR(TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'),'Day') AS day_of_week_name,
    EXTRACT(WEEK FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS iso_week,
    EXTRACT(QUARTER FROM TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')) AS trade_quarter,

    --TRADE DURATION IN HOURS(opening time to closing time)

    ROUND(
        EXTRACT(
            EPOCH FROM( TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')-TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS'))
            )/3600.0, 4
    ) AS trade_duration_hours,

--TRADE TYPE: DURATION BASED

CASE
    WHEN EXTRACT(EPOCH FROM (
        TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')-
        TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')
    )
    )/3600.0 <=1 THEN 'Scalp'
    WHEN EXTRACT(
        EPOCH FROM(
            TO_TIMESTAMP(closing_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')-
            TO_TIMESTAMP(opening_time_raw,'DD/MM/YYYY HH24:MI:SS.MS')
        )
    )/3600.0 <=24 THEN 'Intra-Day'
    ELSE 'Swing'
END AS trade_type,

    /*
    trade_outcome Flag (threshold-based: 0.5% of account balance)
    Win:        net_pnl >= 0.5% of balance (meaningful gain)
    Breakeven:  net_pnl > 0 but < 0.5% of balance (marginal gain)
    Loss:       net_pnl < 0
    */
    CASE 
        WHEN net_pnl >=(balance *0.005) THEN 'Win'
        WHEN net_pnl>0 THEN 'Breakeven'
        ELSE 'Loss'
    END AS trade_trade_outcome,
    ABS(closing_price - entry_price) AS price_move,
    (closing_price - entry_price) AS price_delta,
    loaded_at,
    source_file

    FROM bronze.trades;

--PRIMARY KEY AND PERFORMANCE INDEXS.

ALTER TABLE silver.trades ADD PRIMARY KEY (id);
CREATE INDEX idx_silver_trade_date ON silver.trades(trade_date);
CREATE INDEX idx_silver_direction ON silver.trades(direction);
CREATE INDEX idx_silver_trade_trade_outcome ON silver.trades(trade_trade_outcome);
CREATE INDEX idx_silver_trade_type ON silver.trades(trade_type);
CREATE INDEX idx_silver_trade_duration_hours ON silver.trades(trade_duration_hours);
CREATE INDEX idx_silver_year_month ON silver.trades(trade_year,trade_month);

CREATE TABLE gold.daily_pnl AS
SELECT
    trade_date, trade_year, trade_month, month_name, 
    day_of_week_name, day_of_week_num, iso_week,
    COUNT(*) AS total_trades,
    SUM(net_pnl) AS daily_pnl,
    SUM(CASE WHEN trade_outcome='Win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN trade_outcome='Loss' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN trade_outcome='Breakeven' THEN 1 ELSE 0 END) AS breakevens,
    SUM(CASE WHEN net_pnl>0 THEN net_pnl ELSE 0 END) AS gross_profit,
    SUM(CASE WHEN net_pnl<0 THEN net_pnl ELSE 0 END) AS gross_loss,
    MAX(balance) AS eod_balance

    FROM silver.trades
    GROUP BY 1,2,3,4,5,6,7
    ORDER BY trade_date;

    CREATE TABLE gold.equity_curve AS
    SELECT
        trade_date,
        eod_balance,
    --HIGH WATER MARK
    MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    AS peak_balance,

    --DRAWDOWN IN $
    eod_balance - MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    AS drawdown_abs,

    --DRAWDOWN %
    ROUND(
        (eod_balance - MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        
        )/NULLIF(MAX(eod_balance) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),0)
    *100,4
    ) AS drawdown_pct,

    --CUMMULATIVE PNL

    SUM(daily_pnl) OVER(ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    AS cummulative_pnl
    FROM gold.daily_pnl
    ORDER BY trade_date;

CREATE TABLE gold.trade_type_pnl AS
SELECT
    trade_type,
    COUNT(*) AS total_trades,
    SUM(net_pnl) AS total_pnl,
    SUM(CASE WHEN trade_outcome='Win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN trade_ouTcome='Loss' THEN 1 ELSE 0 END) AS losses,
    ROUND(SUM(CASE WHEN trade_outcome='Win' THEN 1 ELSE 0 END)::NUMERIC
    /NULLIF(COUNT(*),0)*100, 2) AS win_rate_pct,
    ROUND(AVG(net_pnl),4) AS avg_pnl,
    ROUND(SUM(CASE WHEN net_pnl>0 THEN net_pnl ELSE 0 END)/
         NULLIF(ABS(SUM(CASE WHEN net_pnl<0 THEN net_pnl ELSE 0 END)),0)
         ,4
    ) AS profit_factor

    FROM silver.trades
    GROUP BY trade_type
    ORDER BY trade_type;

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
    ROUND(b.wins::NUMERIC / NULLIF(b.total_trades, 0) * 100, 2)
                                                        AS win_rate_pct,

    -- Profit Factor
    ROUND(b.gross_profit::NUMERIC / NULLIF(b.gross_loss::NUMERIC, 0), 4)
                                                        AS profit_factor,

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
        ),
        4
    )                                                   AS expectancy_r,

    -- Average Trade P&L
    ROUND(b.avg_trade_pnl::NUMERIC, 4)                  AS avg_trade_pnl,

    -- Sharpe Ratio (annualised, 252 trading days)
    ROUND(
        (d.avg_daily_pnl::NUMERIC / NULLIF(d.stddev_daily_pnl::NUMERIC, 0))
        * SQRT(252)::NUMERIC,
        4
    )                                                   AS sharpe_ratio,

    -- Calmar Ratio = Annualised Return / |Max Drawdown %|
    ROUND(
        (
            (b.net_pnl::NUMERICy / 10000.0)
            * 252
            / NULLIF(td.trading_days::NUMERIC, 0)
        )
        / NULLIF(ABS(dd.max_drawdown_pct::NUMERIC) / 100.0, 0),
        4
    )                                                   AS calmar_ratio,

    -- Recovery Factor = Net P&L / |Max Drawdown $|
    ROUND(
        b.net_pnl::NUMERIC / NULLIF(ABS(dd.max_drawdown_abs::NUMERIC), 0),
        4
    )                                                   AS recovery_factor,

    dd.max_drawdown_pct,
    dd.max_drawdown_abs        

FROM base b
CROSS JOIN daily d
CROSS JOIN dd
CROSS JOIN td;







