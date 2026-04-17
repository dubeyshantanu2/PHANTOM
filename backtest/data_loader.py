"""
backtest/data_loader.py

Fetches historical OHLCV data from Dhan API for all timeframes
required by the active mode. Caches results to local CSV files to
avoid repeat API calls on re-runs.

Cache location: backtest/cache/<security_id>_<tf>_<from>_<to>.csv
"""

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import pytz

from config import InstrumentConfig

logger = logging.getLogger("PHANTOM.backtest.data_loader")

IST = pytz.timezone("Asia/Kolkata")

# Directory where CSV cache files are stored
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# Dhan API interval map: TF string → interval integer
TF_TO_INTERVAL = {
    "1m":  1,
    "5m":  5,
    "15m": 15,
    "1h":  60,
}

# TFs required per mode
MODE_TF_MAP = {
    "SCALPER": ["1m", "5m", "15m"],
    "SWING":   ["5m", "15m", "1h"],
    "BOTH":    ["1m", "5m", "15m", "1h"],
}


@dataclass
class Candle:
    """Represents a single OHLCV candle."""
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    int
    timestamp: datetime


def _resolve_exchange_params(instrument: InstrumentConfig):
    """
    Returns (exchange_segment, instrument_type) tuple for Dhan API
    based on the instrument config.

    Args:
        instrument: InstrumentConfig for the security.

    Returns:
        Tuple of (exchange_segment str, instrument_type str).
    """
    INDEX_SYMBOLS = {"NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}

    if instrument.symbol.upper() in INDEX_SYMBOLS:
        return "IDX_I", "INDEX"
    elif instrument.is_commodity:
        return "MCX", "COMMODITY"
    else:
        return instrument.exchange, "EQUITY"


def _cache_path(security_id: int, tf: str, from_date: date, to_date: date) -> str:
    """Build the full path to a cache CSV file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    filename = f"{security_id}_{tf}_{from_date}_{to_date}.csv"
    return os.path.join(CACHE_DIR, filename)


def _load_from_cache(path: str) -> Optional[List[Candle]]:
    """
    Load candles from a CSV cache file if it exists.

    Args:
        path: Full path to the cache CSV.

    Returns:
        List of Candle objects or None if cache miss.
    """
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["timestamp"])
        candles = []
        for _, row in df.iterrows():
            ts = row["timestamp"]
            if ts.tzinfo is None:
                ts = IST.localize(ts)
            candles.append(Candle(
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                timestamp=ts,
            ))
        logger.info(f"[CACHE HIT] Loaded {len(candles)} candles from {os.path.basename(path)}")
        return candles
    except Exception as e:
        logger.warning(f"Cache read failed for {path}: {e} — will re-fetch")
        return None


def _save_to_cache(candles: List[Candle], path: str) -> None:
    """
    Save a list of candles to a CSV cache file.

    Args:
        candles: List of Candle objects to save.
        path: Full path to write the CSV.
    """
    rows = [{
        "timestamp": c.timestamp.isoformat(),
        "open":      c.open,
        "high":      c.high,
        "low":       c.low,
        "close":     c.close,
        "volume":    c.volume,
    } for c in candles]
    pd.DataFrame(rows).to_csv(path, index=False)
    logger.info(f"[CACHE SAVE] {len(candles)} candles → {os.path.basename(path)}")


def _parse_response(response: dict, tf: str) -> List[Candle]:
    """
    Parse a Dhan API response dict into a list of Candle objects.

    Args:
        response: Raw Dhan API response dictionary.
        tf: Timeframe string (for logging).

    Returns:
        List of Candle objects sorted by timestamp ascending.

    Raises:
        ValueError: If response format is unexpected.
    """
    if response.get("status") != "success" or "data" not in response:
        raise ValueError(f"Dhan API returned error for {tf}: {response}")

    raw = response["data"]
    if not raw:
        logger.warning(f"Empty data in Dhan response for {tf}")
        return []

    df = pd.DataFrame(raw)

    # Normalise timestamp column — Dhan returns different names
    for ts_col in ("start_Time", "startTime", "timestamp", "time"):
        if ts_col in df.columns:
            if ts_col == "timestamp" and df[ts_col].dtype in ("int64", "float64"):
                df["_ts"] = pd.to_datetime(df[ts_col], unit="s", utc=True).dt.tz_convert(IST)
            else:
                df["_ts"] = pd.to_datetime(df[ts_col], utc=False)
                if df["_ts"].dt.tz is None:
                    df["_ts"] = df["_ts"].dt.tz_localize(IST)
                else:
                    df["_ts"] = df["_ts"].dt.tz_convert(IST)
            break
    else:
        raise ValueError(f"No recognised timestamp column. Got: {df.columns.tolist()}")

    candles = []
    for _, row in df.iterrows():
        candles.append(Candle(
            open=float(row.get("open", 0)),
            high=float(row.get("high", 0)),
            low=float(row.get("low", 0)),
            close=float(row.get("close", 0)),
            volume=int(row.get("volume", 0)),
            timestamp=row["_ts"],
        ))

    candles.sort(key=lambda c: c.timestamp)
    return candles


def _fetch_tf(dhan_client, instrument: InstrumentConfig,
              tf: str, from_date: date, to_date: date) -> List[Candle]:
    """
    Fetch one timeframe from Dhan API, with pagination support.
    Dhan limits each call to 90 days of intraday data, so we split
    longer ranges into 30-day chunks.

    Args:
        dhan_client: Authenticated DhanHQ client.
        instrument: InstrumentConfig for the security.
        tf: Timeframe string e.g. "5m".
        from_date: Start date.
        to_date: End date.

    Returns:
        Merged, sorted list of Candle objects for the full date range.
    """
    exchange_segment, instrument_type = _resolve_exchange_params(instrument)
    interval = TF_TO_INTERVAL[tf]

    all_candles: List[Candle] = []
    chunk_start = from_date

    while chunk_start < to_date:
        chunk_end = min(chunk_start + timedelta(days=29), to_date)
        logger.info(
            f"Fetching {instrument.symbol} {tf} "
            f"{chunk_start} → {chunk_end}"
        )
        try:
            resp = dhan_client.intraday_minute_data(
                security_id=str(instrument.security_id),
                exchange_segment=exchange_segment,
                instrument_type=instrument_type,
                interval=interval,
                from_date=chunk_start.strftime("%Y-%m-%d"),
                to_date=chunk_end.strftime("%Y-%m-%d"),
            )
            chunk_candles = _parse_response(resp, tf)
            all_candles.extend(chunk_candles)
            logger.info(f"  → {len(chunk_candles)} candles")
        except Exception as e:
            logger.error(f"Failed to fetch {tf} chunk {chunk_start}→{chunk_end}: {e}")

        chunk_start = chunk_end + timedelta(days=1)

    # Deduplicate by timestamp
    seen = set()
    unique = []
    for c in all_candles:
        if c.timestamp not in seen:
            seen.add(c.timestamp)
            unique.append(c)
    unique.sort(key=lambda c: c.timestamp)
    return unique


def load_historical(
    dhan_client,
    instrument: InstrumentConfig,
    mode: str,
    from_date: date,
    to_date: date,
) -> Dict[str, List[Candle]]:
    """
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
    """
    required_tfs = MODE_TF_MAP.get(mode.upper(), MODE_TF_MAP["BOTH"])
    result: Dict[str, List[Candle]] = {}

    for tf in required_tfs:
        path = _cache_path(instrument.security_id, tf, from_date, to_date)
        cached = _load_from_cache(path)

        if cached is not None:
            result[tf] = cached
        else:
            candles = _fetch_tf(dhan_client, instrument, tf, from_date, to_date)
            if candles:
                _save_to_cache(candles, path)
                result[tf] = candles
            else:
                logger.warning(f"No candles returned for {tf} — skipping")

    return result


def clear_cache(security_id: int) -> None:
    """
    Delete all cached CSV files for a given security ID.

    Args:
        security_id: The Dhan security ID whose cache to clear.
    """
    if not os.path.exists(CACHE_DIR):
        return
    deleted = 0
    for fname in os.listdir(CACHE_DIR):
        if fname.startswith(f"{security_id}_"):
            os.remove(os.path.join(CACHE_DIR, fname))
            deleted += 1
    logger.info(f"Cleared {deleted} cache files for security_id={security_id}")