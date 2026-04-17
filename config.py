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
        "bias_tf": "15m",
        "pattern_tf": "5m",
        "entry_tf": "1m",
        "fvg_displacement_atr": 0.5,
        "sweep_to_fvg_max_bars": 3,
        "min_rr": 1.5,
        "sl_buffer_points": 5.0
    },
    "SWING": {
        "bias_tf": "1h",
        "pattern_tf": "15m",
        "entry_tf": "5m",
        "fvg_displacement_atr": 0.8,
        "sweep_to_fvg_max_bars": 5,
        "min_rr": 2.0,
        "sl_buffer_points": 15.0
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
    "1m": 200,
    "5m": 200,
    "15m": 100,
    "1h": 50
}
