# Module core.bias_engine

## Function `compute_bias`
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

## Function `detect_bias`
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

