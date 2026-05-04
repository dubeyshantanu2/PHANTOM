# Module core.target_resolver

## Function `resolve_targets`
Calculates profit targets and validates the risk-to-reward ratio.

Determines three Take Profit (TP) levels based on risk multiples 
tailored to the specific trading mode (Scalper vs Swing).

Args:
    entry_price (float): The calculated entry level.
    sl_price (float): The calculated stop loss level.
    mode (str): Trading mode ("SCALPER" or "SWING").
    bias (str): Current market bias ("LONG" or "SHORT").
    min_rr (float): Minimum required Risk:Reward ratio.
    lmap (Any): Current LiquidityMap (placeholder for pool-based targets).

Returns:
    Optional[Dict[str, Any]]: A dictionary containing targets if RR is valid:
        - tp1, tp2, tp3 (float): Calculated profit levels.
        - rr_ratio (float): The final Risk:Reward ratio.
        - target_type (str): Label for the target logic used.

