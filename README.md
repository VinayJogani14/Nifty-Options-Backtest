# Nifty Intraday Options Strategies — Backtest System

## Qode Advisors LLP — Quant Research Analyst Assessment 2
**Author:** Vinay Jogani  
**Date:** April 2026

---

## Overview

Complete backtest system for 3 intraday Nifty options trading strategies using 1-minute OHLCV data from October 2024 to March 2026.

### Strategies:
1. **Mean Reversion** — Short ATM straddle with combined premium SL
2. **Directional** — Momentum breakout buying OTM options
3. **Semi-Directional** — Ratio credit spread based on gap + momentum bias

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
Download the required NIFTY options data (~740 MB zip) from the [Google Drive Link](https://drive.google.com/drive/u/0/folders/1mBWKNuQCQM3EwbncAJ6lTwQFf95Yfauw) and extract it into `data/raw/`. The data should be organized in weekly expiry date folders:
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
│   └── semi_directional.py    # Strategy 3
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

- **Capital:** Rs. 1 Crore (Rs. 33.3 Lakhs per strategy)
- **Lot Size:** 25
- **In-Sample:** Oct 2024 — Oct 2025
- **Out-of-Sample:** Nov 2025 — Mar 2026
- **Metrics:** CAGR, MDD, Sharpe, Calmar, Win Rate, Sortino, Profit Factor, + 10 more
- **Target:** Combined Calmar ≥ 5
