from typing import List, Dict, Any
from data.feed import Candle

def detect_bias(candles: List[Candle]) -> Dict[str, Any]:
    """
    Analyzes market structure to determine the current directional bias.

    Identifies Break of Structure (BOS) events by comparing current price action
    against previous swing highs and lows. A bullish BOS sets a LONG bias,
    while a bearish BOS sets a SHORT bias.

    Args:
        candles (List[Candle]): A list of candles enriched with swing data.
            Expected to have at least 20 candles for reliable detection.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - bias (str): "LONG", "SHORT", or "NEUTRAL".
            - last_bos_price (float|None): The price level where BOS occurred.
            - draw_on_liquidity (float|None): The next likely liquidity target.
            - bos_type (str|None): Detailed type of the BOS ("bullish" or "bearish").
    """
    if len(candles) < 20:
        return {"bias": "NEUTRAL", "last_bos_price": None, "draw_on_liquidity": None, "bos_type": None}
        
    last_swing_high = None
    last_swing_low = None
    
    bos_events = []
    
    # Iterate through candles to find the most recent BOS within the last 20 candles
    recent_candles = candles[-20:]
    
    # Need to find swings first inside this chunk or just rely on pre-calculated
    # Assuming candles passed are already enriched with detect_swings
    for i, c in enumerate(candles):
        if c.is_swing_high:
            last_swing_high = c.high
        if c.is_swing_low:
            last_swing_low = c.low
            
        if last_swing_high is not None and c.close > last_swing_high:
            bos_events.append({"type": "bullish", "price": last_swing_high, "index": i})
            last_swing_high = None # reset
            
        if last_swing_low is not None and c.close < last_swing_low:
            bos_events.append({"type": "bearish", "price": last_swing_low, "index": i})
            last_swing_low = None # reset

    # Check if we have any BOS
    if not bos_events:
        return {"bias": "NEUTRAL", "last_bos_price": None, "draw_on_liquidity": None, "bos_type": None}
        
    last_bos = bos_events[-1]
    bias = "LONG" if last_bos["type"] == "bullish" else "SHORT"
    dol = last_swing_high if bias == "LONG" else last_swing_low
    
    return {
        "bias": bias,
        "last_bos_price": last_bos["price"],
        "draw_on_liquidity": dol,
        "bos_type": last_bos["type"]
    }

# Alias for backtest compatibility
compute_bias = detect_bias
