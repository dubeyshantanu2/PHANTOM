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
        direction (str): "BULL" if displacement candle close > open, else "BEAR".
        top (float): The upper boundary price of the gap.
        bottom (float): The lower boundary price of the gap.
        midpoint (float): The 50% equilibrium level of the FVG.
        created_at (datetime): Timestamp when the FVG was formed.
        status (str): Current state of the zone ("FRESH", "MITIGATED", or "VIOLATED").
        displacement_strength (float): Ratio of the candle body to ATR, indicating 
            the force of the move that created the gap.
    """
    type: str # "bullish" | "bearish"
    direction: str # "BULL" | "BEAR"
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
    if sweep_idx < 0 or sweep_idx >= len(candles): return None
    
    # Look for FVG starting from the sweep candle up to current candle (within max_bars)
    
    for i in range(sweep_idx + 2, min(len(candles), sweep_idx + max_bars + 3)):
        if i >= len(candles): break
        
        c0 = candles[i-2]
        c1 = candles[i-1] # Middle candle
        c2 = candles[i]
        
        # FIXED: Prevent Cross-Day FVG (Overnight Gap Illusion)
        if c0.timestamp.date() != c2.timestamp.date():
            continue
        
        # FIXED: Add ATR zero bypass guard
        if c1.atr is None or c1.atr <= 0:
            continue
            
        fvg = None
        
        if bias == "LONG" and c0.high < c2.low:
            # Bullish FVG
            mid_body = abs(c1.close - c1.open)
            if mid_body > displacement_atr * c1.atr:
                direction = "BULL" if c1.close > c1.open else "BEAR"
                fvg = FVGZone(
                    type="bullish",
                    direction=direction,
                    top=c2.low,
                    bottom=c0.high,
                    midpoint=(c2.low + c0.high) / 2,
                    created_at=c1.timestamp,
                    displacement_strength=mid_body / c1.atr
                )
                
                # FIXED: Guard before returning FVGZone
                if fvg.displacement_strength == 0 or fvg.displacement_strength < 0.5:
                    continue
                return fvg
                
        elif bias == "SHORT" and c0.low > c2.high:
            # Bearish FVG
            mid_body = abs(c1.close - c1.open)
            if mid_body > displacement_atr * c1.atr:
                direction = "BULL" if c1.close > c1.open else "BEAR"
                fvg = FVGZone(
                    type="bearish",
                    direction=direction,
                    top=c0.low,
                    bottom=c2.high,
                    midpoint=(c0.low + c2.high) / 2,
                    created_at=c1.timestamp,
                    displacement_strength=mid_body / c1.atr
                )
                
                # FIXED: Guard before returning FVGZone
                if fvg.displacement_strength == 0 or fvg.displacement_strength < 0.5:
                    continue
                return fvg
                
    return None

# FIXED: Added update_fvg_status to track MITIGATED and VIOLATED states
def update_fvg_status(fvg: FVGZone, candle: Candle) -> FVGZone:
    """
    Updates the status of an FVG based on subsequent price action.
    """
    if fvg.status == "VIOLATED":
        return fvg
        
    if fvg.type == "bullish":
        # VIOLATED if candle closes fully below the zone
        if candle.close < fvg.bottom:
            fvg.status = "VIOLATED"
        # MITIGATED if candle closes inside the zone
        elif fvg.bottom <= candle.close <= fvg.top:
            fvg.status = "MITIGATED"
            
    elif fvg.type == "bearish":
        # VIOLATED if candle closes fully above the zone
        if candle.close > fvg.top:
            fvg.status = "VIOLATED"
        # MITIGATED if candle closes inside the zone
        elif fvg.bottom <= candle.close <= fvg.top:
            fvg.status = "MITIGATED"
            
    return fvg
