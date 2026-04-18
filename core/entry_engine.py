from typing import List, Dict, Any, Optional
from data.feed import Candle
from core.fvg_engine import FVGZone
import logging

logger = logging.getLogger(__name__)

def evaluate_entry(candles: List[Candle], fvg: FVGZone, entry_type: str, bias: str, sl_buffer: float, sweep_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluates current price action for a potential trade entry trigger.

    Checks if the price has retraced into a Fair Value Gap (FVG) and if the
    specified entry condition (MITIGATION, REJECTION, or BOS) is met.

    Args:
        candles (List[Candle]): Current timeframe candles.
        fvg (FVGZone): The Fair Value Gap zone being monitored for entry.
        entry_type (str): The type of entry trigger to watch for ("MITIGATION", 
            "REJECTION", "BOS").
        bias (str): The current market bias ("LONG" or "SHORT").
        sl_buffer (float): Buffer to add to the swing high/low for the Stop Loss.
        sweep_data (Dict[str, Any]): Data regarding the preceding liquidity sweep.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing entry details if triggered,
            else None. Details include:
            - entry_price (float): The calculated entry level.
            - sl_price (float): The calculated stop loss level.
            - entry_type (str): The type of entry that triggered.
            - entry_candle (Candle): The candle that caused the trigger.
    """
    if not candles: return None
    
    # FIXED: BUG 6A — Ensure entries only happen into FRESH FVGs
    if fvg.status != "FRESH":
        return None
        
    latest = candles[-1]
    entry_price = None
    
    if entry_type == "MITIGATION":
        # FIXED: BUG 6B — Tighten MITIGATION conditions to ensure price is INSIDE the zone 
        # and not blown through. Entry at midpoint.
        if bias == "LONG":
            if fvg.bottom <= latest.low <= fvg.top:
                entry_price = fvg.midpoint
        elif bias == "SHORT":
            if fvg.bottom <= latest.high <= fvg.top:
                entry_price = fvg.midpoint
            
    elif entry_type == "REJECTION":
        # FIXED: BUG 6B — Added zone check before evaluating rejection
        if bias == "LONG":
            if fvg.bottom <= latest.low <= fvg.top and latest.close > fvg.bottom:
                entry_price = latest.close
        elif bias == "SHORT":
            if fvg.bottom <= latest.high <= fvg.top and latest.close < fvg.top:
                entry_price = latest.close
            
    elif entry_type == "BOS":
        # FIXED: BUG 6B — Added zone check before evaluating BOS
        if len(candles) >= 2:
            prev = candles[-2]
            if bias == "LONG":
                if fvg.bottom <= latest.low <= fvg.top and latest.close > prev.high:
                    entry_price = latest.close
            elif bias == "SHORT":
                if fvg.bottom <= latest.high <= fvg.top and latest.close < prev.low:
                    entry_price = latest.close

    if entry_price:
        # Calculate SL based on sweep wick
        sl_price = sweep_data["candle"].low - sl_buffer if bias == "LONG" else sweep_data["candle"].high + sl_buffer
        
        # Ensure SL is actually protective (not worse than entry)
        if bias == "LONG" and sl_price >= entry_price:
            return None
        if bias == "SHORT" and sl_price <= entry_price:
            return None
        
        return {
            "entry_price": round(entry_price, 2),
            "sl_price": round(sl_price, 2),
            "entry_type": entry_type,
            "entry_candle": latest
        }
        
    return None
