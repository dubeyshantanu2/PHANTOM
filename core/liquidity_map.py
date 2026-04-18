from typing import List, Dict, Any
from dataclasses import dataclass
from data.feed import Candle

@dataclass
class LiquidityLevel:
    """
    Represents a specific price level where significant liquidity is resting.

    Attributes:
        price (float): The price value of the liquidity level.
        type (str): Either "BSL" (Buy Side Liquidity) or "SSL" (Sell Side Liquidity).
        state (str): Whether the level is still "INTACT" or has been "SWEPT".
        timestamp (datetime): When the level was first identified (as a swing).
        strength (int): Number of times price has touched/rejected this level.
    """
    price: float
    type: str # "BSL" or "SSL"
    state: str = "INTACT" # "INTACT" or "SWEPT"
    timestamp: Any = None
    strength: int = 1

class LiquidityMap:
    """
    A container for all active liquidity levels in the current sessions.

    Attributes:
        bsl (List[LiquidityLevel]): List of Buy Side Liquidity levels.
        ssl (List[LiquidityLevel]): List of Sell Side Liquidity levels.
    """
    def __init__(self):
        self.bsl: List[LiquidityLevel] = []
        self.ssl: List[LiquidityLevel] = []

def build_liquidity_map(candles: List[Candle], tolerance: float = 0.0005) -> LiquidityMap:
    """
    Constructs a map of significant price levels based on swing highs and lows.

    Arg:
        candles (List[Candle]): List of candles enriched with swing data.
        tolerance (float): Percentage tolerance for matching equal levels.

    Returns:
        LiquidityMap: An organized map of BSL and SSL levels.
    """
    lmap = LiquidityMap()
    
    for c in candles:
        if c.is_swing_high:
            # Check for equal highs
            matched = False
            for level in lmap.bsl:
                if abs(level.price - c.high) / c.high <= tolerance:
                    level.strength += 1
                    level.timestamp = c.timestamp
                    matched = True
                    break
            if not matched:
                lmap.bsl.append(LiquidityLevel(price=c.high, type="BSL", timestamp=c.timestamp))
                
        if c.is_swing_low:
            # Check for equal lows
            matched = False
            for level in lmap.ssl:
                if abs(level.price - c.low) / c.low <= tolerance:
                    level.strength += 1
                    level.timestamp = c.timestamp
                    matched = True
                    break
            if not matched:
                lmap.ssl.append(LiquidityLevel(price=c.low, type="SSL", timestamp=c.timestamp))
                
    return lmap

def update_sweep_status(lmap: LiquidityMap, candle: Candle) -> LiquidityMap:
    """
    Updates the state of liquidity levels based on recent price action.

    Marks any level as 'SWEPT' if the current candle's high or low has 
    breached the level's price.

    Args:
        lmap (LiquidityMap): The current liquidity map.
        candle (Candle): The most recent candle price data.

    Returns:
        LiquidityMap: The updated liquidity map with new sweep statuses.
    """
    for level in lmap.bsl:
        if level.state == "INTACT" and candle.high > level.price:
            level.state = "SWEPT"
            
    for level in lmap.ssl:
        if level.state == "INTACT" and candle.low < level.price:
            level.state = "SWEPT"
            
    return lmap
