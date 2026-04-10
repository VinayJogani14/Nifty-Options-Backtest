"""
Configuration constants for the Nifty Intraday Options Backtest System.
"""

# === DATE RANGES ===
INSAMPLE_START = "2024-10-03"   # First date in dataset
INSAMPLE_END = "2025-10-31"     # ~12 months for primary backtest
OOS_START = "2025-11-01"        # Out-of-sample validation start
OOS_END = "2026-02-10"          # Last date in dataset

# === CAPITAL & POSITION SIZING ===
STARTING_CAPITAL = 10_000_000   # Rs. 1 Crore
NIFTY_LOT_SIZE = 25             # Nifty lot size (25 from April 2024 onwards)
BASE_NAV = 100
NUM_STRATEGIES = 3
CAPITAL_PER_STRATEGY = STARTING_CAPITAL / NUM_STRATEGIES  # Rs. 33.3 Lakhs each

# === TRADING HOURS ===
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"

# === TRANSACTION COSTS (per lot, per side) ===
BROKERAGE_PER_ORDER = 20        # Rs. 20 flat per order (discount broker)
STT_SELL_RATE = 0.000625        # 0.0625% on sell-side premium
EXCHANGE_TXN_RATE = 0.00053     # NSE transaction charges
GST_RATE = 0.18                 # 18% GST on brokerage + exchange charges
SEBI_RATE = 0.000001            # Rs. 10 per crore
STAMP_DUTY_BUY = 0.00003        # 0.003% on buy side
SLIPPAGE_PER_UNIT = 0.10        # Rs. 0.10 estimated slippage (institutional limit execution)

# === RISK-FREE RATE ===
RISK_FREE_RATE = 0.07           # 7% annualized (Indian 10Y govt bond approx)

# === EXPIRY ===
EXPIRY_DAY = 3                  # Thursday = weekday 3 in Python (Monday=0)

# === NIFTY STRIKE INTERVAL ===
STRIKE_INTERVAL = 50            # Nifty options have 50-point strike intervals
