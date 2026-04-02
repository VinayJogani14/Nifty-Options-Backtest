# Nifty Intraday Options Strategies — Backtest System

## Qode Advisors LLP — Quant Research Analyst Assessment 2
**Author:** Vinay Jogani  
**Date:** April 2026

---

## Overview

Complete backtest system for 5 intraday Nifty options trading strategies using 1-minute OHLCV data from October 2024 to March 2026.

### Strategies:
1. **Mean Reversion** — Short ATM straddle with combined premium SL
2. **Directional** — Momentum breakout buying OTM options
3. **Semi-Directional** — Ratio credit spread based on gap + momentum bias
4. **Volatility Breakout** — Long straddle on opening range breakout
5. **Iron Fly** — Defined-risk mean reversion with OTM wings

---

## Setup

### 1. Create Virtual Environment
```bash
cd ~/Desktop/Qode_Assessment2
python3 -m venv qode2
source qode2/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Data Setup
Place the NIFTY options data from Google Drive into `data/raw/`. The data should be organized in weekly expiry date folders:
```
data/raw/
├── 2024-10-03/
│   ├── NIFTY_23550_CE_03_OCT_24.csv
│   └── ...
├── 2024-10-10/
└── ...
```

### 4. Run
```bash
PYTHONPATH=. python main.py
```

---

## Output

| Output | Location |
|--------|----------|
| Excel Workbook | `output/Qode_Assignment2_Results.xlsx` |
| PDF Report | `output/Qode_Assignment2_Report.pdf` |
| Plots (10) | `output/plots/` |
| Individual Results | `output/individual_results/` |

---

## Project Structure

```
├── config.py                  # Central configuration
├── main.py                    # Pipeline orchestrator
├── data/
│   ├── data_loader.py         # Data loading & preprocessing
│   └── processed/             # Parquet caches
├── strategies/
│   ├── base_strategy.py       # Abstract base class
│   ├── mean_reversion.py      # Strategy 1
│   ├── directional.py         # Strategy 2
│   ├── semi_directional.py    # Strategy 3
│   ├── volatility_breakout.py # Strategy 4
│   └── iron_fly.py            # Strategy 5
├── engine/
│   ├── backtester.py          # Backtest execution engine
│   ├── metrics.py             # 16+ performance metrics
│   ├── portfolio.py           # Portfolio combination & optimization
│   └── visualizations.py      # 10 visualization plots
├── reports/
│   ├── generate_excel.py      # Excel workbook generator
│   └── generate_report.py     # PDF report generator
└── output/                    # Generated results
```

---

## Key Parameters

- **Capital:** Rs. 1 Crore (Rs. 20 Lakhs per strategy)
- **Lot Size:** 25
- **In-Sample:** Oct 2024 — Oct 2025
- **Out-of-Sample:** Nov 2025 — Mar 2026
- **Metrics:** CAGR, MDD, Sharpe, Calmar, Win Rate, Sortino, Profit Factor, + 10 more
- **Target:** Combined Calmar ≥ 5
