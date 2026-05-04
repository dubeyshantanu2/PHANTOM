# Module data.backtest_feed

## Class `BacktestFeedManager`
Simulates a data feed manager using historical data from DataFrames.

Allows replaying history by maintaining a 'cursor' and providing
candles relative to that cursor.

### Method `__init__`
Initializes the backtest feed with historical data for multiple timeframes.

Args:
    data (Dict[str, pd.DataFrame]): Dictionary mapping timeframe (e.g., '1m') 
                                   to a DataFrame with columns: 
                                   ['timestamp', 'open', 'high', 'low', 'close', 'volume']

### Method `get_candles`
Returns a list of historical candles up to the current cursor.

### Method `set_cursor`
Sets the current simulated 'now' timestamp.

