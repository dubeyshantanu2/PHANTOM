from typing import List, Dict, Any
from data.feed import Candle

def detect_bias(candles: List[Candle]) -> Dict[str, Any]:
    """
    Directional Bias Engine (Reactive).
    Sets bias based on the most recent Break of Structure (BOS).
    If no recent BOS, it looks at current price relative to the 
    most recent major swing.
    """
    if len(candles) < 10:
        return {"bias": "NEUTRAL", "last_bos_price": None, "draw_on_liquidity": None, "bos_type": None}
        
    # Find most recent swing high and low
    last_sh = None
    last_sl = None
    
    # Search backwards for swings
    for c in reversed(candles):
        if c.is_swing_high and last_sh is None:
            last_sh = c.high
        if c.is_swing_low and last_sl is None:
            last_sl = c.low
        if last_sh and last_sl:
            break

    # Look for BOS by checking latest closes against those swings
    latest_close = candles[-1].close
    
    # Check for BULLISH BOS
    if last_sh and latest_close > last_sh:
        return {
            "bias": "LONG",
            "last_bos_price": last_sh,
            "draw_on_liquidity": None,
            "bos_type": "bullish"
        }
        
    # Check for BEARISH BOS
    if last_sl and latest_close < last_sl:
        return {
            "bias": "SHORT",
            "last_bos_price": last_sl,
            "draw_on_liquidity": None,
            "bos_type": "bearish"
        }

    # FALLBACK: If no BOS, maintain bias from the most recent BOS event found 
    # searching backwards through the buffer
    current_sh = None
    current_sl = None
    for i in range(len(candles) - 1, 0, -1):
        c = candles[i]
        prev_c = candles[i-1]
        
        if c.is_swing_high: current_sh = c.high
        if c.is_swing_low:  current_sl = c.low
        
        if current_sh and prev_c.close > current_sh:
            return {"bias": "LONG", "last_bos_price": current_sh, "bos_type": "bullish"}
        if current_sl and prev_c.close < current_sl:
            return {"bias": "SHORT", "last_bos_price": current_sl, "bos_type": "bearish"}

    return {"bias": "NEUTRAL", "last_bos_price": None, "draw_on_liquidity": None, "bos_type": None}

compute_bias = detect_bias
