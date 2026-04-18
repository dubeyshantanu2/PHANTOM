from typing import Dict, Any
from datetime import datetime
import pytz
from config import InstrumentConfig

def validate_setup(setup: Dict[str, Any], instrument: InstrumentConfig) -> str:
    """
    Performs a comprehensive validation of a potential trading setup.

    Runs a series of ordered checks to ensure the setup adheres to all
    trading rules and session constraints.

    Args:
        setup (Dict[str, Any]): The setup data to validate.
        instrument (InstrumentConfig): Configuration for the traded instrument.

    Returns:
        str: Validation status ("VALID", "INVALID", or "PENDING").
            - VALID: All criteria met.
            - INVALID: High-level failure (e.g., bias neutral, session ended).
            - PENDING: Intermediate state (e.g., sweep detected but FVG not yet formed).
    """
    if setup.get("bias") == "NEUTRAL":
        return "INVALID"
        
    htf_bias = setup.get("htf_bias")
    if htf_bias and htf_bias != "NEUTRAL":
        if setup.get("bias") != htf_bias:
            return "INVALID" # HTF alignment failed
        
    if not setup.get("sweep_data"):
        return "PENDING"
        
    if not setup.get("fvg_data"):
        return "PENDING"
        
    if not setup.get("entry_data"):
        return "PENDING"
        
    if not setup.get("target_data"):
        return "INVALID" # RR didn't clear threshold
        
    # Check session end time
    if "entry_data" in setup and "entry_candle" in setup["entry_data"]:
        now = setup["entry_data"]["entry_candle"].timestamp
    else:
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        
    end_hour, end_minute = map(int, instrument.session_end.split(':'))
    
    # Use session_start from config if available, default to 09:20 for Indian markets
    session_start_str = "09:20"
    if "mode" in setup and setup["mode"] in ['SCALPER', 'SWING']:
        from config import MODES
        session_start_str = MODES[setup["mode"]].get("session_start", "09:20")
        
    start_hour, start_minute = map(int, session_start_str.split(':'))
    
    # Simple integer comparison for HH:MM to avoid tz issues
    now_time_val = now.hour * 60 + now.minute
    end_time_val = end_hour * 60 + end_minute
    start_time_val = start_hour * 60 + start_minute
    
    if now_time_val >= end_time_val or now_time_val < start_time_val:
        return "INVALID"
        
    # Check Killzones (Avoid low-volume chop hours)
    if not instrument.is_commodity:
        # NSE: Morning (09:15-11:30) and Afternoon (13:30-15:30)
        in_morning = (9 * 60 + 15) <= now_time_val <= (11 * 60 + 30)
        in_afternoon = (13 * 60 + 30) <= now_time_val <= (15 * 60 + 30)
        if not (in_morning or in_afternoon):
            return "INVALID" # Out of NSE Killzone
    else:
        # MCX: US Session Overlap (18:00-23:30)
        in_evening = (18 * 60 + 0) <= now_time_val <= (23 * 60 + 30)
        if not in_evening:
            return "INVALID" # Out of MCX Killzone
        
    return "VALID"
