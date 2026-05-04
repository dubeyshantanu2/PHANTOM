# Module core.entry_engine

## Function `evaluate_entry`
Evaluates current price action for a potential trade entry trigger.

Checks if the price has retraced into a Fair Value Gap (FVG) and if the
specified entry condition (MITIGATION, REJECTION, or BOS) is met.

Args:
    candles (List[Candle]): Current timeframe candles.
    fvg (FVGZone): The Fair Value Gap zone being monitored for entry.
    entry_type (str): The type of entry trigger to watch for ("MITIGATION", 
        "REJECTION", "BOS").
    bias (str): The current market bias ("LONG" or "SHORT").
    sl_buffer (float): Buffer to add to the swing high/low for the Stop Loss.
    sweep_data (Dict[str, Any]): Data regarding the preceding liquidity sweep.

Returns:
    Optional[Dict[str, Any]]: A dictionary containing entry details if triggered,
        else None. Details include:
        - entry_price (float): The calculated entry level.
        - sl_price (float): The calculated stop loss level.
        - entry_type (str): The type of entry that triggered.
        - entry_candle (Candle): The candle that caused the trigger.

