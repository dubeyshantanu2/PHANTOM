# Module core.mode_controller

## Class `ModeController`
Orchestrates multiple ModePipelines for a single instrument.

Coordinates the execution of different strategies (Scalper, Swing)
simultaneously.

### Method `__init__`
Initializes pipelines based on the requested active modes.

Args:
    instrument (InstrumentConfig): Configuration for the traded instrument.
    active_mode (str): The mode(s) to activate ("SCALPER", "SWING", "BOTH").
    dry_run (bool): If True, all child pipelines will be in dry_run mode.

### Method `tick_all`
Triggers a tick for all active pipelines.

Args:
    feed_manager (FeedManager): Data feed manager.

## Class `ModePipeline`
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

### Method `__init__`
Initializes the pipeline with mode-specific configurations.

Args:
    mode (str): The trading mode.
    config (Dict[str, Any]): Parameters for this mode.
    instrument (InstrumentConfig): Details of the instrument being traded.
    dry_run (bool): If True, disables database saving and Discord alerts (for backtesting).

### Method `reset`
Resets the pipeline state and data for a new cycle.

### Method `tick`
Executes a single cycle of the pipeline's logic.

Fetches new data feeds, processes metrics through the state machine,
and triggers alerts/persistence when state changes occur.

Args:
    feed_manager (FeedManager): The object responsible for fetching OHLCV data.

