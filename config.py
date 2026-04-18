from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class InstrumentConfig:
    """
    Configuration for a specific trading instrument.

    Attributes:
        security_id (int): Unique identifier for the security on the exchange.
        symbol (str): Human-readable ticker symbol (e.g., "NIFTY").
        exchange (str): The exchange segment ("NSE" or "MCX").
        session_end (str): The local time (HH:MM) when the trading session ends.
        is_commodity (bool): True if the instrument is traded on MCX.
    """
    security_id: int
    symbol: str
    exchange: str
    session_end: str
    is_commodity: bool

DEFAULT_SECURITY_ID = 13

KNOWN_INSTRUMENTS: Dict[int, Dict[str, Any]] = {
    13: {"symbol": "NIFTY", "exchange": "NSE", "session_end": "15:30", "is_commodity": False},
    12: {"symbol": "SENSEX", "exchange": "BSE", "session_end": "15:30", "is_commodity": False},
}

MODES = {
    "SCALPER": {
        "htf_bias_tf":             "1h",
        "bias_tf":                 "15m",
        "pattern_tf":              "5m",
        "entry_tf":                "1m",

        # ── Detection thresholds ──────────────────────────────
        "fvg_displacement_atr":    1.2,   # was 0.8 — too loose, caught noise
        "sweep_to_fvg_max_bars":   5,     # was 3 — too tight, missed valid setups
        "swing_lookback":          5,     # bars each side for swing high/low detection
        "equal_level_tolerance":   0.05,  # % tolerance for equal highs/lows

        # ── Risk parameters ───────────────────────────────────
        "min_rr":                  1.2,   # relaxed
        "sl_buffer_points":        10.0,  # was 3.0 — way too tight for NIFTY

        # ── Session filter ────────────────────────────────────
        "session_start":           "09:20",  # skip opening noise candle
    },
    "SWING": {
        "htf_bias_tf":             "1h",
        "bias_tf":                 "1h",
        "pattern_tf":              "15m",
        "entry_tf":                "5m",

        # ── Detection thresholds ──────────────────────────────
        "fvg_displacement_atr":    0.8,   # relaxed to allow more FVGs
        "sweep_to_fvg_max_bars":   7,     # was 5 — give 15m structure more room
        "swing_lookback":          7,     # wider lookback for 15m swings
        "equal_level_tolerance":   0.05,

        # ── Risk parameters ───────────────────────────────────
        "min_rr":                  1.5,   # relaxed
        "sl_buffer_points":        25.0,  # was 10.0 — 15m swept swings need room

        # ── Session filter ────────────────────────────────────
        "session_start":           "09:20",
    }
}

import os
from dotenv import load_dotenv
load_dotenv()
ACTIVE_MODE = os.getenv("ACTIVE_MODE", "BOTH")
ENTRY_TYPE = os.getenv("ENTRY_TYPE", "MITIGATION")

TF_INTERVALS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600
}

CANDLE_BUFFER_SIZE = {
    "1m": 300,
    "5m": 288,
    "15m": 200,
    "1h": 120
}
