"""
backtest/simulator.py

Replays historical candles through the same core pipeline modules
used in live mode. Tracks entry/exit/SL/TP for each setup and
produces a list of BacktestTrade objects.

No Discord alerts are sent. No Supabase writes during replay.
"""

import logging
import uuid
import traceback # FIXED: Added for full traceback output
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from tqdm import tqdm

from backtest.data_loader import Candle
from config import InstrumentConfig, MODES, CANDLE_BUFFER_SIZE, ENTRY_TYPE

logger = logging.getLogger("PHANTOM.backtest.simulator")


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class BacktestTrade:
    """Represents a single completed backtest trade.

    Attributes:
        trade_id (str): Unique identifier for the trade.
        mode (str): Trading mode, either 'SCALPER' or 'SWING'.
        symbol (str): Trading symbol.
        security_id (int): Security ID of the instrument.
        direction (str): Trade direction, 'LONG' or 'SHORT'.
        entry_time (datetime): Time of trade entry.
        entry_price (float): Execution price at entry.
        exit_time (Optional[datetime]): Time of trade exit.
        exit_price (Optional[float]): Execution price at exit.
        sl (float): Stop-loss price.
        tp1 (float): Take-profit target 1.
        tp2 (float): Take-profit target 2.
        tp3 (float): Take-profit target 3.
        outcome (str): Final outcome of the trade (e.g., 'TP1', 'SL').
        rr_achieved (float): Reward-to-risk ratio achieved.
        pnl_points (float): Profit and loss in points.
        setup_id (str): Reference to the original setup identifier.
    """
    trade_id:     str
    mode:         str           # SCALPER | SWING
    symbol:       str
    security_id:  int
    direction:    str           # LONG | SHORT
    entry_time:   datetime
    entry_price:  float
    exit_time:    Optional[datetime]
    exit_price:   Optional[float]
    sl:           float
    tp1:          float
    tp2:          float
    tp3:          float
    outcome:      str           # TP1 | TP2 | TP3 | SL | EXPIRED
    rr_achieved:  float
    pnl_points:   float
    setup_id:     str


@dataclass
class BacktestStats:
    """Aggregate statistics for a completed backtest run.

    Attributes:
        symbol (str): Trading symbol.
        security_id (int): Security ID of the instrument.
        mode (str): Active trading mode.
        from_date (str): Start date of the backtest.
        to_date (str): End date of the backtest.
        total_setups (int): Total number of valid setups identified.
        total_trades (int): Total number of trades executed.
        winners (int): Number of winning trades.
        losers (int): Number of losing trades.
        expired (int): Number of trades that expired.
        win_rate (float): Percentage of winning trades.
        avg_rr (float): Average reward-to-risk ratio.
        total_pnl_points (float): Aggregate PnL in points.
        max_drawdown_points (float): Maximum peak-to-trough drawdown.
        best_trade_points (float): PnL of the best trade.
        worst_trade_points (float): PnL of the worst trade.
        profit_factor (float): Ratio of gross wins to gross losses.
        avg_win_points (float): Average points gained on winners.
        avg_loss_points (float): Average points lost on losers.
        trades_per_day (float): Average trades executed per day.
        scalper_stats (dict): Performance breakdown for scalper mode.
        swing_stats (dict): Performance breakdown for swing mode.
    """
    symbol:              str
    security_id:         int
    mode:                str
    from_date:           str
    to_date:             str
    total_setups:        int = 0
    total_trades:        int = 0
    winners:             int = 0
    losers:              int = 0
    expired:             int = 0
    win_rate:            float = 0.0
    avg_rr:              float = 0.0
    total_pnl_points:    float = 0.0
    max_drawdown_points: float = 0.0
    best_trade_points:   float = 0.0
    worst_trade_points:  float = 0.0
    profit_factor:       float = 0.0
    avg_win_points:      float = 0.0
    avg_loss_points:     float = 0.0
    trades_per_day:      float = 0.0
    scalper_stats:       dict = field(default_factory=dict)
    swing_stats:         dict = field(default_factory=dict)


# ── Rolling buffer helper ──────────────────────────────────────────────────────

class RollingBuffer:
    """Fixed-size deque that exposes the latest N candles as a list.

    Args:
        maxlen (int): Maximum size of the buffer.
    """

    def __init__(self, maxlen: int):
        self._buf: deque = deque(maxlen=maxlen)

    def append(self, candle: Candle) -> None:
        """Add a new candle to the rolling buffer."""
        self._buf.append(candle)

    def to_list(self) -> List[Candle]:
        """Convert the buffer to a standard Python list."""
        return list(self._buf)

    def __len__(self) -> int:
        return len(self._buf)


# ── Active trade tracker ───────────────────────────────────────────────────────

@dataclass
class _ActiveTrade:
    """Internal representation of an open trade being tracked.

    Attributes:
        trade_id (str): Unique identifier.
        setup_id (str): Setup identifier.
        mode (str): SCALPER or SWING.
        direction (str): LONG or SHORT.
        entry_time (datetime): Entry timestamp.
        entry_price (float): Entry price.
        sl (float): Current stop-loss price.
        tp1 (float): Target 1.
        tp2 (float): Target 2.
        tp3 (float): Target 3.
        tp1_hit (bool): Whether TP1 has been reached.
        tp2_hit (bool): Whether TP2 has been reached.
        sl_moved_to_be (bool): Whether SL has been moved to breakeven.
        sl_moved_to_tp1 (bool): Whether SL has been moved to TP1.
    """
    trade_id:    str
    setup_id:    str
    mode:        str
    direction:   str
    entry_time:  datetime
    entry_price: float
    sl:          float
    tp1:         float
    tp2:         float
    tp3:         float
    tp1_hit:     bool = False
    tp2_hit:     bool = False
    be_hit:      bool = False  # FIXED: New 1.0R Breakeven flag
    sl_moved_to_be: bool = False
    sl_moved_to_tp1: bool = False


# ── Simulator ─────────────────────────────────────────────────────────────────

class BacktestSimulator:
    """Replays historical candles tick-by-tick through the core PHANTOM pipeline.

    The simulator shares the exact same detection logic as live mode
    by importing and calling core modules directly.

    Args:
        instrument (InstrumentConfig): Configuration for the security under test.
        mode (str): Active mode (SCALPER, SWING, or BOTH).
        candles_by_tf (Dict[str, List[Candle]]): historical data grouped by timeframe.
    """

    def __init__(
        self,
        instrument: InstrumentConfig,
        mode: str,
        candles_by_tf: Dict[str, List[Candle]],
    ):
        self.instrument = instrument
        self.mode = mode
        self.candles_by_tf = candles_by_tf

        # Determine which mode pipelines to run
        self.active_modes: List[str] = (
            ["SCALPER", "SWING"] if mode == "BOTH"
            else [mode]
        )

        # Rolling buffers per TF
        self.buffers = {
            "1m":  RollingBuffer(1000),
            "5m":  RollingBuffer(1000),
            "15m": RollingBuffer(1000),
            "1h":  RollingBuffer(1000),
        }

        # FIXED: BUG 2 — Pointer-based approach for HTF sync
        self._htf_pointers = {tf: 0 for tf in self.candles_by_tf if tf != "1m"}

        # Results
        self.trades: List[BacktestTrade] = []
        self.total_setups: int = 0

        # Active open trades (setup_id → _ActiveTrade)
        self._open_trades: Dict[str, _ActiveTrade] = {}

        # Import core modules here to mirror live pipeline
        # These are the exact same modules used in live mode
        from core.candle_engine import detect_swings
        from core.liquidity_map import build_liquidity_map, update_sweep_status
        from core.bias_engine import detect_bias
        from core.sweep_detector import detect_sweep
        from core.fvg_engine import detect_fvg, update_fvg_status
        from core.entry_engine import evaluate_entry
        from core.target_resolver import resolve_targets
        from core.setup_validator import validate_setup

        self._enrich = detect_swings
        self._build_liq = build_liquidity_map
        self._update_sweep = update_sweep_status
        self._bias = detect_bias
        self._sweep = detect_sweep
        self._fvg = detect_fvg
        self._update_fvg = update_fvg_status
        self._entry = evaluate_entry
        self._targets = resolve_targets
        self._validate = validate_setup

        # Per-mode state (sweep/fvg pending)
        self._state: Dict[str, dict] = {
            m: {
                "pending_sweep": None,
                "pending_fvg": None,
                "liquidity_map": None,
                "last_bias": "NEUTRAL",
                "fvg_formed_at": None,   # FIXED: BUG 1 — Tracking FVG formation time
                "last_pattern_ts": None, # FIXED: Tracking last processed pattern candle
                "last_bias_ts": None,    # FIXED: Tracking last processed bias candle
            }
            for m in self.active_modes
        }

    # ── Main replay entry point ────────────────────────────────────────────────

    def run(self) -> List[BacktestTrade]:
        """Run the full replay over all historical candles.

        Uses the 1m candle stream as the master clock for SCALPER,
        and 5m for SWING-only mode.

        Returns:
            List[BacktestTrade]: All completed trades from the simulation.
        """
        # Determine master clock TF
        clock_tf = "1m" if "1m" in self.candles_by_tf else "5m"
        timeline = self.candles_by_tf[clock_tf]

        logger.info(
            f"[BACKTEST] Replaying {len(timeline)} {clock_tf} candles "
            f"for {self.instrument.symbol} | Mode: {self.mode}"
        )

        for candle in tqdm(timeline, desc=f"  Replaying {self.instrument.symbol}",
                           unit="candle", ncols=80):
            # Feed candle into its TF buffer
            self.buffers[clock_tf].append(candle)

            # Also sync higher TF buffers at approximate alignment
            self._sync_htf_buffers(candle.timestamp)

            # Check open trades for SL/TP hits on this candle
            self._check_open_trades(candle)

            # Run detection pipeline for each active mode
            for mode_name in self.active_modes:
                self._run_pipeline(mode_name, candle)

        # Expire any trades still open at end of replay
        self._expire_open_trades()

        logger.info(
            f"[BACKTEST] Complete — {self.total_setups} setups, "
            f"{len(self.trades)} trades"
        )
        return self.trades

    # ── HTF buffer sync ────────────────────────────────────────────────────────

    # FIXED: BUG 2 — Pointer-based approach entirely replaces old O(n^2) loop
    def _sync_htf_buffers(self, current_ts: datetime) -> None:
        """Push latest HTF candles into buffers aligned with current clock.

        Args:
            current_ts (datetime): Current timestamp from the master clock.
        """
        for tf in self._htf_pointers:
            candles = self.candles_by_tf[tf]
            ptr = self._htf_pointers[tf]
            while ptr < len(candles) and candles[ptr].timestamp <= current_ts:
                self.buffers[tf].append(candles[ptr])
                ptr += 1
            self._htf_pointers[tf] = ptr

    # ── Pipeline per mode ─────────────────────────────────────────────────────

    def _run_pipeline(self, mode_name: str, clock_candle: Candle) -> None:
        """Execute one iteration of the PHANTOM detection pipeline.

        Args:
            mode_name (str): SCALPER or SWING mode.
            clock_candle (Candle): The current candle from the master clock.
        """
        cfg = MODES[mode_name]
        htf_bias_tf = cfg.get("htf_bias_tf", cfg["bias_tf"])
        bias_tf    = cfg["bias_tf"]
        pattern_tf = cfg["pattern_tf"]
        entry_tf   = cfg["entry_tf"]

        htf_bias_buf = self.buffers.get(htf_bias_tf, RollingBuffer(50)).to_list()
        bias_buf    = self.buffers.get(bias_tf, RollingBuffer(50)).to_list()
        pattern_buf = self.buffers.get(pattern_tf, RollingBuffer(200)).to_list()
        entry_buf   = self.buffers.get(entry_tf, RollingBuffer(200)).to_list()

        # Need minimum candles to proceed
        if len(bias_buf) < 3 or len(pattern_buf) < 3 or len(htf_bias_buf) < 3:
            return

        state = self._state[mode_name]

        try:
            # Enrich candles with swing tags + ATR (Always do this for current buffers)
            enriched_pattern = self._enrich(pattern_buf, lookback=cfg.get("swing_lookback", 5))
            enriched_bias    = self._enrich(bias_buf, lookback=cfg.get("swing_lookback", 5))
            enriched_htf_bias = self._enrich(htf_bias_buf, lookback=cfg.get("swing_lookback", 5))

            # FIXED: Only run steps 2-3 when pattern_tf has a new candle close
            new_pattern_candle = pattern_buf[-1].timestamp != state["last_pattern_ts"]
            
            if new_pattern_candle:
                # 2. Build/update liquidity map
                tolerance = cfg.get("equal_level_tolerance", 0.05) / 100.0
                liq_map = self._build_liq(enriched_pattern, tolerance=tolerance)
                state["liquidity_map"] = liq_map

                # 3. Compute bias from HTF
                bias_result = self._bias(enriched_bias)
                bias = bias_result.get("bias")
                
                # Log bias shift
                if bias != state["last_bias"]:
                    logger.info(f"[{mode_name}] Bias shift: {state['last_bias']} -> {bias} at {clock_candle.timestamp}")
                    state["last_bias"] = bias

                state["last_pattern_ts"] = pattern_buf[-1].timestamp
            else:
                # Reuse data from last pattern candle
                bias = state["last_bias"]
            
            # HTF bias check 
            htf_bias_result = self._bias(enriched_htf_bias)
            htf_bias = htf_bias_result.get("bias")

            # Check if we should enforce HTF alignment
            if not cfg.get("ignore_htf_bias", False):
                if bias == "NEUTRAL" or bias != htf_bias:
                    return
            else:
                if bias == "NEUTRAL":
                    return

            if new_pattern_candle:
                # 4. Detect sweep on pattern TF
                sweep = self._sweep(enriched_pattern, state["liquidity_map"], bias)
                if sweep:
                    logger.info(f"[{mode_name}] Sweep detected: {sweep['sweep_type']} @ {sweep['swept_level']} at {sweep['timestamp']}")
                    sweep["bias"] = bias  # Keep track of bias at time of sweep
                    state["pending_sweep"] = sweep
                    state["pending_fvg"] = None
                    state["fvg_formed_at"] = None

                # 5. Detect FVG post-sweep on pattern TF
                if state["pending_sweep"] and not state["pending_fvg"]:
                    # Re-calculate index of sweep candle to avoid staleness
                    sweep_ts = state["pending_sweep"]["timestamp"]
                    current_sweep_idx = -1
                    for idx, c in enumerate(enriched_pattern):
                        if c.timestamp == sweep_ts:
                            current_sweep_idx = idx
                            break
                    
                    if current_sweep_idx == -1:
                        # Sweep has scrolled out of buffer (timeout)
                        state["pending_sweep"] = None
                    else:
                        # Update internal index for detect_fvg
                        state["pending_sweep"]["sweep_candle_idx"] = current_sweep_idx
                        fvg = self._fvg(
                            enriched_pattern,
                            state["pending_sweep"],
                            bias,
                            cfg["fvg_displacement_atr"],
                            cfg["sweep_to_fvg_max_bars"]
                        )
                        if fvg:
                            logger.info(f"[{mode_name}] FVG formed: {fvg.type} midpoint {fvg.midpoint} at {fvg.created_at}")
                            state["pending_fvg"] = fvg
                            # FIXED: BUG 1 — Avoid entry on same candle FVG forms
                            state["fvg_formed_at"] = clock_candle.timestamp
                            self.total_setups += 1
                            return # Exit to avoid Step 6 on same tick

            # 6. Check entry retracement on entry TF (Run every 1m tick)
            if state["pending_fvg"] and len(entry_buf) >= 3:
                # FIXED: BUG 1 — Guard against same-candle entry
                if state.get("fvg_formed_at") == clock_candle.timestamp:
                    return
                    
                enriched_entry = self._enrich(entry_buf)
                entry_signal = self._entry(
                    enriched_entry,
                    state["pending_fvg"],
                    ENTRY_TYPE,
                    bias,
                    cfg["sl_buffer_atr"], # Passing ATR mult but evaluator will use mode
                    state["pending_sweep"],
                    mode_name
                )

                # FIXED: Update FVG status AFTER checking entry, so we don't reject valid closes inside the FVG
                state["pending_fvg"] = self._update_fvg(state["pending_fvg"], clock_candle)
                
                if entry_signal:
                    # 7. Resolve targets
                    targets = self._targets(
                        entry_signal["entry_price"],
                        entry_signal["sl_price"],
                        mode_name,
                        bias,
                        cfg["min_rr"],
                        state["liquidity_map"]
                    )
                    if not targets:
                        logger.warning(f"[{mode_name}] Setup INVALIDATED: Targets not resolved (RR < {cfg['min_rr']}). Entry: {entry_signal['entry_price']}, SL: {entry_signal['sl_price']}")
                        state["pending_sweep"] = None
                        state["pending_fvg"] = None
                        return

                    # 8. Validate full setup
                    setup = {
                        "mode": mode_name,
                        "bias": bias,
                        "htf_bias": htf_bias, 
                        "sweep_data": state["pending_sweep"],
                        "fvg_data": state["pending_fvg"],
                        "entry_data": entry_signal,
                        "target_data": targets,
                    }
                    valid = self._validate(setup, self.instrument)
                    if valid == "VALID":
                        self._open_trade(
                            mode_name=mode_name,
                            bias=bias,
                            entry_signal=entry_signal,
                            targets=targets,
                            timestamp=clock_candle.timestamp,
                        )
                        # Reset pending state
                        state["pending_sweep"] = None
                        state["pending_fvg"] = None
                    elif valid == "INVALID":
                        logger.warning(f"[{mode_name}] Setup INVALIDATED at entry. Reason: Validation failed (Targets/RR/Risk). Entry: {entry_signal['entry_price']}, SL: {entry_signal['sl_price']}")
                        state["pending_sweep"] = None
                        state["pending_fvg"] = None
                else:
                    # Debug why entry didn't trigger
                    pass


        except Exception as e:
            # FIXED: BUG 3 — Replace debug with warning and include traceback
            logger.warning(
                f"[{mode_name}] Pipeline error at {clock_candle.timestamp}: {e}\n"
                f"{traceback.format_exc()}"
            )

    # ── Trade lifecycle ────────────────────────────────────────────────────────

    def _open_trade(
        self,
        mode_name: str,
        bias: str,
        entry_signal: dict,
        targets: dict,
        timestamp: datetime,
    ) -> None:
        """Register a new open trade for tracking.

        Args:
            mode_name (str): SCALPER or SWING.
            bias (str): LONG or SHORT.
            entry_signal (dict): Data from the entry engine.
            targets (dict): Data from the target resolver.
            timestamp (datetime): Timestamp of entry.
        """
        setup_id = str(uuid.uuid4())[:8]
        trade = _ActiveTrade(
            trade_id=str(uuid.uuid4())[:12],
            setup_id=setup_id,
            mode=mode_name,
            direction=bias,
            entry_time=timestamp,
            entry_price=round(entry_signal["entry_price"], 2),
            sl=round(entry_signal["sl_price"], 2),
            tp1=round(targets["tp1"], 2),
            tp2=round(targets["tp2"], 2),
            tp3=round(targets["tp3"], 2),
        )
        self._open_trades[setup_id] = trade
        logger.debug(
            f"[{mode_name}] Trade opened {bias} @ {trade.entry_price} "
            f"SL={trade.sl} TP1={trade.tp1} TP3={trade.tp3}"
        )

    def _check_open_trades(self, candle: Candle) -> None:
        """Check all open trades against the current candle for SL/TP hits.

        Applies partial TP SL trail logic.

        Args:
            candle (Candle): The current candle to check against.
        """
        closed_ids = []

        # FIXED: Intraday Auto-Square-Off at session end - 15m
        end_h, end_m = map(int, self.instrument.session_end.split(':'))
        sq_off_val = end_h * 60 + end_m - 15
        current_val = candle.timestamp.hour * 60 + candle.timestamp.minute

        for setup_id, t in self._open_trades.items():
            outcome = None
            exit_price = None

            is_long = t.direction == "LONG"

            # --- EOD Square Off check ---
            if current_val >= sq_off_val:
                outcome = "EOD_SQOFF"
                exit_price = candle.close

            # --- TP3 check (full target) ---
            if outcome is None:
                if (is_long and candle.high >= t.tp3) or \
                   (not is_long and candle.low <= t.tp3):
                    outcome = "TP3"
                    exit_price = t.tp3

            # --- TP2 check ---
            if outcome is None:
                if (is_long and candle.high >= t.tp2) or \
                   (not is_long and candle.low <= t.tp2):
                    if not t.tp2_hit:
                        t.tp2_hit = True
                        # Move SL to TP1
                        t.sl = t.tp1
                        t.sl_moved_to_tp1 = True
                        logger.debug(f"TP2 hit — SL moved to TP1 ({t.tp1})")

            # --- 1.0R Breakeven check ---
            if outcome is None and not t.be_hit:
                risk = abs(t.entry_price - t.sl) if not t.sl_moved_to_be else 0 # original risk
                if risk > 0:
                    target_be = t.entry_price + risk if is_long else t.entry_price - risk
                    if (is_long and candle.high >= target_be) or \
                       (not is_long and candle.low <= target_be):
                        t.be_hit = True
                        t.sl = t.entry_price
                        t.sl_moved_to_be = True
                        logger.debug(f"1.0R hit — SL moved to breakeven ({t.entry_price})")

            # --- TP1 check ---
            if outcome is None:
                if (is_long and candle.high >= t.tp1) or \
                   (not is_long and candle.low <= t.tp1):
                    if not t.tp1_hit:
                        t.tp1_hit = True
                        # Move SL to breakeven unless already moved to TP1
                        if not t.sl_moved_to_tp1:
                            t.sl = t.entry_price
                            t.sl_moved_to_be = True
                            logger.debug(f"TP1 hit — SL moved to breakeven ({t.entry_price})")

            # --- SL check (after partial TP adjustments) ---
            if outcome is None:
                if (is_long and candle.low <= t.sl) or \
                   (not is_long and candle.high >= t.sl):
                    if t.tp2_hit:
                        outcome = "TP2"   # stopped out above TP1, counts as TP2
                        exit_price = t.tp1
                    elif t.tp1_hit:
                        outcome = "TP1"   # stopped out at breakeven
                        exit_price = t.entry_price
                    else:
                        outcome = "SL"
                        exit_price = t.sl

            if outcome:
                self._close_trade(t, outcome, exit_price, candle.timestamp)
                closed_ids.append(setup_id)

        for sid in closed_ids:
            del self._open_trades[sid]

    def _close_trade(
        self,
        t: _ActiveTrade,
        outcome: str,
        exit_price: float,
        exit_time: datetime,
    ) -> None:
        """Finalize a trade, compute PnL, and record it.

        Args:
            t (_ActiveTrade): The active trade being closed.
            outcome (str): Outcome type (e.g., TP1, TP3, SL).
            exit_price (float): Final exit price.
            exit_time (datetime): Final exit timestamp.
        """
        if t.direction == "LONG":
            full_pnl = exit_price - t.entry_price
            tp1_pnl = t.tp1 - t.entry_price
            tp3_pnl = t.tp3 - t.entry_price
        else:
            full_pnl = t.entry_price - exit_price
            tp1_pnl = t.entry_price - t.tp1
            tp3_pnl = t.entry_price - t.tp3

        if outcome == "TP1":
            # 50% booked at TP1, 50% stopped at breakeven
            pnl = round(tp1_pnl * 0.5, 2)
        elif outcome == "TP2":
            # 50% booked at TP1, 50% stopped at TP1 (SL moved to TP1)
            pnl = round(tp1_pnl, 2)
        elif outcome == "TP3":
            # 50% booked at TP1, 50% closed at TP3
            pnl = round(tp1_pnl * 0.5 + tp3_pnl * 0.5, 2)
        else:
            # Handle SL or EOD_SQOFF
            if t.tp1_hit:
                # 50% booked at TP1, remaining 50% closed at exit_price
                eod_pnl = (exit_price - t.entry_price) if t.direction == "LONG" else (t.entry_price - exit_price)
                pnl = round(tp1_pnl * 0.5 + eod_pnl * 0.5, 2)
            else:
                pnl = round(full_pnl, 2)

        risk = abs(t.entry_price - t.sl)
        rr = round(pnl / risk, 2) if risk > 0 else 0.0

        bt = BacktestTrade(
            trade_id=t.trade_id,
            setup_id=t.setup_id,
            mode=t.mode,
            symbol=self.instrument.symbol,
            security_id=self.instrument.security_id,
            direction=t.direction,
            entry_time=t.entry_time,
            entry_price=t.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 2),
            sl=t.sl,
            tp1=t.tp1,
            tp2=t.tp2,
            tp3=t.tp3,
            outcome=outcome,
            rr_achieved=rr,
            pnl_points=pnl,
        )
        self.trades.append(bt)
        logger.debug(
            f"[{t.mode}] Trade closed {outcome} "
            f"@ {exit_price} | PnL: {pnl:+.1f} pts | R:R {rr}"
        )

    def _expire_open_trades(self) -> None:
        """Mark all still-open trades as EXPIRED at end of replay."""
        for t in self._open_trades.values():
            bt = BacktestTrade(
                trade_id=t.trade_id,
                setup_id=t.setup_id,
                mode=t.mode,
                symbol=self.instrument.symbol,
                security_id=self.instrument.security_id,
                direction=t.direction,
                entry_time=t.entry_time,
                entry_price=t.entry_price,
                exit_time=None,
                exit_price=None,
                sl=t.sl,
                tp1=t.tp1,
                tp2=t.tp2,
                tp3=t.tp3,
                outcome="EXPIRED",
                rr_achieved=0.0,
                pnl_points=0.0,
            )
            self.trades.append(bt)
        if self._open_trades:
            logger.info(f"[BACKTEST] {len(self._open_trades)} trades expired at session end")
        self._open_trades.clear()
