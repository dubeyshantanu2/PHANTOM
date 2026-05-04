# Module core.fvg_engine

## Class `FVGZone`
Represents a Fair Value Gap (FVG) area in the market.

Attributes:
    type (str): Either "bullish" (undervalued) or "bearish" (overvalued).
    top (float): The upper boundary price of the gap.
    bottom (float): The lower boundary price of the gap.
    midpoint (float): The 50% equilibrium level of the FVG.
    created_at (datetime): Timestamp when the FVG was formed.
    status (str): Current state of the zone ("FRESH", "MITIGATED", or "VIOLATED").
    displacement_strength (float): Ratio of the candle body to ATR, indicating 
        the force of the move that created the gap.

### Method `__init__`
## Function `detect_fvg`
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

## Function `update_fvg_status`
Updates the status of an FVG based on subsequent price action.

