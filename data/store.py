import os
import logging
from typing import Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
else:
    supabase = None
    logger.warning("Supabase credentials not found. Database storage disabled.")

def save_candle(candle, tf: str, instrument_config):
    """
    Persists a single candle's data to the Supabase database.

    Args:
        candle (Candle): The candle object to save.
        tf (str): The timeframe of the candle.
        instrument_config (InstrumentConfig): Configuration of the instrument.
    """
    if not supabase: return
    try:
        data = {
            "security_id": instrument_config.security_id,
            "symbol": instrument_config.symbol,
            "exchange": instrument_config.exchange,
            "tf": tf,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "timestamp": candle.timestamp.isoformat()
        }
        supabase.table("candles").insert(data).execute()
    except Exception as e:
        logger.error(f"Failed to save candle: {e}")

def save_setup(setup_dict: dict):
    """
    Persists a new PHANTOM trading setup to the database.

    Args:
        setup_dict (dict): Flat dictionary containing setup parameters and metrics.

    Returns:
        Optional[int]: The database ID of the newly created record, or None 
            if insertion failed.
    """
    if not supabase: return None
    try:
        res = supabase.table("phantom_setups").insert(setup_dict).execute()
        if res.data:
            return res.data[0]['id']
    except Exception as e:
        logger.error(f"Failed to save setup: {e}")
    return None

def update_setup_state(setup_id: int, state: str, outcome: str = None):
    """
    Updates the state or outcome of an existing setup in the database.

    Args:
        setup_id (int): The unique database ID of the setup.
        state (str): The new state to transition to.
        outcome (str, optional): The eventual result of the trade (e.g., TP1 hit).
    """
    if not supabase or not setup_id: return
    try:
        update_data = {"state": state}
        if outcome:
            update_data["outcome"] = outcome
        supabase.table("phantom_setups").update(update_data).eq("id", setup_id).execute()
    except Exception as e:
        logger.error(f"Failed to update setup {setup_id}: {e}")

class StoreManager:
    """
    Class-based interface for Supabase storage, supporting both 
    live setups and backtest runs.
    """
    def __init__(self):
        self.supabase = supabase

    def save_backtest_run(self, run_id: str, stats: Any):
        """Save summary of a backtest run."""
        if not self.supabase: return
        data = {
            "run_id": run_id,
            "symbol": stats.symbol,
            "mode": stats.mode,
            "from_date": stats.from_date,
            "to_date": stats.to_date,
            "total_trades": stats.total_trades,
            "win_rate": stats.win_rate,
            "profit_factor": stats.profit_factor,
            "total_pnl": stats.total_pnl_points,
            "max_drawdown": stats.max_drawdown_points
        }
        self.supabase.table("backtest_runs").insert(data).execute()

    def save_backtest_trades_bulk(self, trades_batch: list):
        """Bulk save backtest individual trades."""
        if not self.supabase: return
        self.supabase.table("backtest_trades").insert(trades_batch).execute()

    def save_candles_bulk(self, candles: list, tf: str, instrument: Any):
        """Save a batch of candles."""
        if not self.supabase: return
        data = []
        for c in candles:
            data.append({
                "security_id": instrument.security_id,
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "tf": tf,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "timestamp": c.timestamp.isoformat()
            })
        self.supabase.table("candles").insert(data).execute()
