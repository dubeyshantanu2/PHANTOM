import pandas as pd
from typing import List, Dict
from datetime import datetime
from data.feed import Candle
from config import InstrumentConfig

class BacktestFeedManager:
    """
    Simulates a data feed manager using historical data from DataFrames.
    
    Allows replaying history by maintaining a 'cursor' and providing
    candles relative to that cursor.
    """
    def __init__(self, data: Dict[str, pd.DataFrame]):
        """
        Initializes the backtest feed with historical data for multiple timeframes.
        
        Args:
            data (Dict[str, pd.DataFrame]): Dictionary mapping timeframe (e.g., '1m') 
                                           to a DataFrame with columns: 
                                           ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        self.data = data
        self.cursor_timestamp = None
        self.buffers = {tf: [] for tf in data.keys()}

    def set_cursor(self, timestamp: datetime):
        """Sets the current simulated 'now' timestamp."""
        self.cursor_timestamp = timestamp

    def get_candles(self, instrument: InstrumentConfig, tf: str, limit: int) -> List[Candle]:
        """
        Returns a list of historical candles up to the current cursor.
        """
        if tf not in self.data:
            return []

        df = self.data[tf]
        # Get all candles where timestamp <= current cursor
        mask = df['timestamp'] <= self.cursor_timestamp
        current_data = df.loc[mask].tail(limit)

        candles = []
        for _, row in current_data.iterrows():
            candles.append(Candle(
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                timestamp=row['timestamp']
            ))
        
        return candles
