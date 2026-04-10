"""
Backtester Engine
=================
Runs strategies over historical data, manages positions,
computes PnL with transaction costs, and generates tradesheets.
"""

import pandas as pd
import numpy as np
from tqdm import tqdm
from config import (BROKERAGE_PER_ORDER, STT_SELL_RATE, EXCHANGE_TXN_RATE,
                    GST_RATE, SLIPPAGE_PER_UNIT, NIFTY_LOT_SIZE, BASE_NAV,
                    CAPITAL_PER_STRATEGY)


def calculate_transaction_costs(entry_price, exit_price, quantity, action, exit_reason=None):
    """
    Calculate total transaction costs for a single leg trade.

    Args:
        entry_price: Price at entry
        exit_price: Price at exit
        quantity: Number of units traded (positive)
        action: 'BUY' or 'SELL' (the opening action)
        exit_reason: Reason for exit (to apply SL penalty)

    Returns:
        Total transaction cost in rupees
    """
    entry_value = entry_price * quantity
    exit_value = exit_price * quantity

    # Brokerage: Rs.20 per order, 2 orders (entry + exit)
    brokerage = BROKERAGE_PER_ORDER * 2

    # STT: on sell side only
    if action == 'SELL':
        stt = entry_value * STT_SELL_RATE  # Selling at entry
    else:
        stt = exit_value * STT_SELL_RATE   # Selling at exit

    # Exchange transaction charges: on both sides
    exchange = (entry_value + exit_value) * EXCHANGE_TXN_RATE

    # GST: 18% on (brokerage + exchange charges)
    gst = (brokerage + exchange) * GST_RATE

    # Slippage: on both entry and exit
    slippage = SLIPPAGE_PER_UNIT * quantity * 2

    total_cost = brokerage + stt + exchange + gst + slippage
    return round(total_cost, 2)


def run_backtest(strategy, options_data, spot_data, expiry_map=None,
                 strategy_capital=None, verbose=True):
    """
    Run a backtest for a single strategy.

    Args:
        strategy: An instance of a BaseStrategy subclass
        options_data: DataFrame with all options data for the period
        spot_data: DataFrame with derived spot prices
        expiry_map: Dict mapping date -> nearest expiry folder
        strategy_capital: Capital allocated to this strategy

    Returns:
        tradesheet: DataFrame with all trades
        daily_pnl: Series indexed by date with daily net PnL
    """
    if strategy_capital is None:
        strategy_capital = CAPITAL_PER_STRATEGY

    # Pre-group data by date for fast access (avoids repeated 71M row filter)
    if verbose:
        print(f"\n  Pre-indexing data for {strategy.name}...")

    opts_by_date = dict(list(options_data.groupby('date')))
    spot_by_date = dict(list(spot_data.groupby('date')))

    # Valid dates present in both
    valid_dates = sorted(set(opts_by_date.keys()) & set(spot_by_date.keys()))

    if verbose:
        print(f"  Running {strategy.name} on {len(valid_dates)} trading days...")

    all_trades = []
    prev_day_spot = None

    for date in tqdm(valid_dates, desc=strategy.name, disable=not verbose):
        # Get pre-grouped data
        day_spot = spot_by_date[date]
        day_opts = opts_by_date[date]

        if len(day_spot) == 0 or len(day_opts) == 0:
            continue

        # If we have expiry_map, filter to nearest expiry for cleaner data
        if expiry_map is not None and date in expiry_map:
            nearest_exp = expiry_map[date]
            if nearest_exp is not None:
                exp_opts = day_opts[day_opts['expiry_folder'] == nearest_exp]
                if len(exp_opts) > 0:
                    day_opts = exp_opts

        # Generate entry signals
        try:
            signals = strategy.generate_signals(date, day_spot, day_opts, prev_day_spot)
        except Exception as e:
            if verbose:
                print(f"  Signal error on {date}: {e}")
            signals = []

        if signals:
            # Process each signal group
            day_trades = _process_signals(strategy, signals, date,
                                          day_spot, day_opts)
            all_trades.extend(day_trades)

        # Update previous day spot for next iteration
        spot_1529 = day_spot[day_spot['time'] == '15:29']
        if len(spot_1529) > 0:
            prev_day_spot = float(spot_1529.iloc[0]['spot_close'])
        elif len(day_spot) > 0:
            prev_day_spot = float(day_spot.iloc[-1]['spot_close'])

    if not all_trades:
        print(f"WARNING: {strategy.name} generated no trades!")
        return pd.DataFrame(), pd.Series(dtype=float)

    # Build tradesheet
    tradesheet = pd.DataFrame(all_trades)

    # Compute PnL for each trade
    tradesheet = _compute_trade_pnl(tradesheet, strategy_capital)

    # Compute daily PnL
    daily_pnl = tradesheet.groupby('date')['net_pnl'].sum()
    daily_pnl = daily_pnl.reindex(valid_dates, fill_value=0)

    if verbose:
        total_pnl = tradesheet['net_pnl'].sum()
        win_rate = (tradesheet['net_pnl'] > 0).mean()
        print(f"  {strategy.name}: {len(tradesheet)} trades, "
              f"Win rate: {win_rate:.1%}, Total PnL: Rs.{total_pnl:,.0f}")

    return tradesheet, daily_pnl


def _process_signals(strategy, signals, date, day_spot, day_opts):
    """
    Process entry signals: find exit points for each position.

    For each signal, simulate the intraday position and determine
    when to exit based on strategy's exit logic.
    """
    trades = []

    # Group signals by leg_group (for multi-leg strategies)
    from collections import defaultdict
    leg_groups = defaultdict(list)
    for sig in signals:
        leg_groups[sig['leg_group']].append(sig)

    for group_name, group_legs in leg_groups.items():
        # Get all available times for this day
        available_times = sorted(day_opts['time'].unique())
        if not available_times:
            continue

        # Find the entry time (all legs in a group enter at the same time)
        entry_time = group_legs[0]['entry_time']
        exit_time_limit = group_legs[0].get('exit_time_limit', '15:15')

        # Get times from entry onwards
        trading_times = [t for t in available_times if t > entry_time and t <= exit_time_limit]

        # Track active positions
        active_legs = []
        for leg in group_legs:
            active_legs.append({
                'ticker': leg['ticker'],
                'strike': leg['strike'],
                'option_type': leg['option_type'],
                'action': leg['action'],
                'entry_time': leg['entry_time'],
                'entry_price': leg['entry_price'],
                'quantity': leg['quantity'],
                'sl_price': leg.get('sl_price'),
                'target_price': leg.get('target_price'),
                'exited': False,
                'exit_price': None,
                'exit_time': None,
                'exit_reason': None
            })

        # Check exits using strategy's logic
        exits = strategy.check_exit_conditions(
            active_legs, trading_times, day_opts, entry_time
        )

        # Apply exits
        for leg in active_legs:
            exit_info = exits.get(leg['ticker'], None)
            if exit_info:
                leg['exit_price'] = exit_info['exit_price']
                leg['exit_time'] = exit_info['exit_time']
                leg['exit_reason'] = exit_info['exit_reason']
            else:
                # Time exit at exit_time_limit using close price
                exit_price = strategy.get_option_price(
                    day_opts, leg['strike'], leg['option_type'],
                    exit_time_limit, 'close'
                )
                if exit_price is None:
                    # Try 15:15, then last available time
                    for fallback_time in ['15:15', '15:14', '15:13', '15:29']:
                        exit_price = strategy.get_option_price(
                            day_opts, leg['strike'], leg['option_type'],
                            fallback_time, 'close'
                        )
                        if exit_price is not None:
                            exit_time_limit = fallback_time
                            break
                if exit_price is None:
                    exit_price = leg['entry_price']  # Worst case: flat
                leg['exit_price'] = exit_price
                leg['exit_time'] = exit_time_limit
                leg['exit_reason'] = 'TIME'

            # Get Nifty close for this trade
            nifty_close = strategy.get_spot_at_time(
                day_spot[day_spot['date'] == date] if 'date' in day_spot.columns else day_spot,
                leg['exit_time']
            )
            if nifty_close is None:
                nifty_close = strategy.get_spot_at_time(
                    day_spot[day_spot['date'] == date] if 'date' in day_spot.columns else day_spot,
                    '15:29'
                )

            trades.append({
                'date': date,
                'ticker': leg['ticker'],
                'option_type': leg['option_type'],
                'strike': leg['strike'],
                'action': leg['action'],
                'entry_time': leg['entry_time'],
                'entry_price': leg['entry_price'],
                'exit_time': leg['exit_time'],
                'exit_price': leg['exit_price'],
                'exit_reason': leg['exit_reason'],
                'quantity': leg['quantity'],
                'lot_size': NIFTY_LOT_SIZE,
                'nifty_close': nifty_close or 0,
                'leg_group': group_name
            })

    return trades


def _compute_trade_pnl(tradesheet, capital):
    """Compute gross PnL, transaction costs, and net PnL for each trade."""
    # Gross PnL
    gross_pnl = []
    txn_costs = []

    for _, row in tradesheet.iterrows():
        entry_p = row['entry_price']
        exit_p = row['exit_price']
        qty = row['quantity']
        action = row['action']

        if action == 'SELL':
            # Short: profit when price drops
            gpnl = (entry_p - exit_p) * qty
        else:
            # Long: profit when price rises
            gpnl = (exit_p - entry_p) * qty

        tc = calculate_transaction_costs(entry_p, exit_p, qty, action, row['exit_reason'])
        gross_pnl.append(round(gpnl, 2))
        txn_costs.append(tc)

    tradesheet['gross_pnl'] = gross_pnl
    tradesheet['txn_costs'] = txn_costs
    tradesheet['net_pnl'] = tradesheet['gross_pnl'] - tradesheet['txn_costs']

    # Entry and exit values
    tradesheet['entry_value'] = tradesheet['entry_price'] * tradesheet['quantity']
    tradesheet['exit_value'] = tradesheet['exit_price'] * tradesheet['quantity']

    # PnL percentage (based on entry value)
    tradesheet['pnl_pct'] = np.where(
        tradesheet['entry_value'] > 0,
        (tradesheet['net_pnl'] / tradesheet['entry_value'] * 100),
        0
    )

    # Cumulative PnL and NAV
    tradesheet['cumulative_pnl'] = tradesheet['net_pnl'].cumsum()
    tradesheet['nav'] = BASE_NAV * (1 + tradesheet['cumulative_pnl'] / capital)
    tradesheet['available_cap'] = capital + tradesheet['cumulative_pnl']

    return tradesheet
