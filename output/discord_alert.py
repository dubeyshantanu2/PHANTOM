import os
import requests
import logging

logger = logging.getLogger(__name__)
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

def send_alert(state: str, setup_dict: dict):
    """
    Formats and sends a system alert to the configured Discord channel.

    Constructs a human-readable message based on the pipeline state and
    the current setup data.

    Args:
        state (str): The current state of the setup (e.g., "FVG_FORMED", 
            "ENTRY_ZONE").
        setup_dict (dict): Flat dictionary containing all setup context.
    """
    if not webhook_url:
        return
        
    symbol = setup_dict.get("symbol", "UNKNOWN")
    mode = setup_dict.get("mode", "UNKNOWN")
    security_id = setup_dict.get("security_id", "")
    
    content = ""
    
    if state == "FVG_FORMED":
        content = f"🔵 [PHANTOM-{mode}] Setup Brewing\nSymbol : {symbol} (ID: {security_id})\nTF     : {setup_dict.get('pattern_tf')}\nSweep  : {setup_dict.get('sweep_type')} @ {setup_dict.get('sweep_price')}\nFVG    : {setup_dict.get('fvg_bottom')} - {setup_dict.get('fvg_top')}\nWaiting for retracement..."
    
    elif state == "ENTRY_ZONE":
        content = f"🟢 [PHANTOM-{mode}] ENTRY ZONE HIT\nSymbol : {symbol} (ID: {security_id})\nEntry  : {setup_dict.get('entry_price')} | SL: {setup_dict.get('sl')}\nTP1: {setup_dict.get('tp1')} | TP2: {setup_dict.get('tp2')} | TP3: {setup_dict.get('tp3')}\nR:R    : {setup_dict.get('rr')} | Type: {setup_dict.get('entry_type')}"
        
    elif state == "PARTIAL_TP":
        content = f"🟡 [PHANTOM-{mode}] TP1 HIT — Move SL to Breakeven\nSymbol : {symbol} | TP1: {setup_dict.get('tp1')} hit @ {setup_dict.get('price')}"
        
    elif state == "TARGET_HIT":
        content = f"✅ [PHANTOM-{mode}] TARGET HIT\nSymbol : {symbol} | R:R achieved: {setup_dict.get('rr')}"
        
    elif state == "INVALIDATED":
        content = f"🔴 [PHANTOM-{mode}] INVALIDATED\nSymbol : {symbol} | Reason: {setup_dict.get('reason', 'Conditions failed')}"
        
    elif state == "SESSION_END":
        content = f"⏹️ [PHANTOM] Session ended for {symbol}\nTime: {setup_dict.get('current_time')} IST | Setups today: {setup_dict.get('count', 0)}"

    if content:
        try:
            requests.post(webhook_url, json={"content": content})
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
