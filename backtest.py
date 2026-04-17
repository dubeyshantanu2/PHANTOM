import argparse
import logging
import sys
from datetime import datetime, timedelta
import pandas as pd
import pytz

from config import InstrumentConfig, KNOWN_INSTRUMENTS, DEFAULT_SECURITY_ID, MODES
from auth import get_dhan_client
from data.backtest_feed import BacktestFeedManager
from core.mode_controller import ModeController

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("BACKTEST")

def fetch_historical_data(client, instrument, from_date, to_date, inst_type, exchange_segment):
    """
    Fetches historical OHLCV data from Dhan for all required timeframes.
    """
    timeframes = ["1m", "5m", "15m", "1h"]
    data = {}
    
    # Map TF to Dhan interval format
    tf_map = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}
    
    for tf in timeframes:
        logger.info(f"Fetching {tf} data for {instrument.symbol}...")
        
        try:
            response = client.intraday_minute_data(
                security_id=str(instrument.security_id),
                exchange_segment=exchange_segment,
                instrument_type=inst_type,
                interval=tf_map[tf],
                from_date=from_date,
                to_date=to_date
            )
            
            if response.get("status") == "success" and "data" in response:
                df = pd.DataFrame(response["data"])
                if df.empty:
                    logger.warning(f"No data returned for {tf}")
                    continue
                # Expected columns: start_Time, open, high, low, close, volume
                # Need to convert them to Candle dataclass
                logger.info(f"Columns found in {tf} data: {df.columns.tolist()}")
                if 'start_Time' in df.columns:
                    df['timestamp_dt'] = pd.to_datetime(df['start_Time'])
                elif 'startTime' in df.columns:
                    df['timestamp_dt'] = pd.to_datetime(df['startTime'])
                elif 'timestamp' in df.columns:
                    # Dhan index data seems to return 'timestamp' as unix epoch
                    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    logger.error(f"Required time column not found. Columns: {df.columns.tolist()}")
                    continue
                
                # Use our standardized timestamp column
                df['timestamp'] = df['timestamp_dt']
                data[tf] = df.sort_values('timestamp').reset_index(drop=True)
                logger.info(f"Loaded {len(df)} candles for {tf}")
            else:
                logger.error(f"Failed to fetch {tf} data: {response}")
        except Exception as e:
            logger.error(f"Error fetching {tf} data: {e}")
            
    return data

def run_backtest(instrument, mode, data):
    """
    Runs the backtest simulation.
    """
    logger.info(f"Starting backtest simulation for {instrument.symbol} [{mode}]")
    
    # We need the base timeframe (1m) to drive the simulation clock
    if "1m" not in data or data["1m"].empty:
        logger.error("No 1m data available to drive the simulator.")
        return
    
    feed_manager = BacktestFeedManager(data)
    controller = ModeController(instrument, mode, dry_run=True)
    
    simulation_timeline = data["1m"]['timestamp'].tolist()
    all_setups = []
    for ts in simulation_timeline:
        feed_manager.set_cursor(ts)
        controller.tick_all(feed_manager)
        
    # Aggregate results from pipelines
    for p in controller.pipelines:
        all_setups.extend(p.setups_found)
        
    logger.info("Backtest simulation complete.")
    
    # Sort and display results
    if all_setups:
        all_setups.sort(key=lambda x: str(x.get('timestamp')))
        print("\n" + "="*80)
        print("  PHANTOM BACKTEST RESULTS SUMMARY")
        print("="*80)
        print(f"{'TIMESTAMP':<20} | {'MODE':<10} | {'BIAS':<8} | {'RR':<5} | {'ENTRY':<10}")
        print("-" * 80)
        for s in all_setups:
            ts_str = s.get('timestamp').strftime('%Y-%m-%d %H:%M') if hasattr(s.get('timestamp'), 'strftime') else str(s.get('timestamp'))
            print(f"{ts_str:<20} | {s.get('mode', 'N/A'):<10} | {s.get('bias', 'N/A'):<8} | {s.get('rr', 0.0):<5.2f} | {s.get('entry_price', 0.0):<10.2f}")
        print("="*80)
        print(f"Total Setups Found: {len(all_setups)}")
        print("="*80 + "\n")
    else:
        print("\n" + "="*50)
        print("  NO SETUPS FOUND IN THE GIVEN TIME RANGE")
        print("="*50 + "\n")

def main():
    parser = argparse.ArgumentParser(description="PHANTOM Backtester")
    parser.add_argument("--symbol_id", type=int, default=DEFAULT_SECURITY_ID)
    parser.add_argument("--mode", choices=["SCALPER", "SWING", "BOTH"], default="BOTH")
    parser.add_argument("--days", type=int, default=1, help="Number of days to backtest (limited by Dhan intraday API)")
    
    args = parser.parse_args()
    
    # Resolve Instrument
    if args.symbol_id in KNOWN_INSTRUMENTS:
        info = KNOWN_INSTRUMENTS[args.symbol_id]
        instrument = InstrumentConfig(
            security_id=args.symbol_id,
            symbol=info["symbol"],
            exchange=info["exchange"],
            session_end=info["session_end"],
            is_commodity=info["is_commodity"]
        )
    else:
        logger.error(f"Unknown symbol ID {args.symbol_id}")
        sys.exit(1)

    try:
        dhan_client = get_dhan_client()
        # Calculate dates - handling weekends
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        # If it's Saturday (5) or Sunday (6), move to Friday
        if now.weekday() == 5:
            now = now - timedelta(days=1)
        elif now.weekday() == 6:
            now = now - timedelta(days=2)
            
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")
        
        # Determine correct instrument_type and segment for Dhan SDK
        # This is CRITICAL for indices like NIFTY/SENSEX
        exchange_segment = instrument.exchange
        if instrument.symbol in ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"]:
            inst_type = "INDEX"
            exchange_segment = "IDX_I"
        elif instrument.is_commodity:
            inst_type = "COMMODITY"
        else:
            inst_type = "EQUITY"
            
        data = fetch_historical_data(dhan_client, instrument, from_date, to_date, inst_type, exchange_segment)
        
        if not data:
            logger.error("No data fetched. Check your Dhan API connection.")
            sys.exit(1)
            
        run_backtest(instrument, args.mode, data)
        
    except Exception as e:
        logger.exception(f"Backtest failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
