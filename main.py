import argparse
import sys
import time
import logging
from datetime import datetime
import pytz
import schedule

from config import InstrumentConfig, KNOWN_INSTRUMENTS, DEFAULT_SECURITY_ID, ACTIVE_MODE
from auth import get_dhan_client
from data.feed import FeedManager
from data.store import supabase
from core.mode_controller import ModeController
from output.discord_alert import send_alert

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("PHANTOM")

def print_banner(instrument: InstrumentConfig, mode: str):
    """
    Displays the startup banner with project and instrument details.

    Args:
        instrument (InstrumentConfig): Configuration of the instrument.
        mode (str): Current active trading mode.
    """
    print("╔══════════════════════════════════════╗")
    print("║  PHANTOM starting...                 ║")
    print(f"║  Instrument : {instrument.symbol} (ID: {instrument.security_id})".ljust(39) + "║")
    print(f"║  Mode       : {mode}".ljust(39) + "║")
    print(f"║  Session    : {instrument.exchange} (closes {instrument.session_end} IST)".ljust(39) + "║")
    print("╚══════════════════════════════════════╝")

def check_session_end(instrument: InstrumentConfig, setup_count: int = 0):
    """
    Checks if the current time has reached the session end for the instrument.

    If the session has ended, sends a Discord alert and terminates the process.

    Args:
        instrument (InstrumentConfig): Configuration of the instrument.
        setup_count (int, optional): Number of setups processed in the session.
    """
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    end_hour, end_minute = map(int, instrument.session_end.split(':'))
    session_end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    
    if now >= session_end_time:
        alert_data = {"symbol": instrument.symbol, "current_time": now.strftime("%H:%M"), "count": setup_count}
        send_alert("SESSION_END", alert_data)
        logger.info(f"Session ended for {instrument.symbol}")
        sys.exit(0)

def main():
    """
    Entry point for the PHANTOM observation node.

    Parses CLI arguments, resolves instrument configuration, initializes 
    data feeds, and starts the core execution loop.
    """
    parser = argparse.ArgumentParser(description="PHANTOM - Price Hunt And Market Trap Observation Node")
    
    # Parse --<number> for security ID by overriding sys.argv parsing manually
    security_id = DEFAULT_SECURITY_ID
    mode = ACTIVE_MODE
    
    args = sys.argv[1:]
    for arg in args:
        if arg.startswith('--') and arg[2:].isdigit():
            security_id = int(arg[2:])
        elif arg in ["--SCALPER", "--SWING", "--BOTH"]:
            mode = arg[2:]
        elif arg == "--help":
            print("Usage: python main.py [--<security_id>] [--SCALPER | --SWING | --BOTH]")
            print("Example: python main.py --56789 --SWING")
            sys.exit(0)
            
    # Resolve Instrument
    if security_id in KNOWN_INSTRUMENTS:
        info = KNOWN_INSTRUMENTS[security_id]
        instrument = InstrumentConfig(
            security_id=security_id,
            symbol=info["symbol"],
            exchange=info["exchange"],
            session_end=info["session_end"],
            is_commodity=info["is_commodity"]
        )
    else:
        ans = input(f"Unknown security ID {security_id}. Is this a commodity? (y/n): ").strip().lower()
        is_commodity = ans == 'y'
        session_end = "23:30" if is_commodity else "15:30"
        exchange = "MCX" if is_commodity else "NSE"
        instrument = InstrumentConfig(
            security_id=security_id,
            symbol=f"UNKNOWN_{security_id}",
            exchange=exchange,
            session_end=session_end,
            is_commodity=is_commodity
        )

    print_banner(instrument, mode)
    
    try:
        # Initialize
        dhan_client = get_dhan_client()
        feed_manager = FeedManager(dhan_client)
        controller = ModeController(instrument, mode)
        
        # Schedule jobs based on timeframes
        # For simplicity in this structure, we run tick_all every minute.
        # Inside controller, it can decide whether to process based on new candle availability.
        schedule.every(1).minutes.do(lambda: controller.tick_all(feed_manager))
        
        logger.info("Starting polling loop...")
        
        # Initial run
        controller.tick_all(feed_manager)
        
        while True:
            schedule.run_pending()
            check_session_end(instrument)
            time.sleep(1)
            
    except KeyboardInterrupt:
        send_alert("INVALIDATED", {"symbol": instrument.symbol, "mode": mode, "reason": "Manually stopped via CLI"})
        logger.info(f"⏹️ PHANTOM manually stopped for {instrument.symbol}")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
