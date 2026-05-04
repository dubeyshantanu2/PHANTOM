# Module backtest.report

backtest/report.py

Generates a self-contained single-file HTML backtest report.
Uses Chart.js (CDN) for all charts. No external dependencies needed
to view the report — open the .html file in any browser.

Output: backtest/reports/{symbol}_{from}_{to}_{mode}_{run_id[:8]}.html

## Function `generate_report`
Generate a self-contained HTML backtest report and save it to disk.

Args:
    stats (BacktestStats): Computed BacktestStats.
    trades (List[BacktestTrade]): All BacktestTrade objects from the simulator.
    run_id (str): UUID string for this run (used in filename).

Returns:
    str: Absolute path to the generated HTML file.

