"""
Metrics Module
==============
Computes all 16+ performance metrics from trade data.
"""

import numpy as np
import pandas as pd
from config import RISK_FREE_RATE, STARTING_CAPITAL, BASE_NAV, CAPITAL_PER_STRATEGY


def compute_all_metrics(daily_pnl_series: pd.Series, capital: float = None,
                        strategy_name: str = '', tradesheet: pd.DataFrame = None) -> dict:
    """
    Compute all 16+ performance metrics.

    Args:
        daily_pnl_series: Series indexed by date with daily net PnL values
        capital: Starting capital (defaults to CAPITAL_PER_STRATEGY)
        strategy_name: Name for labeling
        tradesheet: Optional full tradesheet for trade-level metrics

    Returns:
        Dictionary of all metrics
    """
    if capital is None:
        capital = CAPITAL_PER_STRATEGY

    metrics = {'Strategy': strategy_name}

    daily_pnl = daily_pnl_series.copy()
    daily_returns = daily_pnl / capital

    # Cumulative values
    cum_pnl = daily_pnl.cumsum()
    nav_series = BASE_NAV * (1 + cum_pnl / capital)

    # 1. CAGR
    total_pnl = daily_pnl.sum()
    end_val = capital + total_pnl
    total_days = (pd.to_datetime(daily_pnl.index.max()) -
                  pd.to_datetime(daily_pnl.index.min())).days
    total_years = max(total_days / 365.25, 1/365.25)
    cagr = (end_val / capital) ** (1 / total_years) - 1 if end_val > 0 else -1
    metrics['CAGR'] = cagr

    # 2. Max Drawdown (MDD)
    nav_running_max = nav_series.cummax()
    dd_pct = (nav_series - nav_running_max) / nav_running_max
    max_dd = dd_pct.min()
    metrics['Max_Drawdown'] = max_dd

    # Drawdown in rupees
    running_max_pnl = cum_pnl.cummax()
    dd_rupees = cum_pnl - running_max_pnl

    # 3. Sharpe Ratio
    rf_daily = RISK_FREE_RATE / 252
    excess_returns = daily_returns - rf_daily
    sharpe = (np.sqrt(252) * excess_returns.mean() / excess_returns.std()
              if excess_returns.std() > 0 else 0)
    metrics['Sharpe_Ratio'] = round(sharpe, 4)

    # 4. Win Rate (daily)
    winning_days = (daily_pnl > 0).sum()
    total_days_traded = len(daily_pnl)
    metrics['Win_Rate'] = round(winning_days / total_days_traded, 4) if total_days_traded > 0 else 0

    # 5. Avg Profit per winning day
    win_pnl = daily_pnl[daily_pnl > 0]
    metrics['Avg_Profit'] = round(win_pnl.mean(), 2) if len(win_pnl) > 0 else 0

    # 6. Avg Loss per losing day
    loss_pnl = daily_pnl[daily_pnl <= 0]
    metrics['Avg_Loss'] = round(loss_pnl.mean(), 2) if len(loss_pnl) > 0 else 0

    # 7. Sortino Ratio
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = downside_returns.std()
    sortino = (np.sqrt(252) * excess_returns.mean() / downside_std
               if downside_std > 0 else 0)
    metrics['Sortino_Ratio'] = round(sortino, 4)

    # 8. Calmar Ratio
    calmar = abs(cagr / max_dd) if max_dd != 0 else 0
    metrics['Calmar_Ratio'] = round(calmar, 4)

    # 9. Profit Factor
    total_profit = daily_pnl[daily_pnl > 0].sum()
    total_loss = abs(daily_pnl[daily_pnl <= 0].sum())
    metrics['Profit_Factor'] = round(total_profit / total_loss, 4) if total_loss > 0 else float('inf')

    # 10. Max Consecutive Wins
    is_win = (daily_pnl > 0).astype(int)
    if len(is_win) > 0:
        win_groups = is_win.diff().ne(0).cumsum()
        consec_wins = is_win.groupby(win_groups).sum()
        metrics['Max_Consecutive_Wins'] = int(consec_wins.max()) if len(consec_wins) > 0 else 0
    else:
        metrics['Max_Consecutive_Wins'] = 0

    # 11. Max Consecutive Losses
    is_loss = (daily_pnl <= 0).astype(int)
    if len(is_loss) > 0:
        loss_groups = is_loss.diff().ne(0).cumsum()
        consec_losses = is_loss.groupby(loss_groups).sum()
        metrics['Max_Consecutive_Losses'] = int(consec_losses.max()) if len(consec_losses) > 0 else 0
    else:
        metrics['Max_Consecutive_Losses'] = 0

    # 12. Expectancy
    win_rate = metrics['Win_Rate']
    loss_rate = 1 - win_rate
    expectancy = (win_rate * metrics['Avg_Profit']) + (loss_rate * metrics['Avg_Loss'])
    metrics['Expectancy'] = round(expectancy, 2)

    # 13. Recovery Factor
    max_dd_rupees = dd_rupees.min()
    metrics['Recovery_Factor'] = round(abs(total_pnl / max_dd_rupees), 4) if max_dd_rupees != 0 else 0

    # 14. Payoff Ratio
    metrics['Payoff_Ratio'] = (round(abs(metrics['Avg_Profit'] / metrics['Avg_Loss']), 4)
                                if metrics['Avg_Loss'] != 0 else float('inf'))

    # 15. Annualized Volatility
    metrics['Annual_Volatility'] = round(daily_returns.std() * np.sqrt(252), 4)

    # 16. Skewness and Kurtosis
    metrics['Return_Skewness'] = round(float(daily_returns.skew()), 4)
    metrics['Return_Kurtosis'] = round(float(daily_returns.kurtosis()), 4)

    # Bonus metrics
    metrics['Total_Trading_Days'] = total_days_traded
    metrics['Total_Net_PnL'] = round(total_pnl, 2)
    metrics['Total_Return_Pct'] = round((end_val / capital - 1) * 100, 2)
    metrics['Final_NAV'] = round(float(nav_series.iloc[-1]), 2) if len(nav_series) > 0 else BASE_NAV

    # Trade-level metrics if tradesheet provided
    if tradesheet is not None and len(tradesheet) > 0:
        metrics['Total_Trades'] = len(tradesheet)
        winners = tradesheet[tradesheet['net_pnl'] > 0]
        losers = tradesheet[tradesheet['net_pnl'] <= 0]
        trade_winners_count = len(winners)
        
        metrics['Trade_Win_Rate'] = round(trade_winners_count / len(tradesheet), 4) if len(tradesheet) > 0 else 0
        metrics['Avg_Trade_Profit'] = round(winners['net_pnl'].mean(), 2) if trade_winners_count > 0 else 0
        metrics['Avg_Trade_Loss'] = round(losers['net_pnl'].mean(), 2) if len(losers) > 0 else 0
        metrics['Avg_PnL_Per_Trade'] = round(tradesheet['net_pnl'].mean(), 2)

    return metrics


def compute_nav_series(daily_pnl_series: pd.Series, capital: float = None) -> pd.Series:
    """Compute NAV series from daily PnL."""
    if capital is None:
        capital = CAPITAL_PER_STRATEGY
    cum_pnl = daily_pnl_series.cumsum()
    nav = BASE_NAV * (1 + cum_pnl / capital)
    return nav


def compute_drawdown_series(nav_series: pd.Series) -> pd.Series:
    """Compute drawdown percentage series from NAV."""
    running_max = nav_series.cummax()
    drawdown = (nav_series - running_max) / running_max
    return drawdown


def compute_rolling_sharpe(daily_pnl_series: pd.Series, window: int = 30,
                            capital: float = None) -> pd.Series:
    """Compute rolling Sharpe ratio."""
    if capital is None:
        capital = CAPITAL_PER_STRATEGY
    daily_returns = daily_pnl_series / capital
    rf_daily = RISK_FREE_RATE / 252
    excess = daily_returns - rf_daily
    rolling_mean = excess.rolling(window).mean()
    rolling_std = excess.rolling(window).std()
    rolling_sharpe = np.sqrt(252) * rolling_mean / rolling_std
    return rolling_sharpe


def format_metrics_table(metrics_list: list) -> pd.DataFrame:
    """Format a list of metrics dicts into a presentable DataFrame."""
    df = pd.DataFrame(metrics_list)
    if 'Strategy' in df.columns:
        df = df.set_index('Strategy')

    # Format percentages
    pct_cols = ['CAGR', 'Max_Drawdown', 'Win_Rate', 'Annual_Volatility',
                'Total_Return_Pct', 'Trade_Win_Rate']
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2%}" if col != 'Total_Return_Pct' else f"{x:.2f}%")

    return df
