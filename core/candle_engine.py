import pandas as pd
import numpy as np
from typing import List
from data.feed import Candle

def detect_swings(candles: List[Candle], lookback: int = 3) -> List[Candle]:
    """
    Identifies swing highs and lows and calculates historical volatility (ATR).
    """
    if not candles: return candles
    
    # Pre-initialize attributes to prevent AttributeErrors in other modules
    for c in candles:
        if not hasattr(c, 'is_swing_high'): c.is_swing_high = False
        if not hasattr(c, 'is_swing_low'):  c.is_swing_low = False
        if not hasattr(c, 'atr'):           c.atr = 0.0

    if len(candles) < lookback * 2 + 1:
        return candles

    df = pd.DataFrame([
        {'high': c.high, 'low': c.low, 'close': c.close} for c in candles
    ])
    
    # Calculate ATR (14-period)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(window=14).mean()

    # Detect swings
    for i in range(lookback, len(candles) - lookback):
        # Swing High
        if all(candles[i].high > candles[i-j].high for j in range(1, lookback+1)) and \
           all(candles[i].high > candles[i+j].high for j in range(1, lookback+1)):
            candles[i].is_swing_high = True
            
        # Swing Low
        if all(candles[i].low < candles[i-j].low for j in range(1, lookback+1)) and \
           all(candles[i].low < candles[i+j].low for j in range(1, lookback+1)):
            candles[i].is_swing_low = True

    for i in range(len(candles)):
        if not np.isnan(df.at[i, 'atr']):
            candles[i].atr = float(df.at[i, 'atr'])

    return candles

# Alias for backtest compatibility
enrich_candles = detect_swings
