"""
Portfolio Module
================
Combines multiple strategy results, performs weight optimization,
and computes combined portfolio metrics.
"""

import numpy as np
import pandas as pd
from itertools import product
from config import STARTING_CAPITAL, CAPITAL_PER_STRATEGY, BASE_NAV
from engine.metrics import compute_all_metrics, compute_nav_series, compute_drawdown_series


def combine_strategies_equal_weight(strategy_daily_pnls: dict) -> pd.Series:
    """
    Combine daily PnL from multiple strategies with equal weights.
    Each strategy gets 1/N of total capital.
    """
    pnl_df = pd.DataFrame(strategy_daily_pnls).fillna(0)
    combined = pnl_df.sum(axis=1)
    return combined


def combine_strategies_weighted(strategy_daily_pnls: dict, weights: dict) -> pd.Series:
    """
    Combine daily PnL with specified weights.
    Weights should sum to 1.0.
    """
    pnl_df = pd.DataFrame(strategy_daily_pnls).fillna(0)
    combined = pd.Series(0.0, index=pnl_df.index)
    for name, weight in weights.items():
        if name in pnl_df.columns:
            # Scale PnL by weight factor (relative to equal weight)
            scale = weight * len(weights)  # If 5 strategies, equal weight = 0.2
            combined += pnl_df[name] * scale
    return combined


def compute_correlation_matrix(strategy_daily_pnls: dict) -> pd.DataFrame:
    """Compute correlation matrix of daily returns across strategies."""
    pnl_df = pd.DataFrame(strategy_daily_pnls).fillna(0)
    returns_df = pnl_df / CAPITAL_PER_STRATEGY
    corr = returns_df.corr()
    return corr


def optimize_weights_for_calmar(strategy_daily_pnls: dict, target_calmar=5.0,
                                  min_weight=0.05, max_weight=0.50,
                                  step=0.05, verbose=True) -> dict:
    """
    Grid search over portfolio weights to maximize Calmar ratio.

    Args:
        strategy_daily_pnls: Dict of strategy_name -> daily PnL Series
        target_calmar: Target Calmar ratio
        min_weight: Minimum weight per strategy
        max_weight: Maximum weight per strategy
        step: Grid search step size

    Returns:
        Dict with 'weights', 'calmar', 'metrics'
    """
    strategy_names = list(strategy_daily_pnls.keys())
    n = len(strategy_names)

    if verbose:
        print(f"\nOptimizing weights for {n} strategies...")
        print(f"Weight range: {min_weight:.0%} to {max_weight:.0%}, step: {step:.0%}")

    # Generate weight combinations that sum to 1.0
    weight_values = np.arange(min_weight, max_weight + step/2, step)
    weight_values = np.round(weight_values, 2)

    best_calmar = -float('inf')
    best_weights = {name: 1.0/n for name in strategy_names}  # Start with equal
    best_metrics = None

    # For efficiency, use a smarter search for n=5
    # Try random sampling if grid is too large
    count = 0
    tested = 0

    if n <= 3:
        # Full grid search for small n
        for combo in product(weight_values, repeat=n):
            if abs(sum(combo) - 1.0) > 0.01:
                continue
            tested += 1
            weights = dict(zip(strategy_names, combo))
            combined = combine_strategies_weighted(strategy_daily_pnls, weights)
            metrics = compute_all_metrics(combined, STARTING_CAPITAL, 'Combined')
            if metrics['Calmar_Ratio'] > best_calmar:
                best_calmar = metrics['Calmar_Ratio']
                best_weights = weights.copy()
                best_metrics = metrics
    else:
        # For 5 strategies, systematic but filtered search
        # Try variations around equal weight first
        equal_w = 1.0 / n
        search_offsets = np.arange(-0.15, 0.20, step)

        for i_off in search_offsets:
            for j_off in search_offsets:
                for k_off in search_offsets:
                    w0 = equal_w + i_off
                    w1 = equal_w + j_off
                    w2 = equal_w + k_off

                    if w0 < min_weight or w1 < min_weight or w2 < min_weight:
                        continue
                    if w0 > max_weight or w1 > max_weight or w2 > max_weight:
                        continue

                    remaining = 1.0 - w0 - w1 - w2

                    # Split remaining between last 2 strategies
                    for w3_ratio in np.arange(0.3, 0.8, 0.1):
                        w3 = remaining * w3_ratio
                        w4 = remaining - w3

                        if w3 < min_weight or w4 < min_weight:
                            continue
                        if w3 > max_weight or w4 > max_weight:
                            continue

                        tested += 1
                        weights = dict(zip(strategy_names, [w0, w1, w2, w3, w4]))
                        combined = combine_strategies_weighted(strategy_daily_pnls, weights)
                        metrics = compute_all_metrics(combined, STARTING_CAPITAL, 'Combined')

                        if metrics['Calmar_Ratio'] > best_calmar:
                            best_calmar = metrics['Calmar_Ratio']
                            best_weights = weights.copy()
                            best_metrics = metrics

    # Also try equal weight
    combined_eq = combine_strategies_equal_weight(strategy_daily_pnls)
    eq_metrics = compute_all_metrics(combined_eq, STARTING_CAPITAL, 'EqualWeight')

    if verbose:
        print(f"Tested {tested} weight combinations")
        print(f"Equal weight Calmar: {eq_metrics['Calmar_Ratio']:.4f}")
        print(f"Best optimized Calmar: {best_calmar:.4f}")
        print(f"Best weights: {', '.join(f'{k}: {v:.1%}' for k, v in best_weights.items())}")
        if best_calmar >= target_calmar:
            print(f"✓ Target Calmar {target_calmar} ACHIEVED!")
        else:
            print(f"✗ Target Calmar {target_calmar} not achieved. Best: {best_calmar:.4f}")

    # Use the better of equal weight vs optimized
    if eq_metrics['Calmar_Ratio'] >= best_calmar:
        final_weights = {name: 1.0/n for name in strategy_names}
        final_metrics = eq_metrics
        final_calmar = eq_metrics['Calmar_Ratio']
        if verbose:
            print("Using equal weights (better than optimized)")
    else:
        final_weights = best_weights
        final_metrics = best_metrics
        final_calmar = best_calmar

    return {
        'weights': final_weights,
        'calmar': final_calmar,
        'metrics': final_metrics,
        'equal_weight_calmar': eq_metrics['Calmar_Ratio'],
        'combinations_tested': tested
    }


def build_portfolio_results(strategy_results: dict, strategy_daily_pnls: dict,
                             weights: dict = None) -> dict:
    """
    Build comprehensive portfolio results.

    Args:
        strategy_results: Dict of strategy_name -> {'tradesheet', 'daily_pnl', 'metrics'}
        strategy_daily_pnls: Dict of strategy_name -> daily PnL Series
        weights: Portfolio weights (None for equal weight)

    Returns:
        Dict with combined results
    """
    if weights is None:
        weights = {name: 1.0/len(strategy_daily_pnls) for name in strategy_daily_pnls}

    # Combined daily PnL
    combined_pnl = combine_strategies_weighted(strategy_daily_pnls, weights)

    # Combined metrics
    combined_metrics = compute_all_metrics(combined_pnl, STARTING_CAPITAL, 'Combined')

    # NAV series for each strategy and combined
    nav_series = {}
    for name, pnl in strategy_daily_pnls.items():
        nav_series[name] = compute_nav_series(pnl, CAPITAL_PER_STRATEGY)
    nav_series['Combined'] = compute_nav_series(combined_pnl, STARTING_CAPITAL)

    # Drawdown
    combined_dd = compute_drawdown_series(nav_series['Combined'])

    # Correlation matrix
    corr_matrix = compute_correlation_matrix(strategy_daily_pnls)

    # Monthly returns
    monthly_returns = {}
    for name, pnl in strategy_daily_pnls.items():
        pnl.index = pd.to_datetime(pnl.index)
        monthly = pnl.resample('ME').sum()
        monthly_returns[name] = monthly / CAPITAL_PER_STRATEGY * 100  # As percentage
    combined_pnl_dt = combined_pnl.copy()
    combined_pnl_dt.index = pd.to_datetime(combined_pnl_dt.index)
    monthly_returns['Combined'] = combined_pnl_dt.resample('ME').sum() / STARTING_CAPITAL * 100

    return {
        'weights': weights,
        'combined_daily_pnl': combined_pnl,
        'combined_metrics': combined_metrics,
        'nav_series': nav_series,
        'combined_drawdown': combined_dd,
        'correlation_matrix': corr_matrix,
        'monthly_returns': monthly_returns
    }
