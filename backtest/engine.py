"""
backtest/engine.py

Orchestrates a full PHANTOM backtest run:
  1. Loads historical data via data_loader
  2. Runs the simulator
  3. Computes BacktestStats
  4. Persists results to Supabase
  5. Triggers HTML report generation
"""

import logging
import os
import uuid
import webbrowser
from datetime import date
from typing import List, Optional

from config import InstrumentConfig
from backtest.data_loader import load_historical
from backtest.simulator import BacktestSimulator, BacktestStats, BacktestTrade

logger = logging.getLogger("PHANTOM.backtest.engine")


def _compute_stats(
    trades: List[BacktestTrade],
    total_setups: int,
    instrument: InstrumentConfig,
    mode: str,
    from_date: date,
    to_date: date,
) -> BacktestStats:
    """
    Compute aggregate BacktestStats from a list of BacktestTrade objects.

    Args:
        trades: All completed trades from the simulator.
        total_setups: Total setups identified (including those that never reached entry).
        instrument: InstrumentConfig for the security.
        mode: Active mode string.
        from_date: Backtest start date.
        to_date: Backtest end date.

    Returns:
        Populated BacktestStats dataclass.
    """
    stats = BacktestStats(
        symbol=instrument.symbol,
        security_id=instrument.security_id,
        mode=mode,
        from_date=str(from_date),
        to_date=str(to_date),
        total_setups=total_setups,
        total_trades=len(trades),
    )

    if not trades:
        return stats

    winners  = [t for t in trades if t.outcome in ("TP1", "TP2", "TP3")]
    losers   = [t for t in trades if t.outcome == "SL"]
    expired  = [t for t in trades if t.outcome == "EXPIRED"]

    stats.winners = len(winners)
    stats.losers  = len(losers)
    stats.expired = len(expired)

    completed = [t for t in trades if t.outcome != "EXPIRED"]

    if completed:
        stats.win_rate = round(len(winners) / len(completed) * 100, 1)
        stats.avg_rr   = round(sum(t.rr_achieved for t in completed) / len(completed), 2)

    stats.total_pnl_points = round(sum(t.pnl_points for t in trades), 2)

    if winners:
        stats.avg_win_points  = round(sum(t.pnl_points for t in winners) / len(winners), 2)
        stats.best_trade_points = round(max(t.pnl_points for t in winners), 2)

    if losers:
        stats.avg_loss_points  = round(sum(t.pnl_points for t in losers) / len(losers), 2)
        stats.worst_trade_points = round(min(t.pnl_points for t in losers), 2)

    gross_wins   = sum(t.pnl_points for t in winners) if winners else 0
    gross_losses = abs(sum(t.pnl_points for t in losers)) if losers else 0
    stats.profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else 0.0

    # Max drawdown: running peak equity → deepest trough
    equity = 0.0
    peak   = 0.0
    max_dd = 0.0
    for t in sorted(trades, key=lambda x: x.entry_time or from_date):
        equity += t.pnl_points
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    stats.max_drawdown_points = round(max_dd, 2)

    # Trades per day
    total_days = max((to_date - from_date).days, 1)
    stats.trades_per_day = round(len(completed) / total_days, 2)

    # Per-mode breakdown if BOTH
    if mode == "BOTH":
        scalper_trades = [t for t in trades if t.mode == "SCALPER"]
        swing_trades   = [t for t in trades if t.mode == "SWING"]
        stats.scalper_stats = _mode_breakdown(scalper_trades)
        stats.swing_stats   = _mode_breakdown(swing_trades)

    return stats


def _mode_breakdown(trades: List[BacktestTrade]) -> dict:
    """Compute a simplified stats dict for a subset of trades."""
    if not trades:
        return {}
    completed = [t for t in trades if t.outcome != "EXPIRED"]
    winners   = [t for t in completed if t.outcome in ("TP1", "TP2", "TP3")]
    losers    = [t for t in completed if t.outcome == "SL"]
    gross_w   = sum(t.pnl_points for t in winners)
    gross_l   = abs(sum(t.pnl_points for t in losers))
    return {
        "total_trades":   len(trades),
        "winners":        len(winners),
        "losers":         len(losers),
        "win_rate":       round(len(winners) / len(completed) * 100, 1) if completed else 0,
        "avg_rr":         round(sum(t.rr_achieved for t in completed) / len(completed), 2) if completed else 0,
        "total_pnl":      round(sum(t.pnl_points for t in trades), 2),
        "profit_factor":  round(gross_w / gross_l, 2) if gross_l > 0 else 0,
    }


def _save_to_supabase(
    run_id: str,
    stats: BacktestStats,
    trades: List[BacktestTrade],
) -> None:
    """
    Persist backtest results to Supabase (backtest_runs + backtest_trades).
    Silently skips if Supabase env vars are not configured.

    Args:
        run_id: UUID string for this backtest run.
        stats: Computed BacktestStats.
        trades: All BacktestTrade objects.
    """
    try:
        from data.store import StoreManager
        store = StoreManager()

        # Save summary row
        store.save_backtest_run(run_id, stats)

        # Save individual trades in batches of 100
        batch = []
        for t in trades:
            batch.append({
                "run_id":       run_id,
                "trade_id":     t.trade_id,
                "mode":         t.mode,
                "symbol":       t.symbol,
                "security_id":  t.security_id,
                "entry_time":   t.entry_time.isoformat() if t.entry_time else None,
                "entry_price":  t.entry_price,
                "exit_time":    t.exit_time.isoformat() if t.exit_time else None,
                "exit_price":   t.exit_price,
                "sl":           t.sl,
                "tp1":          t.tp1,
                "tp2":          t.tp2,
                "tp3":          t.tp3,
                "outcome":      t.outcome,
                "rr_achieved":  t.rr_achieved,
                "pnl_points":   t.pnl_points,
            })
            if len(batch) >= 100:
                store.save_backtest_trades_bulk(batch)
                batch = []
        if batch:
            store.save_backtest_trades_bulk(batch)

        logger.info(f"[BACKTEST] Results saved to Supabase (run_id={run_id})")

    except Exception as e:
        logger.warning(f"[BACKTEST] Supabase save skipped: {e}")


# ── Engine ─────────────────────────────────────────────────────────────────────

class BacktestEngine:
    """
    Top-level orchestrator for a PHANTOM backtest run.

    Args:
        instrument: Resolved InstrumentConfig.
        mode: Active mode — SCALPER | SWING | BOTH.
        from_date: Backtest start date.
        to_date: Backtest end date.
        open_report: If True, open HTML report in browser after completion.
    """

    def __init__(
        self,
        instrument: InstrumentConfig,
        mode: str,
        from_date: date,
        to_date: date,
        open_report: bool = False,
    ):
        self.instrument   = instrument
        self.mode         = mode
        self.from_date    = from_date
        self.to_date      = to_date
        self.open_report  = open_report
        self.run_id       = str(uuid.uuid4())

    def run(self) -> BacktestStats:
        """
        Execute the full backtest pipeline.

        Returns:
            BacktestStats with all computed metrics.
        """
        logger.info(
            f"[BACKTEST] Starting run {self.run_id} | "
            f"{self.instrument.symbol} | {self.mode} | "
            f"{self.from_date} → {self.to_date}"
        )

        # Step 1 — Load historical data
        # Auth is required to fetch from Dhan if not cached
        candles_by_tf = self._load_data()
        if not candles_by_tf:
            logger.error("[BACKTEST] No historical data loaded — aborting")
            return BacktestStats(
                symbol=self.instrument.symbol,
                security_id=self.instrument.security_id,
                mode=self.mode,
                from_date=str(self.from_date),
                to_date=str(self.to_date),
            )

        # Step 2 — Run simulator
        simulator = BacktestSimulator(
            instrument=self.instrument,
            mode=self.mode,
            candles_by_tf=candles_by_tf,
        )
        trades = simulator.run()

        # Step 3 — Compute stats
        stats = _compute_stats(
            trades=trades,
            total_setups=simulator.total_setups,
            instrument=self.instrument,
            mode=self.mode,
            from_date=self.from_date,
            to_date=self.to_date,
        )

        # Step 4 — Persist to Supabase
        _save_to_supabase(self.run_id, stats, trades)

        # Step 5 — Generate HTML report
        report_path = self._generate_report(stats, trades)
        if report_path and self.open_report:
            webbrowser.open(f"file://{os.path.abspath(report_path)}")
            logger.info(f"[BACKTEST] Report opened: {report_path}")

        return stats

    def _load_data(self):
        """Load historical candles, using auth only if cache misses."""
        try:
            from auth import get_dhan_client
            dhan_client = get_dhan_client()
        except Exception as e:
            logger.warning(f"[BACKTEST] Auth failed ({e}) — will use cache only")
            dhan_client = None

        from backtest.data_loader import load_historical
        return load_historical(
            dhan_client=dhan_client,
            instrument=self.instrument,
            mode=self.mode,
            from_date=self.from_date,
            to_date=self.to_date,
        )

    def _generate_report(
        self,
        stats: BacktestStats,
        trades: List[BacktestTrade],
    ) -> Optional[str]:
        """Generate and save the HTML report. Returns file path or None."""
        try:
            from backtest.report import generate_report
            return generate_report(
                stats=stats,
                trades=trades,
                run_id=self.run_id,
            )
        except Exception as e:
            logger.error(f"[BACKTEST] Report generation failed: {e}")
            return None
