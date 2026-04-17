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
        
    if not setup.get("sweep_data"):
        return "PENDING"
        
    if not setup.get("fvg_data"):
        return "PENDING"
        
    if not setup.get("entry_data"):
        return "PENDING"
        
    if not setup.get("target_data"):
        return "INVALID" # RR didn't clear threshold
        
    # Check session end time
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    end_hour, end_minute = map(int, instrument.session_end.split(':'))
    session_end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    
    if now >= session_end_time:
        return "INVALID"
        
    return "VALID"
