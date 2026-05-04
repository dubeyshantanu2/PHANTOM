# Module data.store

## Class `StoreManager`
Class-based interface for Supabase storage, supporting both 
live setups and backtest runs.

### Method `__init__`
### Method `save_backtest_run`
Save summary of a backtest run.

### Method `save_backtest_trades_bulk`
Bulk save backtest individual trades.

### Method `save_candles_bulk`
Save a batch of candles.

## Function `save_candle`
Persists a single candle's data to the Supabase database.

Args:
    candle (Candle): The candle object to save.
    tf (str): The timeframe of the candle.
    instrument_config (InstrumentConfig): Configuration of the instrument.

## Function `save_setup`
Persists a new PHANTOM trading setup to the database.

Args:
    setup_dict (dict): Flat dictionary containing setup parameters and metrics.

Returns:
    Optional[int]: The database ID of the newly created record, or None 
        if insertion failed.

## Function `update_setup_state`
Updates the state or outcome of an existing setup in the database.

Args:
    setup_id (int): The unique database ID of the setup.
    state (str): The new state to transition to.
    outcome (str, optional): The eventual result of the trade (e.g., TP1 hit).

