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
    
    if mode == "SCALPER":
        tp1 = entry_price + risk * 1.5 if bias == "LONG" else entry_price - risk * 1.5
        tp2 = entry_price + risk * 2.5 if bias == "LONG" else entry_price - risk * 2.5
        tp3 = entry_price + risk * 4.0 if bias == "LONG" else entry_price - risk * 4.0
    else: # SWING
        tp1 = entry_price + risk * 2.0 if bias == "LONG" else entry_price - risk * 2.0
        tp2 = entry_price + risk * 3.5 if bias == "LONG" else entry_price - risk * 3.5
        tp3 = entry_price + risk * 5.0 if bias == "LONG" else entry_price - risk * 5.0

    rr_ratio = abs(tp3 - entry_price) / risk
    if rr_ratio < min_rr:
        return None
        
    return {
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "tp3": round(tp3, 2),
        "rr_ratio": round(rr_ratio, 2),
        "target_type": "STANDARD"
    }
