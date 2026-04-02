"""
Main Pipeline
=============
Runs the ENTIRE backtest pipeline end-to-end:
1. Load processed data
2. Run all 5 strategies on in-sample data
3. Run all 5 strategies on out-of-sample data
4. Compute all individual metrics
5. Build combined portfolio with weight optimization
6. Compute combined metrics
7. Generate all 10 plots
8. Generate Excel workbook
9. Generate PDF report
10. Print execution timing summary
"""

import sys
import os
import time
import warnings
warnings.filterwarnings('ignore')

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from config import (STARTING_CAPITAL, CAPITAL_PER_STRATEGY, NIFTY_LOT_SIZE,
                    INSAMPLE_START, INSAMPLE_END, OOS_START, OOS_END)

from data.data_loader import load_and_process_data, load_processed_data
from strategies.mean_reversion import MeanReversionStrategy
from strategies.directional import DirectionalStrategy
from strategies.semi_directional import SemiDirectionalStrategy
from strategies.volatility_breakout import VolatilityBreakoutStrategy
from strategies.iron_fly import IronFlyStrategy
from engine.backtester import run_backtest
from engine.metrics import compute_all_metrics
from engine.portfolio import (optimize_weights_for_calmar, build_portfolio_results,
                                compute_correlation_matrix)
from engine.visualizations import generate_all_plots
from reports.generate_excel import generate_excel_report
from reports.generate_report import generate_pdf_report


def run_data_processing():
    """Phase 1: Load and process data."""
    # Check for cached processed data
    data = load_processed_data()
    if data is not None:
        print("Using cached processed data.")
        return data

    print("Processing raw data (first run — this may take 10-15 minutes)...")
    data = load_and_process_data()
    return data


def create_strategies():
    """Create all 3 strategy instances."""
    return {
        'MeanReversion': MeanReversionStrategy(CAPITAL_PER_STRATEGY, NIFTY_LOT_SIZE),
        'Directional': DirectionalStrategy(CAPITAL_PER_STRATEGY, NIFTY_LOT_SIZE),
        'SemiDirectional': SemiDirectionalStrategy(CAPITAL_PER_STRATEGY, NIFTY_LOT_SIZE)
    }


def run_all_strategies(strategies, options_data, spot_data, expiry_map=None, label=''):
    """Run all strategies and collect results."""
    results = {}
    daily_pnls = {}

    # Build expiry map dict if DataFrame provided
    exp_map = None
    if expiry_map is not None:
        if isinstance(expiry_map, pd.DataFrame):
            exp_map = dict(zip(expiry_map['date'], expiry_map['nearest_expiry']))
        else:
            exp_map = expiry_map

    for name, strategy in strategies.items():
        print(f"\n{'='*60}")
        print(f"  Running {name} ({label})")
        print(f"{'='*60}")

        tradesheet, daily_pnl = run_backtest(
            strategy, options_data, spot_data,
            expiry_map=exp_map,
            strategy_capital=CAPITAL_PER_STRATEGY,
            verbose=True
        )

        if len(tradesheet) > 0:
            metrics = compute_all_metrics(
                daily_pnl, CAPITAL_PER_STRATEGY, name, tradesheet
            )
        else:
            metrics = {'Strategy': name, 'Total_Trades': 0}

        results[name] = {
            'tradesheet': tradesheet,
            'daily_pnl': daily_pnl,
            'metrics': metrics
        }
        daily_pnls[name] = daily_pnl

    return results, daily_pnls


def main():
    total_start = time.perf_counter()
    timings = {}

    print("="*70)
    print("  NIFTY INTRADAY OPTIONS STRATEGIES — BACKTEST PIPELINE")
    print("  Qode Advisors LLP — Assessment 2")
    print("="*70)

    # ============ Phase 1: Data ============
    t = time.perf_counter()
    data = run_data_processing()
    timings['Data Loading'] = time.perf_counter() - t

    insample_opts = data['insample_opts']
    oos_opts = data['oos_opts']
    insample_spot = data['insample_spot']
    oos_spot = data['oos_spot']
    expiry_map = data['expiry_map']

    print(f"\nIn-sample: {len(insample_opts):,} rows, {insample_opts['date'].nunique()} days")
    print(f"OOS: {len(oos_opts):,} rows, {oos_opts['date'].nunique()} days")

    # ============ Phase 2: In-Sample Strategies ============
    t = time.perf_counter()
    strategies = create_strategies()
    is_results, is_daily_pnls = run_all_strategies(
        strategies, insample_opts, insample_spot, expiry_map, 'In-Sample'
    )
    timings['In-Sample Strategies'] = time.perf_counter() - t

    # Collect metrics
    all_metrics_is = [r['metrics'] for r in is_results.values()]

    # Print summary
    print("\n" + "="*70)
    print("  IN-SAMPLE RESULTS SUMMARY")
    print("="*70)
    for name, res in is_results.items():
        m = res['metrics']
        print(f"  {name:<20} | Trades: {m.get('Total_Trades', 0):>5} | "
              f"Win: {m.get('Win_Rate', 0):>5.1%} | "
              f"Sharpe: {m.get('Sharpe_Ratio', 0):>6.2f} | "
              f"Calmar: {m.get('Calmar_Ratio', 0):>6.2f} | "
              f"PnL: Rs.{m.get('Total_Net_PnL', 0):>12,.0f}")

    # ============ Phase 3: Portfolio Construction ============
    t = time.perf_counter()

    # Optimize weights
    opt_result = optimize_weights_for_calmar(is_daily_pnls, target_calmar=5.0)
    optimal_weights = opt_result['weights']

    # Build portfolio results
    portfolio_results = build_portfolio_results(is_results, is_daily_pnls, optimal_weights)
    combined_metrics = portfolio_results['combined_metrics']

    print(f"\n  Combined Portfolio: Sharpe={combined_metrics.get('Sharpe_Ratio', 0):.2f}, "
          f"Calmar={combined_metrics.get('Calmar_Ratio', 0):.2f}, "
          f"PnL=Rs.{combined_metrics.get('Total_Net_PnL', 0):,.0f}")

    timings['Portfolio Construction'] = time.perf_counter() - t

    # ============ Phase 4: Out-of-Sample ============
    t = time.perf_counter()
    all_metrics_oos = []
    if len(oos_opts) > 0:
        strategies_oos = create_strategies()
        oos_results, oos_daily_pnls = run_all_strategies(
            strategies_oos, oos_opts, oos_spot, expiry_map, 'Out-of-Sample'
        )
        all_metrics_oos = [r['metrics'] for r in oos_results.values()]

        print("\n  OUT-OF-SAMPLE RESULTS SUMMARY")
        for name, res in oos_results.items():
            m = res['metrics']
            print(f"  {name:<20} | Trades: {m.get('Total_Trades', 0):>5} | "
                  f"Win: {m.get('Win_Rate', 0):>5.1%} | "
                  f"Sharpe: {m.get('Sharpe_Ratio', 0):>6.2f} | "
                  f"PnL: Rs.{m.get('Total_Net_PnL', 0):>12,.0f}")
    timings['Out-of-Sample'] = time.perf_counter() - t

    # ============ Phase 5: Outputs ============
    t = time.perf_counter()

    # All metrics to include combined
    all_metrics_is_full = all_metrics_is + [combined_metrics]

    # Generate plots
    generate_all_plots(portfolio_results, is_daily_pnls, all_metrics_is_full)

    # Generate Excel
    generate_excel_report(is_results, portfolio_results,
                           all_metrics_is_full, all_metrics_oos)

    # Generate PDF
    generate_pdf_report(is_results, portfolio_results,
                         all_metrics_is_full, all_metrics_oos,
                         execution_timings=timings)

    timings['Output Generation'] = time.perf_counter() - t

    # ============ Final Summary ============
    total = time.perf_counter() - total_start

    print("\n" + "="*70)
    print("  EXECUTION TIMING SUMMARY")
    print("="*70)
    for step, elapsed in timings.items():
        print(f"  {step:<30} {elapsed:>8.2f}s")
    print(f"  {'TOTAL':<30} {total:>8.2f}s")
    print("="*70)

    print("\n  OUTPUT FILES:")
    print("  - output/Qode_Assignment2_Results.xlsx")
    print("  - output/Qode_Assignment2_Report.pdf")
    print("  - output/plots/ (10 PNG files)")
    print("\n  DONE! ✓")


if __name__ == '__main__':
    main()
