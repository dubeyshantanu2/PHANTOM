import logging
from typing import Dict, Any
from core.bias_engine import detect_bias
from core.liquidity_map import build_liquidity_map, update_sweep_status
from core.sweep_detector import detect_sweep
from core.fvg_engine import detect_fvg
from core.entry_engine import evaluate_entry
from core.target_resolver import resolve_targets
from core.setup_validator import validate_setup
from output.discord_alert import send_alert
from data.store import save_setup, update_setup_state
from config import InstrumentConfig, MODES, ENTRY_TYPE

logger = logging.getLogger(__name__)

class ModePipeline:
    """
    Manages the lifecycle of a trading strategy setup for a specific mode.

    The pipeline operates as a state machine, transitioning through phases like
    BIAS_CONFIRMED, LIQUIDITY_MAPPED, SWEEP_DETECTED, etc., as price action
    satisfies internal algorithm criteria.

    Attributes:
        mode (str): The trading mode (e.g., "SCALPER", "SWING").
        config (Dict[str, Any]): Mode-specific parameters (timeframes, buffers).
        instrument (InstrumentConfig): Configuration for the traded instrument.
        state (str): Current state of the pipeline machine.
        setup_data (dict): Collection of extracted data for the current setup.
        setup_id (str|None): Database ID for the current setup.
        lmap (LiquidityMap|None): The calculated liquidity map for the session.
    """
    def __init__(self, mode: str, config: Dict[str, Any], instrument: InstrumentConfig, dry_run: bool = False):
        """
        Initializes the pipeline with mode-specific configurations.

        Args:
            mode (str): The trading mode.
            config (Dict[str, Any]): Parameters for this mode.
            instrument (InstrumentConfig): Details of the instrument being traded.
            dry_run (bool): If True, disables database saving and Discord alerts (for backtesting).
        """
        self.mode = mode
        self.config = config
        self.instrument = instrument
        self.dry_run = dry_run
        self.state = "IDLE"
        self.setup_data = {}
        self.setup_id = None
        self.lmap = None
        self.setups_found = []  # To collect results during backtest

    def tick(self, feed_manager):
        """
        Executes a single cycle of the pipeline's logic.

        Fetches new data feeds, processes metrics through the state machine,
        and triggers alerts/persistence when state changes occur.

        Args:
            feed_manager (FeedManager): The object responsible for fetching OHLCV data.
        """
        # Store current timestamp for backtest reporting
        if hasattr(feed_manager, 'cursor_timestamp'):
            self.setup_data["current_ts"] = feed_manager.cursor_timestamp

        # 1. Fetch candles
        htf_bias_tf = self.config.get("htf_bias_tf", self.config["bias_tf"])
        htf_bias_candles = feed_manager.get_candles(self.instrument, htf_bias_tf, 50)
        bias_candles = feed_manager.get_candles(self.instrument, self.config["bias_tf"], 50)
        pattern_candles = feed_manager.get_candles(self.instrument, self.config["pattern_tf"], 50)
        entry_candles = feed_manager.get_candles(self.instrument, self.config["entry_tf"], 50)

        # 2. State Machine
        if self.state == "IDLE":
            enriched_bias = detect_swings(bias_candles, lookback=self.config.get("swing_lookback", 3))
            bias_res = detect_bias(enriched_bias)
            if bias_res["bias"] != "NEUTRAL":
                self.setup_data["bias"] = bias_res["bias"]
                self.setup_data["bias_data"] = bias_res
                self.state = "BIAS_CONFIRMED"
                logger.info(f"{self.instrument.symbol} [{self.mode}] Bias Confirmed: {bias_res['bias']}")

        elif self.state == "BIAS_CONFIRMED":
            enriched_pattern = detect_swings(pattern_candles, lookback=self.config.get("swing_lookback", 3))
            tolerance = self.config.get("equal_level_tolerance", 0.05) / 100.0
            self.lmap = build_liquidity_map(enriched_pattern, tolerance=tolerance)
            if self.lmap:
                self.state = "LIQUIDITY_MAPPED"

        elif self.state == "LIQUIDITY_MAPPED":
            enriched_pattern = detect_swings(pattern_candles, lookback=self.config.get("swing_lookback", 3))
            sweep = detect_sweep(enriched_pattern, self.lmap, self.setup_data["bias"])
            if sweep:
                self.setup_data["sweep_data"] = sweep
                self.state = "SWEEP_DETECTED"
                logger.info(f"{self.instrument.symbol} [{self.mode}] Sweep Detected: {sweep['sweep_type']}")

        elif self.state == "SWEEP_DETECTED":
            enriched_pattern = detect_swings(pattern_candles, lookback=self.config.get("swing_lookback", 3))
            fvg = detect_fvg(enriched_pattern, self.setup_data["sweep_data"], self.setup_data["bias"],
                             self.config["fvg_displacement_atr"], self.config["sweep_to_fvg_max_bars"])
            if fvg:
                self.setup_data["fvg_data"] = fvg
                self.state = "FVG_FORMED"
                self._prepare_setup_dict("FVG_FORMED")
                if not self.dry_run:
                    send_alert("FVG_FORMED", self.setup_data["dict"])
                    self.setup_id = save_setup(self.setup_data["dict"])
                else:
                    logger.info(f"Backtest: Setup FVG_FORMED for {self.instrument.symbol}")

        elif self.state == "FVG_FORMED":
            enriched_entry = detect_swings(entry_candles, lookback=self.config.get("swing_lookback", 3))
            entry = evaluate_entry(enriched_entry, self.setup_data["fvg_data"], ENTRY_TYPE, 
                                   self.setup_data["bias"], self.config["sl_buffer_points"], 
                                   self.setup_data["sweep_data"])
            if entry:
                self.setup_data["entry_data"] = entry
                targets = resolve_targets(entry["entry_price"], entry["sl_price"], self.mode, 
                                          self.setup_data["bias"], self.config["min_rr"], self.lmap)
                if targets:
                    enriched_htf = detect_swings(htf_bias_candles, lookback=self.config.get("swing_lookback", 3))
                    htf_bias_res = detect_bias(enriched_htf)
                    self.setup_data["htf_bias"] = htf_bias_res["bias"]
                    self.setup_data["target_data"] = targets
                    
                    # Validate before proceeding
                    setup_for_validation = {
                        "bias": self.setup_data["bias"],
                        "htf_bias": self.setup_data["htf_bias"],
                        "sweep_data": self.setup_data["sweep_data"],
                        "fvg_data": self.setup_data["fvg_data"],
                        "entry_data": self.setup_data["entry_data"],
                        "target_data": self.setup_data["target_data"],
                    }
                    if validate_setup(setup_for_validation, self.instrument) == "VALID":
                        self.state = "ENTRY_ZONE"
                        self._prepare_setup_dict("ENTRY_ZONE")
                        if not self.dry_run:
                            send_alert("ENTRY_ZONE", self.setup_data["dict"])
                            update_setup_state(self.setup_id, "ENTRY_ZONE")
                        else:
                            logger.info(f"Backtest: Setup ENTRY_ZONE for {self.instrument.symbol}")
                            self.setups_found.append(self.setup_data["dict"])
                    else:
                        self.state = "INVALIDATED"
                        self._prepare_setup_dict("INVALIDATED")
                        self.setup_data["dict"]["reason"] = "HTF Alignment or RR fail"
                        if not self.dry_run:
                            send_alert("INVALIDATED", self.setup_data["dict"])
                            update_setup_state(self.setup_id, "INVALIDATED", "VALIDATION_FAIL")
                        self.reset()
                else:
                    self.state = "INVALIDATED"
                    self._prepare_setup_dict("INVALIDATED")
                    self.setup_data["dict"]["reason"] = "RR < min_rr"
                    if not self.dry_run:
                        send_alert("INVALIDATED", self.setup_data["dict"])
                        update_setup_state(self.setup_id, "INVALIDATED", "RR_FAIL")
                    self.reset()

        # In a complete system, you'd track active trades for TP/SL hits here

    def _prepare_setup_dict(self, state: str):
        """
        Formats internal setup data into a flat dictionary for alerts/storage.

        Args:
            state (str): The current state name to include in the dictionary.
        """
        bias_tf = self.config["bias_tf"]
        pattern_tf = self.config["pattern_tf"]
        entry_tf = self.config["entry_tf"]
        
        self.setup_data["dict"] = {
            "security_id": self.instrument.security_id,
            "symbol": self.instrument.symbol,
            "mode": self.mode,
            "bias": self.setup_data.get("bias", "UNKNOWN"),
            "bias_tf": bias_tf,
            "pattern_tf": pattern_tf,
            "entry_tf": entry_tf,
            "state": state
        }
        
        if "current_ts" in self.setup_data:
            ts = self.setup_data["current_ts"]
            self.setup_data["dict"]["timestamp"] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
        
        if "sweep_data" in self.setup_data:
            self.setup_data["dict"]["sweep_type"] = self.setup_data["sweep_data"]["sweep_type"]
            self.setup_data["dict"]["sweep_price"] = self.setup_data["sweep_data"]["swept_level"]
            
        if "fvg_data" in self.setup_data:
            self.setup_data["dict"]["fvg_top"] = self.setup_data["fvg_data"].top
            self.setup_data["dict"]["fvg_bottom"] = self.setup_data["fvg_data"].bottom
            
        if "entry_data" in self.setup_data:
            self.setup_data["dict"]["entry_price"] = self.setup_data["entry_data"]["entry_price"]
            self.setup_data["dict"]["sl"] = self.setup_data["entry_data"]["sl_price"]
            self.setup_data["dict"]["entry_type"] = self.setup_data["entry_data"]["entry_type"]
            
        if "target_data" in self.setup_data:
            self.setup_data["dict"]["tp1"] = self.setup_data["target_data"]["tp1"]
            self.setup_data["dict"]["tp2"] = self.setup_data["target_data"]["tp2"]
            self.setup_data["dict"]["tp3"] = self.setup_data["target_data"]["tp3"]
            self.setup_data["dict"]["rr"] = self.setup_data["target_data"]["rr_ratio"]

    def reset(self):
        """Resets the pipeline state and data for a new cycle."""
        self.state = "IDLE"
        self.setup_data = {}
        self.setup_id = None
        self.lmap = None

class ModeController:
    """
    Orchestrates multiple ModePipelines for a single instrument.

    Coordinates the execution of different strategies (Scalper, Swing)
    simultaneously.
    """
    def __init__(self, instrument: InstrumentConfig, active_mode: str, dry_run: bool = False):
        """
        Initializes pipelines based on the requested active modes.

        Args:
            instrument (InstrumentConfig): Configuration for the traded instrument.
            active_mode (str): The mode(s) to activate ("SCALPER", "SWING", "BOTH").
            dry_run (bool): If True, all child pipelines will be in dry_run mode.
        """
        self.pipelines = []
        if active_mode in ["SCALPER", "BOTH"]:
            self.pipelines.append(ModePipeline("SCALPER", MODES["SCALPER"], instrument, dry_run=dry_run))
        if active_mode in ["SWING", "BOTH"]:
            self.pipelines.append(ModePipeline("SWING", MODES["SWING"], instrument, dry_run=dry_run))

    def tick_all(self, feed_manager):
        """
        Triggers a tick for all active pipelines.

        Args:
            feed_manager (FeedManager): Data feed manager.
        """
        for p in self.pipelines:
            p.tick(feed_manager)
