-- PHANTOM Unified Schema

-- 1. Table for Backtest Runs
CREATE TABLE IF NOT EXISTS backtest_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL UNIQUE,
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Table for Backtest Individual Trades
CREATE TABLE IF NOT EXISTS backtest_trades (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES backtest_runs(run_id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL,
    bias TEXT NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    entry_price REAL NOT NULL,
    exit_price REAL,
    sl_price REAL,
    tp1 REAL,
    tp2 REAL,
    tp3 REAL,
    pnl_points REAL,
    pnl_percent REAL,
    outcome TEXT,
    duration_minutes INTEGER,
    max_favorable_excursion REAL,
    max_adverse_excursion REAL
);

-- 3. Table for Live/Pending Setups
CREATE TABLE IF NOT EXISTS phantom_setups (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    security_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL,
    bias TEXT,
    bias_tf TEXT,
    pattern_tf TEXT,
    entry_tf TEXT,
    state TEXT NOT NULL,
    sweep_type TEXT,
    sweep_price REAL,
    fvg_top REAL,
    fvg_bottom REAL,
    entry_price REAL,
    sl REAL,
    entry_type TEXT,
    tp1 REAL,
    tp2 REAL,
    tp3 REAL,
    rr REAL,
    outcome TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Table for Candle Caching
CREATE TABLE IF NOT EXISTS candles (
    id SERIAL PRIMARY KEY,
    security_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    tf TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume BIGINT,
    timestamp TIMESTAMPTZ NOT NULL,
    UNIQUE(security_id, tf, timestamp)
);

-- Indicies for performance
CREATE INDEX IF NOT EXISTS idx_backtest_trades_run_id ON backtest_trades(run_id);
CREATE INDEX IF NOT EXISTS idx_candles_security_ts ON candles(security_id, tf, timestamp);
