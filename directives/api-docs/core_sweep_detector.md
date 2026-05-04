# Module core.sweep_detector

## Function `detect_sweep`
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

