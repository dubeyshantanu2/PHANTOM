# Module backtest.engine

backtest/engine.py

Orchestrates a full PHANTOM backtest run:
  1. Loads historical data via data_loader
  2. Runs the simulator
  3. Computes BacktestStats
  4. Persists results to Supabase
  5. Triggers HTML report generation

## Class `BacktestEngine`
Top-level orchestrator for a PHANTOM backtest run.

Args:
    instrument (InstrumentConfig): Resolved instrument configuration.
    mode (str): Active mode (SCALPER, SWING, or BOTH).
    from_date (date): Backtest start date.
    to_date (date): Backtest end date.
    open_report (bool): Whether to auto-open the HTML report in the browser.

### Method `__init__`
### Method `run`
Execute the full backtest pipeline.

Returns:
    BacktestStats: Computed metrics for the entire run.

