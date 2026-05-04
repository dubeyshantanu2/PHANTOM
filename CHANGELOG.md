# Changelog

All notable changes to the PHANTOM project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Tick Collision**: Added a `_is_ticking` guard to the scheduled jobs in `main.py` to prevent concurrent execution of pipeline ticks across different timeframes if one tick overlaps into the schedule of another.
- **Session Setup Count**: Fixed a bug where `setup_count` was always 0 in the session-end alert by summing the setups directly from the `ModeController` pipelines instead of calling the non-existent `get_setup_count()` method.
- **CLI Parsing**: Replaced custom `sys.argv` parsing with standard `argparse`. Added explicit `--id` and `--mode` arguments to fix the broken `--<id>` syntax.

## [1.1.0] - 2026-04-18

### Added
- **Backtesting Engine**: High-performance market replay system for historical strategy evaluation.
- **Backtest Simulator**: Tick-by-tick (1-minute) simulation of price action through the same core engines used in live mode.
- **Interactive Reports**: Self-contained HTML reports with Chart.js visualization, equity curves, drawdown analysis, and trade breakdown.
- **Historical Data Loader**: Asynchronous data ingestion with local caching support for NSE and MCX instruments.
- **Supabase Integration**: Persistence of backtest runs and individual trade metrics for longitudinal performance tracking.
- **CLI Support**: New arguments for backtesting (`--backtest`, `--from`, `--to`, `--days`, `--report`).

### Changed
- **Dashboard Design**: Premium dark-mode styling for backtest reports with dynamic charts and sortable trade tables.
- **Simulator Logic**: Fixed HTF synchronization bugs and added intraday auto-square-off logic.

## [1.0.0] - 2026-04-18

### Added
- Initial release of PHANTOM (Price Hunt And Market Trap Observation Node).
- Core engines: Bias, Candle, Entry, FVG, Liquidity, Mode Controller, Setup Validator, Sweep Detector, and Target Resolver.
- Data integration with Dhan HQ API.
- Persistence layer using Supabase.
- Discord alerting system for session updates and trading setups.
- Multi-timeframe support (1m, 5m, 15m, 1h).
- Support for Indian markets (NSE + MCX).
- **Project Structure**: Comprehensive `.gitignore` to maintain a clean repository.

### Security
- Environment variable based configuration for sensitive API keys and secrets.
