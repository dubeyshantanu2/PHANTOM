# Module backtest.simulator

backtest/simulator.py

Replays historical candles through the same core pipeline modules
used in live mode. Tracks entry/exit/SL/TP for each setup and
produces a list of BacktestTrade objects.

No Discord alerts are sent. No Supabase writes during replay.

## Class `BacktestSimulator`
Replays historical candles tick-by-tick through the core PHANTOM pipeline.

The simulator shares the exact same detection logic as live mode
by importing and calling core modules directly.

Args:
    instrument (InstrumentConfig): Configuration for the security under test.
    mode (str): Active mode (SCALPER, SWING, or BOTH).
    candles_by_tf (Dict[str, List[Candle]]): historical data grouped by timeframe.

### Method `__init__`
### Method `run`
Run the full replay over all historical candles.

Uses the 1m candle stream as the master clock for SCALPER,
and 5m for SWING-only mode.

Returns:
    List[BacktestTrade]: All completed trades from the simulation.

## Class `BacktestStats`
Aggregate statistics for a completed backtest run.

Attributes:
    symbol (str): Trading symbol.
    security_id (int): Security ID of the instrument.
    mode (str): Active trading mode.
    from_date (str): Start date of the backtest.
    to_date (str): End date of the backtest.
    total_setups (int): Total number of valid setups identified.
    total_trades (int): Total number of trades executed.
    winners (int): Number of winning trades.
    losers (int): Number of losing trades.
    expired (int): Number of trades that expired.
    win_rate (float): Percentage of winning trades.
    avg_rr (float): Average reward-to-risk ratio.
    total_pnl_points (float): Aggregate PnL in points.
    max_drawdown_points (float): Maximum peak-to-trough drawdown.
    best_trade_points (float): PnL of the best trade.
    worst_trade_points (float): PnL of the worst trade.
    profit_factor (float): Ratio of gross wins to gross losses.
    avg_win_points (float): Average points gained on winners.
    avg_loss_points (float): Average points lost on losers.
    trades_per_day (float): Average trades executed per day.
    scalper_stats (dict): Performance breakdown for scalper mode.
    swing_stats (dict): Performance breakdown for swing mode.

### Method `__init__`
## Class `BacktestTrade`
Represents a single completed backtest trade.

Attributes:
    trade_id (str): Unique identifier for the trade.
    mode (str): Trading mode, either 'SCALPER' or 'SWING'.
    symbol (str): Trading symbol.
    security_id (int): Security ID of the instrument.
    direction (str): Trade direction, 'LONG' or 'SHORT'.
    entry_time (datetime): Time of trade entry.
    entry_price (float): Execution price at entry.
    exit_time (Optional[datetime]): Time of trade exit.
    exit_price (Optional[float]): Execution price at exit.
    sl (float): Stop-loss price.
    tp1 (float): Take-profit target 1.
    tp2 (float): Take-profit target 2.
    tp3 (float): Take-profit target 3.
    outcome (str): Final outcome of the trade (e.g., 'TP1', 'SL').
    rr_achieved (float): Reward-to-risk ratio achieved.
    pnl_points (float): Profit and loss in points.
    setup_id (str): Reference to the original setup identifier.

### Method `__init__`
## Class `RollingBuffer`
Fixed-size deque that exposes the latest N candles as a list.

Args:
    maxlen (int): Maximum size of the buffer.

### Method `__init__`
### Method `append`
Add a new candle to the rolling buffer.

### Method `to_list`
Convert the buffer to a standard Python list.

