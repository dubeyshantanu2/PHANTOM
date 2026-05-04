# Module backtest.data_loader

backtest/data_loader.py

Fetches historical OHLCV data from Dhan API for all timeframes
required by the active mode. Caches results to local CSV files to
avoid repeat API calls on re-runs.

Cache location: backtest/cache/<security_id>_<tf>_<from>_<to>.csv

## Class `Candle`
Represents a single OHLCV candle.

### Method `__init__`
## Function `clear_cache`
Delete all cached CSV files for a given security ID.

Args:
    security_id: The Dhan security ID whose cache to clear.

## Function `load_historical`
Load all required timeframes for the given mode and date range.
Checks CSV cache first; fetches from Dhan API on cache miss.

Args:
    dhan_client: Authenticated DhanHQ client.
    instrument: InstrumentConfig for the security.
    mode: Active mode string — SCALPER | SWING | BOTH.
    from_date: Backtest start date.
    to_date: Backtest end date (inclusive).

Returns:
    Dict mapping timeframe string to list of Candle objects.
    e.g. {"1m": [...], "5m": [...], "15m": [...], "1h": [...]}

