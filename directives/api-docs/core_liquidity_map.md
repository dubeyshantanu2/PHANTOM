# Module core.liquidity_map

## Class `LiquidityLevel`
Represents a specific price level where significant liquidity is resting.

Attributes:
    price (float): The price value of the liquidity level.
    type (str): Either "BSL" (Buy Side Liquidity) or "SSL" (Sell Side Liquidity).
    state (str): Whether the level is still "INTACT" or has been "SWEPT".
    timestamp (datetime): When the level was first identified (as a swing).
    strength (int): Number of times price has touched/rejected this level.

### Method `__init__`
## Class `LiquidityMap`
A container for all active liquidity levels in the current sessions.

Attributes:
    bsl (List[LiquidityLevel]): List of Buy Side Liquidity levels.
    ssl (List[LiquidityLevel]): List of Sell Side Liquidity levels.

### Method `__init__`
## Function `build_liquidity_map`
Constructs a map of significant price levels based on swing highs and lows.

Arg:
    candles (List[Candle]): List of candles enriched with swing data.
    tolerance (float): Percentage tolerance for matching equal levels.

Returns:
    LiquidityMap: An organized map of BSL and SSL levels.

## Function `update_sweep_status`
Updates the state of liquidity levels based on recent price action.

Marks any level as 'SWEPT' if the current candle's high or low has 
breached the level's price.

Args:
    lmap (LiquidityMap): The current liquidity map.
    candle (Candle): The most recent candle price data.

Returns:
    LiquidityMap: The updated liquidity map with new sweep statuses.

