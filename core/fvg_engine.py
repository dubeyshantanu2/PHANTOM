from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from data.feed import Candle

@dataclass
class FVGZone:
    """
    Represents a Fair Value Gap (FVG) area in the market.

    Attributes:
        type (str): Either "bullish" (undervalued) or "bearish" (overvalued).
        top (float): The upper boundary price of the gap.
        bottom (float): The lower boundary price of the gap.
        midpoint (float): The 50% equilibrium level of the FVG.
        created_at (datetime): Timestamp when the FVG was formed.
        status (str): Current state of the zone ("FRESH" or "MITIGATED").
        displacement_strength (float): Ratio of the candle body to ATR, indicating 
            the force of the move that created the gap.
    """
    type: str # "bullish" | "bearish"
    top: float
    bottom: float
    midpoint: float
    created_at: datetime
    status: str = "FRESH"
    displacement_strength: float = 0.0

def detect_fvg(candles: List[Candle], sweep_data: Dict[str, Any], bias: str, displacement_atr: float, max_bars: int) -> Optional[FVGZone]:
    """
    Identifies if an FVG has formed following a liquidity sweep.

    An FVG is detected as a 3-candle pattern where there's a gap between the
    high of the first candle and the low of the third (for bullish) or vice versa.

    Args:
        candles (List[Candle]): The list of candles on the pattern timeframe.
        sweep_data (Dict[str, Any]): Data about the preceding liquidity sweep.
        bias (str): Current market bias ("LONG" or "SHORT").
        displacement_atr (float): Minimum body size (in multiples of ATR) 
            required to consider the move a 'displacement'.
        max_bars (int): Maximum number of bars to look ahead from the sweep 
            for FVG formation.

    Returns:
        Optional[FVGZone]: An FVGZone object if a valid gap is found, else None.
    """
    if len(candles) < 3: return None
    
    sweep_idx = sweep_data["sweep_candle_idx"]
    # Look for FVG starting from the sweep candle up to current candle (within max_bars)
    
    for i in range(sweep_idx + 2, min(len(candles), sweep_idx + max_bars + 3)):
        if i >= len(candles): break
        
        c0 = candles[i-2]
        c1 = candles[i-1] # Middle candle
        c2 = candles[i]
        
        fvg = None
        
        if bias == "LONG" and c0.high < c2.low:
            # Bullish FVG
            mid_body = abs(c1.close - c1.open)
            if mid_body > displacement_atr * c1.atr:
                fvg = FVGZone(
                    type="bullish",
                    top=c2.low,
                    bottom=c0.high,
                    midpoint=(c2.low + c0.high) / 2,
                    created_at=c1.timestamp,
                    displacement_strength=mid_body / c1.atr
                )
                return fvg
                
        elif bias == "SHORT" and c0.low > c2.high:
            # Bearish FVG
            mid_body = abs(c1.close - c1.open)
            if mid_body > displacement_atr * c1.atr:
                fvg = FVGZone(
                    type="bearish",
                    top=c0.low,
                    bottom=c2.high,
                    midpoint=(c0.low + c2.high) / 2,
                    created_at=c1.timestamp,
                    displacement_strength=mid_body / c1.atr
                )
                return fvg
                
    return None
