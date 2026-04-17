import logging
from dataclasses import dataclass
from typing import List
from datetime import datetime
import pandas as pd
from dhanhq import dhanhq
from config import InstrumentConfig, CANDLE_BUFFER_SIZE

logger = logging.getLogger(__name__)

@dataclass
class Candle:
    """
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
    """
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    is_swing_high: bool = False
    is_swing_low: bool = False
    atr: float = 0.0

class FeedManager:
    """
    Manages OHLCV data feeds from the Dhan HQ API.

    Handles connection to the SDK, fetching historical/intraday data,
    and maintaining in-memory buffers for different timeframes.

    Attributes:
        client (dhanhq): Authenticated Dhan SDK client.
        buffers (Dict[str, List[Candle]]): In-memory storage of recent candles.
    """
    def __init__(self, client: dhanhq):
        self.client = client
        self.buffers = {
            "1m": [],
            "5m": [],
            "15m": [],
            "1h": []
        }

    def get_candles(self, instrument: InstrumentConfig, tf: str, limit: int) -> List[Candle]:
        """
        Fetches OHLCV candles for a specific instrument and timeframe.

        Retrieves data using the Dhan SDK, converts it to Candle objects,
        and updates the internal buffer up to CANDLE_BUFFER_SIZE.

        Args:
            instrument (InstrumentConfig): Configuration of the instrument.
            tf (str): Timeframe to fetch (e.g., "1m", "5m", "15m", "1h").
            limit (int): Number of most recent candles to return.

        Returns:
            List[Candle]: List of Candle objects sorted by time (ascending).
        """
        try:
            # Map TF to Dhan interval format
            tf_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
            interval = tf_map.get(tf, "1")
            
            # The dhanhq SDK function for historical data requires from_date and to_date
            # We'll use get_historical_minute_charts or intraday daily historical data
            # Here we assume a general interface. Adjust according to the actual SDK method.
            # Example using historical_minute_charts:
            response = self.client.intraday_minute_data(
                security_id=str(instrument.security_id),
                exchange_segment=instrument.exchange,
                instrument_type="EQUITY" if not instrument.is_commodity else "COMMODITY",
                interval=interval
            )
            
            if response.get("status") == "success" and "data" in response:
                df = pd.DataFrame(response["data"])
                # Expected columns: start_Time, open, high, low, close, volume
                # Need to convert them to Candle dataclass
                candles = []
                for _, row in df.tail(limit).iterrows():
                    candles.append(Candle(
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume']),
                        timestamp=pd.to_datetime(row['start_Time']).to_pydatetime()
                    ))
                
                # Update buffer
                self.buffers[tf] = candles[-CANDLE_BUFFER_SIZE[tf]:]
                return self.buffers[tf]
            else:
                logger.error(f"Failed to fetch {tf} candles: {response}")
                return self.buffers[tf]
                
        except Exception as e:
            logger.error(f"Error fetching candles for {tf}: {e}")
            return self.buffers[tf]
