# PHANTOM
**Price Hunt And Market Trap Observation Node**

PHANTOM is a high-performance market observation node designed for Smart Money Concept (SMC) trading. It specializes in detecting liquidity sweeps, market structure breaks (BOS), and Fair Value Gaps (FVG) for intraday trading on Indian markets (NSE + MCX).

---

## 🏗️ Architecture Overview

PHANTOM operates as a state-machine based observation node, synchronizing multiple timeframes to identify high-probability setups.

```mermaid
graph TD
    A[Main Loop] --> B{Feed Manager}
    B -->|Live OHLCV| C[Mode Controller]
    B -->|Historical Feed| BT[Backtest Engine]
    
    C --> D[Mode Pipeline: Scalper]
    C --> E[Mode Pipeline: Swing]
    
    BT --> S[Backtest Simulator]
    S --> D
    S --> E
    
    subgraph "Core Engines"
        D --> F[Bias Engine]
        F --> G[Liquidity Map]
        G --> H[Sweep Detector]
        H --> I[FVG Engine]
        I --> J[Entry Engine]
        J --> K[Target Resolver]
    end
    
    K --> L[Setup Validator]
    L -->|Valid Setup| M[Supabase Store]
    L -->|Valid Setup| N[Discord Webhook]
    S -->|Stats & Trades| M
    S -->|HTML Report| R[Report Generator]
```

---

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.9+
- Dhan Account (with API access)
- Supabase Project (for data persistence)
- Discord (Optional, for alerts)

### 2. Installation
```bash
# Clone the repository
git clone <repo-url> phantom
cd phantom

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Initialization
Execute the `schema.sql` file in your Supabase SQL Editor to create the necessary `candles` and `phantom_setups` tables.

---

## ⚙️ Configuration (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `DHAN_CLIENT_ID` | Your Dhan client ID | `1100123456` |
| `DHAN_TOTP_SECRET` | TOTP secret (32-char base32 key) | `JBSWY3DPEHPK3PXP` |
| `SUPABASE_URL` | Your Supabase Project URL | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | Your Supabase API Key | `eyJhbGciOiJIUzI1...` |
| `DISCORD_WEBHOOK_URL` | Discord webhook for alerts | `https://discord.com/api/webhooks/...` |
| `ACTIVE_MODE` | Trading mode: `SCALPER`, `SWING`, or `BOTH` | `BOTH` |
| `ENTRY_TYPE` | Primary entry trigger | `MITIGATION` |

---

## 🛠️ System Components

### 🧠 Core Engines
- **Bias Engine**: Analyzes higher timeframe structure to determine long/short bias.
- **Liquidity Map**: Tracks swing highs/lows and identifies equal highs/lows (BSL/SSL).
- **Sweep Detector**: Monitors for wick violations of liquidity levels followed by a close back inside.
- **FVG Engine**: Detects displacement-grade Fair Value Gaps following a sweep.
- **Entry Engine**: Validates entry triggers (Mitigation, Rejection, or candle-body BOS).
- **Target Resolver**: Calculates TP levels based on risk multiples and opposing liquidity.

### 📊 Data Layer
- **Feed Manager**: Handles real-time polling and historical data fetching via Dhan HQ.
- **Store Manager**: Manages asynchronous persistence to Supabase.

### 🧪 Backtest System
- **Backtest Simulator**: Replays historical candles tick-by-tick through core modules.
- **Report Generator**: Produces premium HTML dashboards with Chart.js visualization.
- **Backtest Feed**: Specialized provider for historical OHLCV data.

---

## ⌨️ CLI Usage

Standard execution (Default: NIFTY):
```bash
python main.py
```

Run for a specific security (e.g., BANKNIFTY ID: 15):
```bash
python main.py --id 15
```

Override active mode to Swing only:
```bash
python main.py --id 15 --mode SWING
```

### 📊 Backtesting

Run a 30-day backtest for NIFTY and open the report:
```bash
python main.py --backtest --report
```

Run backtest for a specific range and instrument:
```bash
python main.py --backtest --id 15 --from 2024-01-01 --to 2024-03-31 --report
```

Run backtest for the last 90 days in Scalper mode:
```bash
python main.py --backtest --mode SCALPER --days 90 --report
```

---

## 📄 Automated Documentation
API documentation is generated from Google-style docstrings.

```bash
python execution/generate_docs.py
```
Outputs are saved in `directives/api-docs/`.

---

## 📚 API Documentation

Technical documentation for all system modules is available in the [directives/api-docs/](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs) directory.

### Key Modules:
- **Core Engines**: [Bias Engine](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/core_bias_engine.md), [Sweep Detector](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/core_sweep_detector.md), [FVG Engine](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/core_fvg_engine.md)
- **Backtest**: [Simulator](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/backtest_simulator.md), [Report Generator](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/backtest_report.md)
- **Data Layer**: [Feed Manager](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/data_feed.md), [Store Manager](file:///home/atompopeye/Documents/PHANTOM/directives/api-docs/data_store.md)

To refresh the documentation:
```bash
python execution/generate_docs.py
```

---

## 📜 License
PHANTOM is proprietary software. All rights reserved.
