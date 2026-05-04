from typing import List, Dict, Any, Optional
from data.feed import Candle
from core.fvg_engine import FVGZone
import logging

logger = logging.getLogger(__name__)

def evaluate_entry(candles: List[Candle], fvg: FVGZone, entry_type: str, bias: str, sl_buffer: float, sweep_data: Dict[str, Any], mode: str = "SCALPER") -> Optional[Dict[str, Any]]:
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
        sl_buffer (float): Buffer to add to the swing high/low for the Stop Loss (deprecated in favor of ATR).
        sweep_data (Dict[str, Any]): Data regarding the preceding liquidity sweep.
        mode (str): Trading mode ("SCALPER" or "SWING").

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
        # FIXED: Enter at the edge of the FVG for higher fill rate
        if bias == "LONG":
            if latest.low <= fvg.top:
                entry_price = fvg.top
        elif bias == "SHORT":
            if latest.high >= fvg.bottom:
                entry_price = fvg.bottom
            
    elif entry_type == "REJECTION":
        if bias == "LONG":
            if latest.low <= fvg.top and latest.close > fvg.top:
                entry_price = latest.close
        elif bias == "SHORT":
            if latest.high >= fvg.bottom and latest.close < fvg.bottom:
                entry_price = latest.close
            
    elif entry_type == "BOS":
        if len(candles) >= 2:
            prev = candles[-2]
            if bias == "LONG":
                if latest.low <= fvg.top and latest.close > prev.high:
                    entry_price = latest.close
            elif bias == "SHORT":
                if latest.high >= fvg.bottom and latest.close < prev.low:
                    entry_price = latest.close

    if entry_price:
        # FIXED: Use ATR-based adaptive SL buffer
        from config import MODES
        cfg = MODES[mode] if 'mode' in locals() else MODES["SCALPER"] # fallback
        atr_mult = cfg.get("sl_buffer_atr", 1.0)
        
        # We need the ATR from the pattern candle or latest candle
        atr_val = latest.atr if (hasattr(latest, 'atr') and latest.atr) else 10.0
        actual_sl_buffer = atr_val * atr_mult

        # FIXED: Calculate SL based on the FVG boundary rather than the HTF sweep extreme 
        # to drastically reduce risk distance on higher timeframes.
        if bias == "LONG":
            sl_price = fvg.bottom - actual_sl_buffer
        else:
            sl_price = fvg.top + actual_sl_buffer
        
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
