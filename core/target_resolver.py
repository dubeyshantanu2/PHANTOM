from typing import Dict, Any, Optional

def resolve_targets(entry_price: float, sl_price: float, mode: str, bias: str, min_rr: float, lmap: Any) -> Optional[Dict[str, Any]]:
    """
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
    """
    risk = abs(entry_price - sl_price)
    if risk == 0: return None
    
    # Standard R-multiple targets
    if mode == "SCALPER":
        tp1_std = entry_price + risk * 1.5 if bias == "LONG" else entry_price - risk * 1.5
        tp2_std = entry_price + risk * 2.5 if bias == "LONG" else entry_price - risk * 2.5
        tp3_std = entry_price + risk * 4.0 if bias == "LONG" else entry_price - risk * 4.0
    else: # SWING
        tp1_std = entry_price + risk * 2.0 if bias == "LONG" else entry_price - risk * 2.0
        tp2_std = entry_price + risk * 3.5 if bias == "LONG" else entry_price - risk * 3.5
        tp3_std = entry_price + risk * 5.0 if bias == "LONG" else entry_price - risk * 5.0

    target_type = "STANDARD"
    tp1, tp2, tp3 = tp1_std, tp2_std, tp3_std

    # FIXED: BUG 7B — Use liquidity pools from lmap as real targets
    if lmap is not None:
        pools = []
        if bias == "LONG" and hasattr(lmap, "bsl"):
            # Look for nearest BSL pool ABOVE entry price
            pools = sorted([p.price for p in lmap.bsl if p.price > entry_price and p.state == "INTACT"])
        elif bias == "SHORT" and hasattr(lmap, "ssl"):
            # Look for nearest SSL pool BELOW entry price
            pools = sorted([p.price for p in lmap.ssl if p.price < entry_price and p.state == "INTACT"], reverse=True)
            
        if pools:
            pool_tp1 = pools[0]
            # If pool is closer than standard TP1, use it as TP1 ONLY if it meets min_rr
            pool_rr = abs(pool_tp1 - entry_price) / risk
            if abs(pool_tp1 - entry_price) < abs(tp1_std - entry_price) and pool_rr >= min_rr:
                tp1 = pool_tp1
                target_type = "LIQUIDITY_POOL"
                # Keep original TP2/TP3 for now, or could adjust them too

    # FIXED: BUG 7A — Min RR check should be on TP1 (first achievable target)
    rr_to_tp1 = abs(tp1 - entry_price) / risk
    if rr_to_tp1 < min_rr:
        return None
        
    # FIXED: Minimum distance check
    if abs(tp1 - entry_price) < abs(entry_price - sl_price) * 0.5:
        return None  # TP1 too close to be worth the trade

    rr_ratio = abs(tp3 - entry_price) / risk
        
    return {
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "tp3": round(tp3, 2),
        "rr_ratio": round(rr_ratio, 2),
        "target_type": target_type
    }
