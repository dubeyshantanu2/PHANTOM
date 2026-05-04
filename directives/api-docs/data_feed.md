# Module data.feed

## Class `Candle`
Represents a single OHLCV candle with technical indicators.

Attributes:
    open (float): Opening price of the period.
    high (float): Highest price reached during the period.
    low (float): Lowest price reached during the period.
    close (float): Closing price of the period.
    volume (int): Total volume traded during the period.
    timestamp (datetime): Start time of the candle.
    is_swing_high (bool): True if this candle is a swing high.
    is_swing_low (bool): True if this candle is a swing low.
    atr (float): Average True Range at this candle point.

### Method `__init__`
## Class `FeedManager`
Manages OHLCV data feeds from the Dhan HQ API.

Handles connection to the SDK, fetching historical/intraday data,
and maintaining in-memory buffers for different timeframes.

Attributes:
    client (dhanhq): Authenticated Dhan SDK client.
    buffers (Dict[str, List[Candle]]): In-memory storage of recent candles.

### Method `__init__`
### Method `get_candles`
Fetches OHLCV candles for a specific instrument and timeframe.

Retrieves data using the Dhan SDK, converts it to Candle objects,
and updates the internal buffer up to CANDLE_BUFFER_SIZE.

Args:
    instrument (InstrumentConfig): Configuration of the instrument.
    tf (str): Timeframe to fetch (e.g., "1m", "5m", "15m", "1h").
    limit (int): Number of most recent candles to return.

Returns:
    List[Candle]: List of Candle objects sorted by time (ascending).

