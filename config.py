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
        "bias_tf":                 "1h",     # Shifted from 15m
        "pattern_tf":              "15m",    # Shifted from 5m
        "entry_tf":                "5m",     # Shifted from 1m
        "ignore_htf_bias":         True,  

        # ── Detection thresholds ──────────────────────────────
        "fvg_displacement_atr":    0.5,   
        "sweep_to_fvg_max_bars":   10,    
        "swing_lookback":          3,     
        "equal_level_tolerance":   0.05,  

        # ── Risk parameters ───────────────────────────────────
        "min_rr":                  1.1,   
        "sl_buffer_atr":           1.0,   
        "max_risk_points":         90.0,  # Increased from 60

        # ── Session filter ────────────────────────────────────
        "session_start":           "09:20",  
    },
    "SWING": {
        "htf_bias_tf":             "1h",
        "bias_tf":                 "1h",
        "pattern_tf":              "1h",     
        "entry_tf":                "15m",    

        # ── Detection thresholds ──────────────────────────────
        "fvg_displacement_atr":    0.5,   
        "sweep_to_fvg_max_bars":   15,    
        "swing_lookback":          5,     
        "equal_level_tolerance":   0.05,

        # ── Risk parameters ───────────────────────────────────
        "min_rr":                  1.2,   
        "sl_buffer_atr":           1.5,   
        "max_risk_points":         200.0, # Increased from 120

        # ── Session filter ────────────────────────────────────
        "session_start":           "09:20",
    }
}

import os
from dotenv import load_dotenv
load_dotenv()
ACTIVE_MODE = os.getenv("ACTIVE_MODE", "BOTH")
ENTRY_TYPE = os.getenv("ENTRY_TYPE", "REJECTION")  # Changed from MITIGATION to REJECTION

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
