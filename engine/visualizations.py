"""
Visualizations Module
=====================
Generates all 10 required plots for the backtest report.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
import os
from config import BASE_NAV, STARTING_CAPITAL, CAPITAL_PER_STRATEGY
from engine.metrics import compute_rolling_sharpe

# Professional styling
plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor': '#161b22',
    'axes.edgecolor': '#30363d',
    'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9',
    'xtick.color': '#8b949e',
    'ytick.color': '#8b949e',
    'grid.color': '#21262d',
    'grid.alpha': 0.6,
    'legend.facecolor': '#161b22',
    'legend.edgecolor': '#30363d',
    'font.family': 'sans-serif',
    'font.size': 11,
})

COLORS = ['#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff',
          '#79c0ff', '#7ee787', '#e3b341', '#ff7b72', '#d2a8ff']
COMBINED_COLOR = '#f0f6fc'


def save_plot(fig, filename, output_dir='output/plots'):
    """Save a figure to disk."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"  Saved: {filepath}")


def plot_individual_equity_curves(nav_series: dict, output_dir='output/plots'):
    """Plot 1: Individual equity curves in subplots."""
    strategy_names = [k for k in nav_series.keys() if k != 'Combined']
    n = len(strategy_names)
    fig, axes = plt.subplots(n, 1, figsize=(14, 3*n), sharex=True)
    if n == 1:
        axes = [axes]

    for i, name in enumerate(strategy_names):
        nav = nav_series[name]
        ax = axes[i]
        dates = pd.to_datetime(nav.index)
        ax.plot(dates, nav.values, color=COLORS[i], linewidth=1.5, label=name)
        ax.axhline(y=BASE_NAV, color='#8b949e', linestyle='--', alpha=0.5, linewidth=0.8)
        ax.fill_between(dates, BASE_NAV, nav.values,
                         where=nav.values >= BASE_NAV, alpha=0.15, color=COLORS[i])
        ax.fill_between(dates, BASE_NAV, nav.values,
                         where=nav.values < BASE_NAV, alpha=0.15, color='#f85149')
        ax.set_ylabel('NAV')
        ax.set_title(name, fontsize=12, fontweight='bold', color=COLORS[i])
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.suptitle('Individual Strategy Equity Curves (NAV Base 100)',
                 fontsize=14, fontweight='bold', y=1.01)
    fig.tight_layout()
    save_plot(fig, 'individual_equity_curves.png', output_dir)


def plot_combined_equity_curve(nav_series: dict, output_dir='output/plots'):
    """Plot 2: All strategies overlaid + combined portfolio (bold)."""
    fig, ax = plt.subplots(figsize=(14, 7))

    strategy_names = [k for k in nav_series.keys() if k != 'Combined']
    for i, name in enumerate(strategy_names):
        nav = nav_series[name]
        dates = pd.to_datetime(nav.index)
        ax.plot(dates, nav.values, color=COLORS[i], alpha=0.6, linewidth=1, label=name)

    if 'Combined' in nav_series:
        nav = nav_series['Combined']
        dates = pd.to_datetime(nav.index)
        ax.plot(dates, nav.values, color=COMBINED_COLOR, linewidth=2.5,
                label='Combined Portfolio', zorder=10)

    ax.axhline(y=BASE_NAV, color='#8b949e', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.set_xlabel('Date')
    ax.set_ylabel('NAV (Base 100)')
    ax.set_title('Combined Equity Curves — All Strategies + Portfolio',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.tight_layout()
    save_plot(fig, 'combined_equity_curve.png', output_dir)


def plot_combined_drawdown(drawdown: pd.Series, output_dir='output/plots'):
    """Plot 3: Drawdown % of combined portfolio."""
    fig, ax = plt.subplots(figsize=(14, 5))
    dates = pd.to_datetime(drawdown.index)
    ax.fill_between(dates, 0, drawdown.values * 100, color='#f85149', alpha=0.5)
    ax.plot(dates, drawdown.values * 100, color='#f85149', linewidth=1)
    ax.set_xlabel('Date')
    ax.set_ylabel('Drawdown (%)')
    ax.set_title('Combined Portfolio Drawdown', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.tight_layout()
    save_plot(fig, 'combined_drawdown.png', output_dir)


def plot_monthly_returns_heatmap(monthly_returns: dict, output_dir='output/plots'):
    """Plot 4: Monthly returns heatmap."""
    df = pd.DataFrame(monthly_returns)
    if df.empty:
        return
    df.index = pd.to_datetime(df.index)
    df['Year-Month'] = df.index.strftime('%Y-%m')
    df = df.set_index('Year-Month')

    fig, ax = plt.subplots(figsize=(14, max(6, len(df) * 0.4)))
    sns.heatmap(df, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                linewidths=0.5, linecolor='#30363d', ax=ax,
                cbar_kws={'label': 'Return (%)'})
    ax.set_title('Monthly Returns Heatmap (%)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Month')
    fig.tight_layout()
    save_plot(fig, 'monthly_returns_heatmap.png', output_dir)


def plot_daily_pnl_distribution(daily_pnl: pd.Series, output_dir='output/plots'):
    """Plot 5: Histogram of daily PnL for combined portfolio."""
    fig, ax = plt.subplots(figsize=(14, 6))
    pnl_vals = daily_pnl.values
    positive = pnl_vals[pnl_vals > 0]
    negative = pnl_vals[pnl_vals <= 0]

    bins = 50
    ax.hist(positive, bins=bins, color='#3fb950', alpha=0.7, label='Positive Days')
    ax.hist(negative, bins=bins, color='#f85149', alpha=0.7, label='Negative Days')
    ax.axvline(x=0, color='#8b949e', linestyle='--', linewidth=1)
    ax.axvline(x=pnl_vals.mean(), color='#58a6ff', linestyle='-', linewidth=1.5,
               label=f'Mean: ₹{pnl_vals.mean():,.0f}')
    ax.set_xlabel('Daily PnL (₹)')
    ax.set_ylabel('Frequency')
    ax.set_title('Combined Portfolio Daily PnL Distribution', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_plot(fig, 'daily_pnl_distribution.png', output_dir)


def plot_correlation_matrix(corr_matrix: pd.DataFrame, output_dir='output/plots'):
    """Plot 6: Correlation matrix heatmap."""
    fig, ax = plt.subplots(figsize=(8, 7))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdBu_r', center=0,
                vmin=-1, vmax=1, linewidths=1, linecolor='#30363d', ax=ax,
                square=True)
    ax.set_title('Strategy Return Correlation Matrix', fontsize=14, fontweight='bold')
    fig.tight_layout()
    save_plot(fig, 'correlation_matrix.png', output_dir)


def plot_strategy_comparison_bar(all_metrics: list, output_dir='output/plots'):
    """Plot 7: Grouped bar chart comparing key metrics across strategies."""
    df = pd.DataFrame(all_metrics)
    if 'Strategy' not in df.columns:
        return
    df = df.set_index('Strategy')

    metrics_to_plot = ['Sharpe_Ratio', 'Calmar_Ratio', 'Win_Rate']
    available = [m for m in metrics_to_plot if m in df.columns]

    fig, axes = plt.subplots(1, len(available), figsize=(5*len(available), 6))
    if len(available) == 1:
        axes = [axes]

    for i, metric in enumerate(available):
        ax = axes[i]
        values = df[metric].astype(float)
        bars = ax.bar(range(len(values)), values, color=COLORS[:len(values)], alpha=0.8)
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(values.index, rotation=45, ha='right', fontsize=9)
        ax.set_title(metric.replace('_', ' '), fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar, val in zip(bars, values):
            fmt = f'{val:.1%}' if metric == 'Win_Rate' else f'{val:.2f}'
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    fmt, ha='center', va='bottom', fontsize=9, color='#c9d1d9')

    fig.suptitle('Strategy Comparison', fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    save_plot(fig, 'strategy_comparison_bar.png', output_dir)


def plot_cumulative_pnl_rupees(strategy_daily_pnls: dict, combined_pnl: pd.Series,
                                output_dir='output/plots'):
    """Plot 8: Cumulative PnL in rupees for all strategies + combined."""
    fig, ax = plt.subplots(figsize=(14, 7))

    for i, (name, pnl) in enumerate(strategy_daily_pnls.items()):
        dates = pd.to_datetime(pnl.index)
        cum_pnl = pnl.cumsum()
        ax.plot(dates, cum_pnl.values / 100000, color=COLORS[i], alpha=0.6,
                linewidth=1, label=name)

    dates = pd.to_datetime(combined_pnl.index)
    cum_pnl = combined_pnl.cumsum()
    ax.plot(dates, cum_pnl.values / 100000, color=COMBINED_COLOR, linewidth=2.5,
            label='Combined', zorder=10)

    ax.axhline(y=0, color='#8b949e', linestyle='--', alpha=0.5)
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative PnL (₹ Lakhs)')
    ax.set_title('Cumulative PnL — All Strategies + Combined', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.tight_layout()
    save_plot(fig, 'cumulative_pnl_rupees.png', output_dir)


def plot_rolling_sharpe(combined_pnl: pd.Series, window=30, output_dir='output/plots'):
    """Plot 9: Rolling Sharpe for combined portfolio."""
    fig, ax = plt.subplots(figsize=(14, 5))
    rolling = compute_rolling_sharpe(combined_pnl, window, STARTING_CAPITAL)
    dates = pd.to_datetime(rolling.index)
    ax.plot(dates, rolling.values, color='#58a6ff', linewidth=1.2)
    ax.axhline(y=0, color='#8b949e', linestyle='--', alpha=0.5)
    ax.axhline(y=1, color='#3fb950', linestyle='--', alpha=0.4, label='Sharpe = 1')
    ax.axhline(y=2, color='#d29922', linestyle='--', alpha=0.4, label='Sharpe = 2')
    ax.fill_between(dates, 0, rolling.values,
                     where=rolling.values >= 0, alpha=0.1, color='#3fb950')
    ax.fill_between(dates, 0, rolling.values,
                     where=rolling.values < 0, alpha=0.1, color='#f85149')
    ax.set_xlabel('Date')
    ax.set_ylabel(f'{window}-Day Rolling Sharpe')
    ax.set_title(f'Combined Portfolio — {window}-Day Rolling Sharpe Ratio',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.tight_layout()
    save_plot(fig, 'rolling_sharpe.png', output_dir)


def plot_portfolio_weights_pie(weights: dict, output_dir='output/plots'):
    """Plot 10: Pie chart of final portfolio allocation."""
    fig, ax = plt.subplots(figsize=(8, 8))
    names = list(weights.keys())
    values = list(weights.values())
    colors = COLORS[:len(names)]

    wedges, texts, autotexts = ax.pie(
        values, labels=names, colors=colors, autopct='%1.1f%%',
        startangle=90, pctdistance=0.85, labeldistance=1.1,
        textprops={'color': '#c9d1d9', 'fontsize': 11}
    )
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')

    centre_circle = plt.Circle((0, 0), 0.65, fc='#161b22')
    ax.add_patch(centre_circle)
    ax.text(0, 0, 'Portfolio\nWeights', ha='center', va='center',
            fontsize=13, fontweight='bold', color='#c9d1d9')
    ax.set_title('Final Portfolio Allocation', fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    save_plot(fig, 'portfolio_weights_pie.png', output_dir)


def generate_all_plots(portfolio_results: dict, strategy_daily_pnls: dict,
                        all_metrics: list, output_dir='output/plots'):
    """Generate all 10 plots."""
    print("\nGenerating plots...")

    # 1. Individual equity curves
    plot_individual_equity_curves(portfolio_results['nav_series'], output_dir)

    # 2. Combined equity curve
    plot_combined_equity_curve(portfolio_results['nav_series'], output_dir)

    # 3. Combined drawdown
    plot_combined_drawdown(portfolio_results['combined_drawdown'], output_dir)

    # 4. Monthly returns heatmap
    plot_monthly_returns_heatmap(portfolio_results['monthly_returns'], output_dir)

    # 5. Daily PnL distribution
    plot_daily_pnl_distribution(portfolio_results['combined_daily_pnl'], output_dir)

    # 6. Correlation matrix
    plot_correlation_matrix(portfolio_results['correlation_matrix'], output_dir)

    # 7. Strategy comparison bar
    plot_strategy_comparison_bar(all_metrics, output_dir)

    # 8. Cumulative PnL
    plot_cumulative_pnl_rupees(strategy_daily_pnls,
                                portfolio_results['combined_daily_pnl'], output_dir)

    # 9. Rolling Sharpe
    plot_rolling_sharpe(portfolio_results['combined_daily_pnl'], 30, output_dir)

    # 10. Portfolio weights pie
    plot_portfolio_weights_pie(portfolio_results['weights'], output_dir)

    print(f"All 10 plots saved to {output_dir}/")
