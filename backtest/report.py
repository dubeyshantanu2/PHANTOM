"""
backtest/report.py

Generates a self-contained single-file HTML backtest report.
Uses Chart.js (CDN) for all charts. No external dependencies needed
to view the report — open the .html file in any browser.

Output: backtest/reports/{symbol}_{from}_{to}_{mode}_{run_id[:8]}.html
"""

import json
import logging
import os
from datetime import datetime
from typing import List

from backtest.simulator import BacktestStats, BacktestTrade

logger = logging.getLogger("PHANTOM.backtest.report")

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def _outcome_color(outcome: str) -> str:
    return {
        "TP3": "#22c55e",
        "TP2": "#4ade80",
        "TP1": "#86efac",
        "SL":  "#f87171",
        "EXPIRED": "#9ca3af",
    }.get(outcome, "#9ca3af")


def _trade_row(i: int, t: BacktestTrade) -> str:
    entry_str = t.entry_time.strftime("%d %b %H:%M") if t.entry_time else "—"
    exit_str  = t.exit_time.strftime("%d %b %H:%M") if t.exit_time else "—"
    exit_px   = f"{t.exit_price:.2f}" if t.exit_price else "—"
    pnl_sign  = "+" if t.pnl_points >= 0 else ""
    return f"""
    <tr>
      <td>{i}</td>
      <td>{entry_str}</td>
      <td><span class="badge {'badge-scalper' if t.mode=='SCALPER' else 'badge-swing'}">{t.mode}</span></td>
      <td><span class="badge {'badge-long' if t.direction=='LONG' else 'badge-short'}">{t.direction}</span></td>
      <td>{t.entry_price:.2f}</td>
      <td>{t.sl:.2f}</td>
      <td>{t.tp1:.2f}</td>
      <td>{t.tp2:.2f}</td>
      <td>{t.tp3:.2f}</td>
      <td>{exit_px}</td>
      <td>{exit_str}</td>
      <td><span style="color:{_outcome_color(t.outcome)};font-weight:700">{t.outcome}</span></td>
      <td>{t.rr_achieved:.2f}</td>
      <td style="font-weight:700;color:{'#4ade80' if t.pnl_points>=0 else '#f87171'}">{pnl_sign}{t.pnl_points:.1f}</td>
    </tr>"""


def _equity_curve_data(trades: List[BacktestTrade]):
    """Build cumulative PnL data series, split by mode."""
    all_sorted = sorted(
        [t for t in trades if t.entry_time],
        key=lambda t: t.entry_time
    )
    labels, all_eq, scalper_eq, swing_eq = [], [], [], []
    cum = cum_s = cum_sw = 0.0
    for t in all_sorted:
        cum += t.pnl_points
        labels.append(t.entry_time.strftime("%d %b %H:%M"))
        all_eq.append(round(cum, 2))
        if t.mode == "SCALPER":
            cum_s += t.pnl_points
            scalper_eq.append(round(cum_s, 2))
            swing_eq.append(None)
        else:
            cum_sw += t.pnl_points
            swing_eq.append(round(cum_sw, 2))
            scalper_eq.append(None)
    return labels, all_eq, scalper_eq, swing_eq


def _drawdown_data(trades: List[BacktestTrade]):
    """Build per-trade drawdown series from peak equity."""
    sorted_trades = sorted(
        [t for t in trades if t.entry_time],
        key=lambda t: t.entry_time
    )
    labels, dd_series = [], []
    equity = peak = 0.0
    for t in sorted_trades:
        equity += t.pnl_points
        peak = max(peak, equity)
        dd_series.append(round(-(peak - equity), 2))
        labels.append(t.entry_time.strftime("%d %b %H:%M"))
    return labels, dd_series


def _outcome_pie_data(trades: List[BacktestTrade]):
    counts = {"TP3": 0, "TP2": 0, "TP1": 0, "SL": 0, "EXPIRED": 0}
    for t in trades:
        counts[t.outcome] = counts.get(t.outcome, 0) + 1
    return list(counts.keys()), list(counts.values())


def _trades_by_hour(trades: List[BacktestTrade]):
    hours = {h: 0 for h in range(24)}
    for t in trades:
        if t.entry_time:
            hours[t.entry_time.hour] += 1
    return [f"{h:02d}:00" for h in range(24)], [hours[h] for h in range(24)]


def _trades_by_dow(trades: List[BacktestTrade]):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts = [0] * 7
    for t in trades:
        if t.entry_time:
            counts[t.entry_time.weekday()] += 1
    return days, counts


def _mode_card(label: str, d: dict) -> str:
    if not d:
        return ""
    return f"""
    <div class="mode-card">
      <h4>{label}</h4>
      <div class="stat-row"><span>Trades</span><strong>{d.get('total_trades',0)}</strong></div>
      <div class="stat-row"><span>Win Rate</span><strong>{d.get('win_rate',0):.1f}%</strong></div>
      <div class="stat-row"><span>Avg R:R</span><strong>{d.get('avg_rr',0):.2f}</strong></div>
      <div class="stat-row"><span>Profit Factor</span><strong>{d.get('profit_factor',0):.2f}</strong></div>
      <div class="stat-row"><span>Total PnL</span><strong>{d.get('total_pnl',0):+.1f} pts</strong></div>
    </div>"""


def generate_report(
    stats: BacktestStats,
    trades: List[BacktestTrade],
    run_id: str,
) -> str:
    """Generate a self-contained HTML backtest report and save it to disk.

    Args:
        stats (BacktestStats): Computed BacktestStats.
        trades (List[BacktestTrade]): All BacktestTrade objects from the simulator.
        run_id (str): UUID string for this run (used in filename).

    Returns:
        str: Absolute path to the generated HTML file.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    fname = (
        f"{stats.symbol}_{stats.from_date}_{stats.to_date}"
        f"_{stats.mode}_{run_id[:8]}.html"
    )
    out_path = os.path.join(REPORTS_DIR, fname)

    # Chart data
    eq_labels, all_eq, sc_eq, sw_eq = _equity_curve_data(trades)
    dd_labels, dd_data = _drawdown_data(trades)
    pie_labels, pie_data = _outcome_pie_data(trades)
    hour_labels, hour_data = _trades_by_hour(trades)
    dow_labels, dow_data = _trades_by_dow(trades)

    # Trade table rows
    trade_rows = "".join(_trade_row(i + 1, t) for i, t in enumerate(
        sorted(trades, key=lambda t: t.entry_time or datetime.min)
    ))

    # Mode comparison cards
    mode_cards = ""
    if stats.mode == "BOTH":
        mode_cards = f"""
        <section class="section">
          <h2>Mode Comparison</h2>
          <div class="mode-grid">
            {_mode_card("🔪 SCALPER", stats.scalper_stats)}
            {_mode_card("📈 SWING", stats.swing_stats)}
          </div>
        </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>PHANTOM Backtest — {stats.symbol}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:#0f172a;color:#e2e8f0;padding:24px}}
    h1{{font-size:1.6rem;font-weight:700;color:#f8fafc}}
    h2{{font-size:1.1rem;font-weight:600;color:#94a3b8;
        text-transform:uppercase;letter-spacing:.05em;margin-bottom:16px}}
    h4{{font-size:1rem;color:#f1f5f9;margin-bottom:12px}}
    .header{{display:flex;justify-content:space-between;align-items:flex-start;
             margin-bottom:32px;flex-wrap:wrap;gap:12px}}
    .header-sub{{color:#94a3b8;font-size:.875rem;margin-top:4px}}
    .section{{background:#1e293b;border-radius:12px;padding:24px;margin-bottom:24px}}
    .summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:16px}}
    .stat-card{{background:#0f172a;border-radius:8px;padding:16px;text-align:center}}
    .stat-card .val{{font-size:1.8rem;font-weight:700;color:#38bdf8}}
    .stat-card .lbl{{font-size:.75rem;color:#94a3b8;margin-top:4px;text-transform:uppercase}}
    .stat-row{{display:flex;justify-content:space-between;padding:6px 0;
               border-bottom:1px solid #1e293b;font-size:.875rem}}
    .chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
    .chart-wrap{{background:#0f172a;border-radius:8px;padding:16px}}
    .chart-wrap canvas{{max-height:260px}}
    table{{width:100%;border-collapse:collapse;font-size:.8rem}}
    th{{background:#0f172a;color:#64748b;text-align:left;padding:10px 8px;
        text-transform:uppercase;font-size:.7rem;letter-spacing:.05em;cursor:pointer}}
    th:hover{{color:#38bdf8}}
    tr:hover{{background:rgba(255,255,255,0.02)}}
    td{{padding:8px;border-bottom:1px solid #1e293b;color:#cbd5e1}}
    .badge{{padding:2px 8px;border-radius:9999px;font-size:.7rem;font-weight:600}}
    .badge-scalper{{background:#312e81;color:#a5b4fc}}
    .badge-swing{{background:#164e63;color:#67e8f9}}
    .badge-long{{background:#14532d;color:#86efac}}
    .badge-short{{background:#7f1d1d;color:#fca5a5}}
    .mode-grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
    .mode-card{{background:#0f172a;border-radius:8px;padding:20px}}
    .run-id{{font-size:.7rem;color:#334155;margin-top:8px}}
    @media(max-width:768px){{
      .chart-grid,.mode-grid{{grid-template-columns:1fr}}
    }}
  </style>
</head>
<body>

<div class="header">
  <div>
    <h1>🩸 PHANTOM Backtest Report</h1>
    <div class="header-sub">
      {stats.symbol} (ID: {stats.security_id}) &nbsp;·&nbsp;
      {stats.from_date} → {stats.to_date} &nbsp;·&nbsp;
      Mode: {stats.mode}
    </div>
    <div class="run-id">Run ID: {run_id}</div>
  </div>
</div>

<!-- Summary Cards -->
<section class="section">
  <h2>Summary</h2>
  <div class="summary-grid">
    <div class="stat-card"><div class="val">{stats.total_trades}</div><div class="lbl">Trades</div></div>
    <div class="stat-card"><div class="val">{stats.win_rate:.1f}%</div><div class="lbl">Win Rate</div></div>
    <div class="stat-card"><div class="val">{stats.avg_rr:.2f}</div><div class="lbl">Avg R:R</div></div>
    <div class="stat-card"><div class="val">{stats.profit_factor:.2f}</div><div class="lbl">Profit Factor</div></div>
    <div class="stat-card"><div class="val" style="color:{'#4ade80' if stats.total_pnl_points>=0 else '#f87171'}">{stats.total_pnl_points:+.1f}</div><div class="lbl">Total PnL (pts)</div></div>
    <div class="stat-card"><div class="val" style="color:#f87171">{stats.max_drawdown_points:.1f}</div><div class="lbl">Max Drawdown</div></div>
    <div class="stat-card"><div class="val">{stats.winners}</div><div class="lbl">Winners</div></div>
    <div class="stat-card"><div class="val">{stats.losers}</div><div class="lbl">Losers</div></div>
    <div class="stat-card"><div class="val">{stats.trades_per_day:.1f}</div><div class="lbl">Trades/Day</div></div>
  </div>
</section>

<!-- Equity Curve -->
<section class="section">
  <h2>Equity Curve</h2>
  <div class="chart-wrap" style="background:transparent;padding:0">
    <canvas id="equityChart"></canvas>
  </div>
</section>

<!-- Drawdown -->
<section class="section">
  <h2>Drawdown</h2>
  <div class="chart-wrap" style="background:transparent;padding:0">
    <canvas id="ddChart"></canvas>
  </div>
</section>

<!-- Distribution Charts -->
<section class="section">
  <h2>Distributions</h2>
  <div class="chart-grid">
    <div class="chart-wrap"><h4>Outcome Mix</h4><canvas id="pieChart"></canvas></div>
    <div class="chart-wrap"><h4>Trades by Hour</h4><canvas id="hourChart"></canvas></div>
    <div class="chart-wrap"><h4>Trades by Day of Week</h4><canvas id="dowChart"></canvas></div>
  </div>
</section>

{mode_cards}

<!-- Trade Table -->
<section class="section">
  <h2>All Trades ({len(trades)})</h2>
  <div style="overflow-x:auto">
    <table id="tradeTable">
      <thead>
        <tr>
          <th onclick="sortTable(0)">#</th>
          <th onclick="sortTable(1)">Date</th>
          <th onclick="sortTable(2)">Mode</th>
          <th onclick="sortTable(3)">Dir</th>
          <th onclick="sortTable(4)">Entry</th>
          <th onclick="sortTable(5)">SL</th>
          <th onclick="sortTable(6)">TP1</th>
          <th onclick="sortTable(7)">TP2</th>
          <th onclick="sortTable(8)">TP3</th>
          <th onclick="sortTable(9)">Exit Px</th>
          <th onclick="sortTable(10)">Exit Time</th>
          <th onclick="sortTable(11)">Outcome</th>
          <th onclick="sortTable(12)">R:R</th>
          <th onclick="sortTable(13)">PnL pts</th>
        </tr>
      </thead>
      <tbody>{trade_rows}</tbody>
    </table>
  </div>
</section>

<script>
const eqLabels   = {json.dumps(eq_labels)};
const allEq      = {json.dumps(all_eq)};
const scEq       = {json.dumps(sc_eq)};
const swEq       = {json.dumps(sw_eq)};
const ddLabels   = {json.dumps(dd_labels)};
const ddData     = {json.dumps(dd_data)};
const pieLabels  = {json.dumps(pie_labels)};
const pieData    = {json.dumps(pie_data)};
const hourLabels = {json.dumps(hour_labels)};
const hourData   = {json.dumps(hour_data)};
const dowLabels  = {json.dumps(dow_labels)};
const dowData    = {json.dumps(dow_data)};

const gridColor = 'rgba(255,255,255,0.05)';
const textColor = '#64748b';

// Equity curve
new Chart(document.getElementById('equityChart'), {{
  type: 'line',
  data: {{
    labels: eqLabels,
    datasets: [
      {{ label: 'Total', data: allEq, borderColor: '#38bdf8', borderWidth:2,
         pointRadius:0, tension:0.3, fill:false }},
      {{ label: 'SCALPER', data: scEq, borderColor: '#a78bfa', borderWidth:1.5,
         pointRadius:0, tension:0.3, fill:false, borderDash:[4,4] }},
      {{ label: 'SWING', data: swEq, borderColor: '#34d399', borderWidth:1.5,
         pointRadius:0, tension:0.3, fill:false, borderDash:[4,4] }},
    ]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ labels:{{ color:textColor }} }} }},
    scales:{{ x:{{ ticks:{{ color:textColor,maxTicksLimit:12 }}, grid:{{ color:gridColor }} }},
              y:{{ ticks:{{ color:textColor }}, grid:{{ color:gridColor }} }} }} }}
}});

// Drawdown
new Chart(document.getElementById('ddChart'), {{
  type: 'line',
  data: {{
    labels: ddLabels,
    datasets: [{{ label: 'Drawdown', data: ddData, borderColor:'#f87171',
      backgroundColor:'rgba(248,113,113,0.15)', borderWidth:1.5,
      pointRadius:0, tension:0.3, fill:true }}]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }},
    scales:{{ x:{{ ticks:{{ color:textColor,maxTicksLimit:12 }}, grid:{{ color:gridColor }} }},
              y:{{ ticks:{{ color:textColor }}, grid:{{ color:gridColor }} }} }} }}
}});

// Outcome pie
new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{
    labels: pieLabels,
    datasets: [{{ data: pieData,
      backgroundColor:['#22c55e','#4ade80','#86efac','#f87171','#9ca3af'] }}]
  }},
  options: {{ responsive:true,
    plugins:{{ legend:{{ labels:{{ color:textColor }} }} }} }}
}});

// By hour
new Chart(document.getElementById('hourChart'), {{
  type: 'bar',
  data: {{
    labels: hourLabels,
    datasets: [{{ label:'Trades', data:hourData,
      backgroundColor:'rgba(56,189,248,0.7)', borderRadius:4 }}]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }},
    scales:{{ x:{{ ticks:{{ color:textColor }}, grid:{{ color:gridColor }} }},
              y:{{ ticks:{{ color:textColor }}, grid:{{ color:gridColor }} }} }} }}
}});

// By DOW
new Chart(document.getElementById('dowChart'), {{
  type: 'bar',
  data: {{
    labels: dowLabels,
    datasets: [{{ label:'Trades', data:dowData,
      backgroundColor:'rgba(167,139,250,0.7)', borderRadius:4 }}]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }},
    scales:{{ x:{{ ticks:{{ color:textColor }}, grid:{{ color:gridColor }} }},
              y:{{ ticks:{{ color:textColor }}, grid:{{ color:gridColor }} }} }} }}
}});

// Sortable table
let sortDir = {{}};
function sortTable(col) {{
  const tbody = document.querySelector('#tradeTable tbody');
  const rows = Array.from(tbody.rows);
  sortDir[col] = !sortDir[col];
  rows.sort((a,b) => {{
    const av = a.cells[col].innerText.trim();
    const bv = b.cells[col].innerText.trim();
    const an = parseFloat(av), bn = parseFloat(bv);
    const cmp = isNaN(an)||isNaN(bn) ? av.localeCompare(bv) : an-bn;
    return sortDir[col] ? cmp : -cmp;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
</script>

</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"[BACKTEST] Report saved → {out_path}")
    return out_path
