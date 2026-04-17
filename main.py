"""
PHANTOM - Price Hunt And Market Trap Observation Node
Entry point: handles CLI parsing, instrument resolution,
live polling loop, and backtest routing.
"""

import argparse
import sys
import time
import logging
from datetime import datetime, date, timedelta

import pytz
import schedule

from config import (
    InstrumentConfig, KNOWN_INSTRUMENTS, DEFAULT_SECURITY_ID, ACTIVE_MODE
)
from auth import get_dhan_client
from data.feed import FeedManager
from data.store import StoreManager
from core.mode_controller import ModeController
from output.discord_alert import send_alert

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("PHANTOM.main")

IST = pytz.timezone("Asia/Kolkata")


# ── Banners ────────────────────────────────────────────────────────────────────

def print_live_banner(instrument: InstrumentConfig, mode: str) -> None:
    """Print startup banner for live mode."""
    lines = [
        "╔══════════════════════════════════════════╗",
        "║  PHANTOM starting... [LIVE]              ║",
        f"║  Instrument : {instrument.symbol} (ID: {instrument.security_id})".ljust(44) + "║",
        f"║  Mode       : {mode}".ljust(44) + "║",
        f"║  Session    : {instrument.exchange} (closes {instrument.session_end} IST)".ljust(44) + "║",
        "╚══════════════════════════════════════════╝",
    ]
    print("\n".join(lines))


def print_backtest_banner(instrument: InstrumentConfig, mode: str,
                           from_date: date, to_date: date) -> None:
    """Print startup banner for backtest mode."""
    period = f"{from_date.strftime('%Y-%m-%d')} → {to_date.strftime('%Y-%m-%d')}"
    lines = [
        "╔══════════════════════════════════════════╗",
        "║  PHANTOM starting... [BACKTEST]          ║",
        f"║  Instrument : {instrument.symbol} (ID: {instrument.security_id})".ljust(44) + "║",
        f"║  Mode       : {mode}".ljust(44) + "║",
        f"║  Period     : {period}".ljust(44) + "║",
        "╚══════════════════════════════════════════╝",
    ]
    print("\n".join(lines))


# ── Instrument resolution ──────────────────────────────────────────────────────

def resolve_instrument(security_id: int) -> InstrumentConfig:
    """
    Resolve an InstrumentConfig from a security ID.
    If the ID is unknown, prompts the user interactively.

    Args:
        security_id: Dhan security ID.

    Returns:
        InstrumentConfig for the given ID.
    """
    if security_id in KNOWN_INSTRUMENTS:
        info = KNOWN_INSTRUMENTS[security_id]
        return InstrumentConfig(
            security_id=security_id,
            symbol=info["symbol"],
            exchange=info["exchange"],
            session_end=info["session_end"],
            is_commodity=info["is_commodity"],
        )

    # Unknown ID — prompt user
    print(f"\nUnknown security ID: {security_id}")
    ans = input("Is this a commodity (MCX)? (y/n): ").strip().lower()
    is_commodity = ans == "y"
    exchange = "MCX" if is_commodity else "NSE"
    session_end = "23:30" if is_commodity else "15:30"
    symbol = input("Enter symbol name (e.g. CRUDEOIL, BANKNIFTY): ").strip().upper()
    if not symbol:
        symbol = f"SID{security_id}"

    return InstrumentConfig(
        security_id=security_id,
        symbol=symbol,
        exchange=exchange,
        session_end=session_end,
        is_commodity=is_commodity,
    )


# ── Session gate ───────────────────────────────────────────────────────────────

def is_session_over(instrument: InstrumentConfig) -> bool:
    """Return True if current IST time has passed the instrument session end."""
    now = datetime.now(IST)
    end_h, end_m = map(int, instrument.session_end.split(":"))
    session_end_dt = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    return now >= session_end_dt


def handle_session_end(instrument: InstrumentConfig, setup_count: int) -> None:
    """Send SESSION_END alert and exit cleanly."""
    now_str = datetime.now(IST).strftime("%H:%M")
    send_alert("SESSION_END", {
        "symbol": instrument.symbol,
        "security_id": instrument.security_id,
        "current_time": now_str,
        "count": setup_count,
    })
    logger.info(f"[LIVE] Session ended for {instrument.symbol} at {now_str} IST")
    sys.exit(0)


# ── CLI argument parsing ───────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Usage examples:
        python main.py
        python main.py --56789
        python main.py --56789 --SWING
        python main.py --backtest
        python main.py --backtest --56789 --SWING
        python main.py --backtest --from 2024-01-01 --to 2024-03-31
        python main.py --backtest --report
    """
    parser = argparse.ArgumentParser(
        prog="phantom",
        description="PHANTOM — Price Hunt And Market Trap Observation Node",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                              # Live, NIFTY, BOTH\n"
            "  python main.py --56789                      # Live, custom ID\n"
            "  python main.py --56789 --SWING              # Live, SWING only\n"
            "  python main.py --backtest                   # Backtest NIFTY, 30 days\n"
            "  python main.py --backtest --56789           # Backtest custom ID\n"
            "  python main.py --backtest --from 2024-01-01 --to 2024-03-31\n"
            "  python main.py --backtest --report          # Backtest + open HTML\n"
        ),
    )

    # Security ID: --<number> syntax e.g. --56789
    # We pre-process sys.argv to extract this before argparse sees it
    parser.add_argument(
        "--security-id",
        type=int,
        default=None,
        dest="security_id",
        help="Dhan security ID (default: 13 = NIFTY). Use as --56789",
    )

    # Mode override
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--SCALPER", action="store_true", help="Run in SCALPER mode only")
    mode_group.add_argument("--SWING", action="store_true", help="Run in SWING mode only")
    mode_group.add_argument("--BOTH", action="store_true", help="Run in BOTH modes (default)")

    # Backtest flags
    parser.add_argument("--backtest", action="store_true", help="Run in backtest mode")
    parser.add_argument(
        "--days", type=int, default=None,
        help="Number of days to backtest (default: 30)"
    )
    parser.add_argument(
        "--from", dest="from_date", type=str, default=None,
        metavar="YYYY-MM-DD", help="Backtest start date (if --days not used)"
    )
    parser.add_argument(
        "--to", dest="to_date", type=str, default=None,
        metavar="YYYY-MM-DD", help="Backtest end date (default: yesterday)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Auto-open HTML report in browser after backtest"
    )

    # Pre-process argv: turn --56789 into --security-id 56789
    processed_argv = []
    for arg in sys.argv[1:]:
        if arg.startswith("--") and arg[2:].isdigit():
            processed_argv.extend(["--security-id", arg[2:]])
        else:
            processed_argv.append(arg)

    return parser.parse_args(processed_argv)


# ── Live polling loop ──────────────────────────────────────────────────────────

def run_live(instrument: InstrumentConfig, mode: str) -> None:
    """
    Run PHANTOM in live mode.
    Polls Dhan API on per-timeframe schedules and feeds data
    through the core pipeline.

    Args:
        instrument: Resolved InstrumentConfig.
        mode: Active mode string — SCALPER | SWING | BOTH.
    """
    print_live_banner(instrument, mode)

    dhan_client = get_dhan_client()
    feed = FeedManager(dhan_client)
    store = StoreManager()
    controller = ModeController(instrument, mode)

    setup_count = 0

    # ── Per-TF tick functions ────────────────────────────────────────────────

    def tick_1m():
        """1-minute tick: feeds SCALPER entry engine."""
        candles = feed.get_candles(instrument.security_id, "1m", limit=200)
        store.save_candles_bulk(candles, "1m", instrument)
        controller.on_candles("1m", candles)

    def tick_5m():
        """5-minute tick: SCALPER pattern detection + SWING entry engine."""
        candles = feed.get_candles(instrument.security_id, "5m", limit=200)
        store.save_candles_bulk(candles, "5m", instrument)
        controller.on_candles("5m", candles)

    def tick_15m():
        """15-minute tick: SWING pattern detection + SCALPER bias engine."""
        candles = feed.get_candles(instrument.security_id, "15m", limit=100)
        store.save_candles_bulk(candles, "15m", instrument)
        controller.on_candles("15m", candles)

    def tick_1h():
        """1-hour tick: SWING bias engine."""
        candles = feed.get_candles(instrument.security_id, "1h", limit=50)
        store.save_candles_bulk(candles, "1h", instrument)
        controller.on_candles("1h", candles)

    # ── Schedule separate jobs per TF ────────────────────────────────────────
    schedule.every(1).minutes.do(tick_1m)
    schedule.every(5).minutes.do(tick_5m)
    schedule.every(15).minutes.do(tick_15m)
    schedule.every(60).minutes.do(tick_1h)

    logger.info(f"[LIVE] Polling started for {instrument.symbol} | Mode: {mode}")

    # Run all TFs immediately on startup
    tick_1h()
    tick_15m()
    tick_5m()
    tick_1m()

    try:
        while True:
            schedule.run_pending()

            # Track setup count from controller
            setup_count = controller.get_setup_count()

            # Session end check on every loop tick
            if is_session_over(instrument):
                handle_session_end(instrument, setup_count)

            time.sleep(1)

    except KeyboardInterrupt:
        send_alert("MANUAL_STOP", {
            "symbol": instrument.symbol,
            "security_id": instrument.security_id,
            "mode": mode,
        })
        logger.info(f"[LIVE] PHANTOM manually stopped for {instrument.symbol}")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"[LIVE] Fatal error: {e}")
        sys.exit(1)


# ── Backtest routing ───────────────────────────────────────────────────────────

def run_backtest(instrument: InstrumentConfig, mode: str,
                 from_date: date, to_date: date, open_report: bool) -> None:
    """
    Run PHANTOM in backtest mode.
    Auth is skipped — uses cached or freshly fetched historical OHLCV.

    Args:
        instrument: Resolved InstrumentConfig.
        mode: Active mode string — SCALPER | SWING | BOTH.
        from_date: Start date for historical replay.
        to_date: End date for historical replay.
        open_report: If True, auto-opens HTML report in browser after run.
    """
    # Import here so live mode has zero dependency on backtest module
    from backtest.engine import BacktestEngine

    print_backtest_banner(instrument, mode, from_date, to_date)

    engine = BacktestEngine(
        instrument=instrument,
        mode=mode,
        from_date=from_date,
        to_date=to_date,
        open_report=open_report,
    )
    stats = engine.run()

    # Print summary to terminal
    print("\n" + "═" * 50)
    print(f"  PHANTOM BACKTEST COMPLETE — {instrument.symbol}")
    print("═" * 50)
    print(f"  Period       : {from_date} → {to_date}")
    print(f"  Mode         : {mode}")
    print(f"  Total Setups : {stats.total_setups}")
    print(f"  Total Trades : {stats.total_trades}")
    print(f"  Win Rate     : {stats.win_rate:.1f}%")
    print(f"  Avg R:R      : {stats.avg_rr:.2f}")
    print(f"  Profit Factor: {stats.profit_factor:.2f}")
    print(f"  Total PnL    : {stats.total_pnl_points:+.1f} pts")
    print(f"  Max Drawdown : {stats.max_drawdown_points:.1f} pts")
    print("═" * 50 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point — routes to live or backtest based on CLI args."""
    args = parse_args()

    # Resolve security ID
    security_id = args.security_id if args.security_id is not None else DEFAULT_SECURITY_ID

    # Resolve mode
    if args.SCALPER:
        mode = "SCALPER"
    elif args.SWING:
        mode = "SWING"
    else:
        mode = "BOTH"  # default, also covers --BOTH

    # Resolve instrument (may prompt user if unknown)
    instrument = resolve_instrument(security_id)

    if args.backtest:
        # ── Backtest mode ────────────────────────────────────────────────────
        today = date.today()
        if args.days:
            from_date = today - timedelta(days=args.days)
        elif args.from_date:
            from_date = date.fromisoformat(args.from_date)
        else:
            from_date = today - timedelta(days=30)
        to_date = (
            date.fromisoformat(args.to_date)
            if args.to_date
            else today - timedelta(days=1)
        )

        if from_date >= to_date:
            logger.error("--from date must be before --to date")
            sys.exit(1)

        run_backtest(instrument, mode, from_date, to_date, open_report=args.report)

    else:
        # ── Live mode ────────────────────────────────────────────────────────
        run_live(instrument, mode)


if __name__ == "__main__":
    main()
