from typing import List, Dict, Any, Optional
from data.feed import Candle
from core.liquidity_map import LiquidityMap, LiquidityLevel

def detect_sweep(candles: List[Candle], lmap: LiquidityMap, bias: str) -> Optional[Dict[str, Any]]:
    """
    Identifies if a liquidity sweep has occurred on the pattern timeframe.

    A sweep is defined as a candle whose wick violates a liquidity level
    but whose close remains within the previous structure (liquidity grab).

    Args:
        candles (List[Candle]): List of candles to check for sweeps.
        lmap (LiquidityMap): Current map of active liquidity levels.
        bias (str): Current market bias ("LONG" or "SHORT").

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing sweep details if found:
            - sweep_type (str): "SSL" (for LONG bias) or "BSL" (for SHORT bias).
            - swept_level (float): The price level that was swept.
            - sweep_candle_idx (int): Global index of the sweep candle.
            - candle (Candle): The specific Candle object that performed the sweep.
            - strength (float): The depth of the sweep relative to ATR.
    """
    if not candles:
        return None
        
    latest_candle = candles[-1]
    
    if bias == "LONG":
        # Look for SSL sweep
        for level in lmap.ssl:
            if level.state == "INTACT" and latest_candle.low < level.price and latest_candle.close > level.price:
                strength = (level.price - latest_candle.low) / (latest_candle.atr if latest_candle.atr else 1)
                return {
                    "sweep_type": "SSL",
                    "swept_level": level.price,
                    "sweep_candle_idx": len(candles) - 1,
                    "timestamp": latest_candle.timestamp,
                    "candle": latest_candle,
                    "strength": strength
                }
    elif bias == "SHORT":
        # Look for BSL sweep
        for level in lmap.bsl:
            if level.state == "INTACT" and latest_candle.high > level.price and latest_candle.close < level.price:
                strength = (latest_candle.high - level.price) / (latest_candle.atr if latest_candle.atr else 1)
                return {
                    "sweep_type": "BSL",
                    "swept_level": level.price,
                    "sweep_candle_idx": len(candles) - 1,
                    "timestamp": latest_candle.timestamp,
                    "candle": latest_candle,
                    "strength": strength
                }
                
    return None
