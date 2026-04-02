"""
Excel Report Generator
======================
Generates the comprehensive Excel workbook with all 10 sheets.
"""

import pandas as pd
import numpy as np
import os
from config import BASE_NAV, STARTING_CAPITAL, CAPITAL_PER_STRATEGY


def generate_excel_report(strategy_results: dict, portfolio_results: dict,
                           all_metrics_is: list, all_metrics_oos: list = None,
                           output_path='output/Qode_Assignment2_Results.xlsx'):
    """
    Generate the comprehensive Excel workbook.

    Args:
        strategy_results: Dict of name -> {'tradesheet', 'daily_pnl', 'metrics'}
        portfolio_results: Dict from build_portfolio_results
        all_metrics_is: List of metrics dicts for in-sample
        all_metrics_oos: Optional list for out-of-sample
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Define formats
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1B2838', 'font_color': '#FFFFFF',
            'border': 1, 'text_wrap': True, 'valign': 'vcenter',
            'font_size': 11
        })
        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'font_size': 10})
        pct_fmt = workbook.add_format({'num_format': '0.00%', 'font_size': 10})
        green_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'font_color': '#00B050', 'font_size': 10
        })
        red_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'font_color': '#FF0000', 'font_size': 10
        })
        text_fmt = workbook.add_format({'font_size': 10, 'text_wrap': True})

        # ============ Sheet 1: Guide ============
        _write_guide_sheet(writer, workbook, header_fmt, text_fmt)

        # ============ Sheets 2-6: Tradesheets ============
        sheet_names = {
            'MeanReversion': 'Tradesheet_MeanReversion',
            'Directional': 'Tradesheet_Directional',
            'SemiDirectional': 'Tradesheet_SemiDirectional'
        }

        for strat_name, sheet_name in sheet_names.items():
            if strat_name in strategy_results and 'tradesheet' in strategy_results[strat_name]:
                ts = strategy_results[strat_name]['tradesheet'].copy()
                if len(ts) > 0:
                    # Select and order columns
                    cols = ['ticker', 'option_type', 'strike', 'action',
                            'date', 'entry_time', 'entry_price',
                            'exit_time', 'exit_price', 'exit_reason',
                            'nifty_close', 'lot_size', 'quantity',
                            'entry_value', 'exit_value',
                            'gross_pnl', 'txn_costs', 'net_pnl',
                            'pnl_pct', 'cumulative_pnl', 'nav', 'available_cap']
                    available_cols = [c for c in cols if c in ts.columns]
                    ts = ts[available_cols]

                    ts.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
                    ws = writer.sheets[sheet_name]

                    # Format headers
                    for col_idx, col_name in enumerate(available_cols):
                        ws.write(0, col_idx, col_name, header_fmt)

                    # Auto-filter and freeze
                    ws.autofilter(0, 0, len(ts), len(available_cols) - 1)
                    ws.freeze_panes(1, 0)

                    # Column widths
                    for col_idx, col_name in enumerate(available_cols):
                        max_len = max(len(str(col_name)), ts[col_name].astype(str).str.len().max())
                        ws.set_column(col_idx, col_idx, min(max_len + 2, 20))

                    # Conditional formatting for PnL columns
                    if 'net_pnl' in available_cols:
                        pnl_col = available_cols.index('net_pnl')
                        ws.conditional_format(1, pnl_col, len(ts), pnl_col, {
                            'type': 'cell', 'criteria': '>', 'value': 0,
                            'format': green_fmt
                        })
                        ws.conditional_format(1, pnl_col, len(ts), pnl_col, {
                            'type': 'cell', 'criteria': '<', 'value': 0,
                            'format': red_fmt
                        })
                else:
                    pd.DataFrame({'Note': ['No trades generated']}).to_excel(
                        writer, sheet_name=sheet_name, index=False)

        # ============ Sheet 7: Statistics ============
        _write_statistics_sheet(writer, workbook, all_metrics_is, all_metrics_oos,
                                 header_fmt, num_fmt)

        # ============ Sheet 8: Monthly PnL ============
        _write_monthly_pnl_sheet(writer, workbook, portfolio_results, header_fmt, num_fmt)

        # ============ Sheet 9: Equity Curves ============
        _write_equity_curves_sheet(writer, workbook, portfolio_results, header_fmt, num_fmt)

        # ============ Sheet 10: Portfolio Allocation ============
        _write_allocation_sheet(writer, workbook, portfolio_results, header_fmt, text_fmt, num_fmt)

    print(f"Excel report saved to {output_path}")


def _write_guide_sheet(writer, workbook, header_fmt, text_fmt):
    """Write the Guide/methodology sheet."""
    guide_data = [
        ['Nifty Intraday Options Strategies — Backtest Results', ''],
        ['', ''],
        ['Strategy', 'Description'],
        ['1. Mean Reversion', 'Short ATM Straddle at 09:20. Combined premium SL (1.5x) and Target (0.5x). Skip expiry.'],
        ['2. Directional', 'Momentum breakout: Buy OTM option after 0.5%+ move in 09:15-09:45 window. Trailing SL.'],
        ['3. Semi-Directional', 'Ratio credit spread based on overnight gap + 10-min momentum. 2:1 ratio sells.'],
        ['', ''],
        ['Column', 'Definition'],
        ['Ticker', 'Option symbol (NIFTY_Strike_CE/PE_Expiry)'],
        ['Action', 'BUY = long position, SELL = short position'],
        ['EntryPrice/ExitPrice', 'Option premium at entry/exit'],
        ['ExitReason', 'SL = Stop-loss, TARGET = Profit target, TIME = End-of-day exit, COMBINED_SL = Combined premium SL'],
        ['GrossPnl', 'PnL before transaction costs'],
        ['TxnCosts', 'Brokerage + STT + Exchange charges + GST + Slippage'],
        ['NetPnl', 'GrossPnl - TxnCosts'],
        ['NAV', 'Net Asset Value, base 100'],
        ['AvailableCap', 'Remaining capital after cumulative PnL'],
        ['', ''],
        ['Data', 'Details'],
        ['Period', 'Oct 2024 to Mar 2026 (In-sample: Oct 2024 - Oct 2025, OOS: Nov 2025 - Mar 2026)'],
        ['Capital', 'Rs. 1 Crore total, Rs. 33.3 Lakhs per strategy'],
        ['Lot Size', '25 (Nifty lot size from April 2024)'],
        ['Transaction Costs', '0 (Zero transaction costs assumed as per requirements)'],
    ]

    df = pd.DataFrame(guide_data, columns=['Key', 'Value'])
    df.to_excel(writer, sheet_name='Guide', index=False, startrow=0)
    ws = writer.sheets['Guide']
    ws.set_column(0, 0, 25)
    ws.set_column(1, 1, 100)


def _write_statistics_sheet(writer, workbook, all_metrics_is, all_metrics_oos,
                              header_fmt, num_fmt):
    """Write the Statistics sheet with all 16 metrics."""
    # In-sample metrics
    is_df = pd.DataFrame(all_metrics_is)
    if 'Strategy' in is_df.columns:
        is_df = is_df.set_index('Strategy')
    is_df = is_df.T
    is_df.index.name = 'Metric'

    is_df.to_excel(writer, sheet_name='Statistics', startrow=1, startcol=0)
    ws = writer.sheets['Statistics']
    ws.write(0, 0, 'IN-SAMPLE METRICS', header_fmt)
    ws.set_column(0, 0, 25)

    # OOS metrics below
    if all_metrics_oos:
        start_row = len(is_df) + 4
        ws.write(start_row, 0, 'OUT-OF-SAMPLE METRICS', header_fmt)
        oos_df = pd.DataFrame(all_metrics_oos)
        if 'Strategy' in oos_df.columns:
            oos_df = oos_df.set_index('Strategy')
        oos_df = oos_df.T
        oos_df.to_excel(writer, sheet_name='Statistics', startrow=start_row + 1, startcol=0)


def _write_monthly_pnl_sheet(writer, workbook, portfolio_results, header_fmt, num_fmt):
    """Write monthly returns sheet."""
    monthly = portfolio_results.get('monthly_returns', {})
    if monthly:
        df = pd.DataFrame(monthly)
        df.index = pd.to_datetime(df.index).strftime('%Y-%m')
        df.index.name = 'Month'
        df.to_excel(writer, sheet_name='Monthly_PnL', startrow=1)
        ws = writer.sheets['Monthly_PnL']
        ws.write(0, 0, 'Monthly Returns (%)', header_fmt)


def _write_equity_curves_sheet(writer, workbook, portfolio_results, header_fmt, num_fmt):
    """Write daily NAV values."""
    nav_series = portfolio_results.get('nav_series', {})
    if nav_series:
        df = pd.DataFrame(nav_series)
        df.index.name = 'Date'
        df.to_excel(writer, sheet_name='Equity_Curves', startrow=1)
        ws = writer.sheets['Equity_Curves']
        ws.write(0, 0, 'Daily NAV Values (Base 100)', header_fmt)


def _write_allocation_sheet(writer, workbook, portfolio_results, header_fmt, text_fmt, num_fmt):
    """Write portfolio allocation details."""
    ws_name = 'Portfolio_Allocation'

    # Weights
    weights = portfolio_results.get('weights', {})
    weights_df = pd.DataFrame(list(weights.items()), columns=['Strategy', 'Weight'])
    weights_df['Weight_Pct'] = weights_df['Weight'] * 100
    weights_df.to_excel(writer, sheet_name=ws_name, startrow=1, index=False)

    ws = writer.sheets[ws_name]
    ws.write(0, 0, 'Portfolio Allocation', header_fmt)

    # Correlation matrix
    corr = portfolio_results.get('correlation_matrix', None)
    if corr is not None:
        start_row = len(weights_df) + 4
        ws.write(start_row, 0, 'Correlation Matrix', header_fmt)
        corr.to_excel(writer, sheet_name=ws_name, startrow=start_row + 1)

    # Combined metrics
    combined_metrics = portfolio_results.get('combined_metrics', {})
    if combined_metrics:
        start_row = len(weights_df) + (len(corr) if corr is not None else 0) + 8
        ws.write(start_row, 0, 'Combined Portfolio Metrics', header_fmt)
        metrics_df = pd.DataFrame(list(combined_metrics.items()), columns=['Metric', 'Value'])
        metrics_df.to_excel(writer, sheet_name=ws_name, startrow=start_row + 1, index=False)
