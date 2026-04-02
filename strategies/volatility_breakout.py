"""
Strategy 4: Volatility Breakout — Long Straddle on Opening Range Breakout
=========================================================================
- Entry: 09:16 (first available bar). Buy 1 ATM CE + 1 ATM PE
- Opening range: 09:15-09:45 spot high/low
- At 09:46: if spot > range high, close PE, hold CE (and vice versa)
- At 11:00 if no breakout: close both
- Surviving leg: target 150% of entry, SL 50% of entry
- Time exit: 15:15
- Trade every day including expiry
"""

import pandas as pd
from strategies.base_strategy import BaseStrategy
from config import NIFTY_LOT_SIZE, STRIKE_INTERVAL


class VolatilityBreakoutStrategy(BaseStrategy):

    def __init__(self, capital, lot_size=NIFTY_LOT_SIZE):
        super().__init__("VolBreakout", capital, lot_size)
        self.entry_time = "09:16"
        self.orb_end_time = "09:45"
        self.breakout_check_time = "09:46"
        self.no_breakout_exit_time = "11:00"
        self.exit_time_limit = "15:15"
        self.surviving_target_pct = 1.50  # 150% of entry
        self.surviving_sl_pct = 0.50  # 50% drop from entry

    def generate_signals(self, date, spot_data, options_data, prev_day_spot=None):
        """Generate long straddle signals at 09:16."""
        # Get spot at entry time
        spot = self.get_spot_at_time(spot_data, self.entry_time)
        if spot is None:
            # Try 09:15 or 09:17
            for t in ['09:15', '09:17', '09:18']:
                spot = self.get_spot_at_time(spot_data, t)
                if spot is not None:
                    break
        if spot is None:
            return []

        atm_strike = self.get_atm_strike(spot, STRIKE_INTERVAL)

        # Get entry prices
        entry_t = self.entry_time
        ce_price = self.get_option_price(options_data, atm_strike, 'CE', entry_t, 'close')
        pe_price = self.get_option_price(options_data, atm_strike, 'PE', entry_t, 'close')

        # Try alternate entry time if needed
        if ce_price is None or pe_price is None:
            for t in ['09:15', '09:17', '09:18', '09:19', '09:20']:
                ce_price = self.get_option_price(options_data, atm_strike, 'CE', t, 'close')
                pe_price = self.get_option_price(options_data, atm_strike, 'PE', t, 'close')
                if ce_price is not None and pe_price is not None:
                    entry_t = t
                    break

        if ce_price is None or pe_price is None or ce_price < 2 or pe_price < 2:
            return []

        # Get tickers
        ce_rows = options_data[(options_data['strike'] == atm_strike) &
                                (options_data['option_type'] == 'CE')]
        pe_rows = options_data[(options_data['strike'] == atm_strike) &
                                (options_data['option_type'] == 'PE')]
        ce_ticker = ce_rows['ticker'].iloc[0] if len(ce_rows) > 0 else f"NIFTY_{atm_strike}_CE"
        pe_ticker = pe_rows['ticker'].iloc[0] if len(pe_rows) > 0 else f"NIFTY_{atm_strike}_PE"

        leg_group = f"VB_{date}_{atm_strike}"

        return [
            {
                'ticker': ce_ticker,
                'strike': atm_strike,
                'option_type': 'CE',
                'action': 'BUY',
                'entry_time': entry_t,
                'entry_price': ce_price,
                'quantity': self.lot_size,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
            {
                'ticker': pe_ticker,
                'strike': atm_strike,
                'option_type': 'PE',
                'action': 'BUY',
                'entry_time': entry_t,
                'entry_price': pe_price,
                'quantity': self.lot_size,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            }
        ]

    def check_exit_conditions(self, positions, trading_times, options_data, entry_time):
        """
        Phase 1 (09:16 to 09:46): Track opening range, check breakout at 09:46.
        Phase 2 (post-breakout): Monitor surviving leg with target/SL.
        """
        exits = {}

        if not positions or len(positions) < 2:
            return exits

        ce_leg = None
        pe_leg = None
        for leg in positions:
            if leg['option_type'] == 'CE':
                ce_leg = leg
            elif leg['option_type'] == 'PE':
                pe_leg = leg

        if ce_leg is None or pe_leg is None:
            return exits

        # Phase 1: Determine opening range and breakout
        # Get spot data for opening range (09:15 to 09:45)
        orb_high = float('-inf')
        orb_low = float('inf')

        # We need spot data — access it through options data indirectly
        # Actually, we should compute spot from the ATM options
        # For simplicity, use the ATM call+put to estimate direction
        # Better: just track the straddle value

        # Alternative: use option prices to detect breakout
        # CE rises on upside breakout, PE rises on downside breakout

        # Get times for the ORB window
        orb_times = [t for t in trading_times if t <= self.orb_end_time]
        post_orb_times = [t for t in trading_times if t > self.orb_end_time]

        # Track max/min CE and PE during ORB
        ce_entry = ce_leg['entry_price']
        pe_entry = pe_leg['entry_price']

        # After ORB window, check breakout direction
        breakout_direction = None

        if self.breakout_check_time in [t for t in trading_times]:
            ce_at_breakout = self.get_option_price(
                options_data, ce_leg['strike'], 'CE', self.breakout_check_time, 'close')
            pe_at_breakout = self.get_option_price(
                options_data, pe_leg['strike'], 'PE', self.breakout_check_time, 'close')

            if ce_at_breakout and pe_at_breakout:
                # If CE has gained significantly more than PE lost → upside breakout
                ce_pnl = ce_at_breakout - ce_entry
                pe_pnl = pe_at_breakout - pe_entry

                # Net straddle value change
                net_change = ce_pnl + pe_pnl

                if ce_pnl > 0 and ce_pnl > abs(pe_pnl) * 0.5:
                    breakout_direction = 'UP'
                elif pe_pnl > 0 and pe_pnl > abs(ce_pnl) * 0.5:
                    breakout_direction = 'DOWN'

        # Apply breakout logic
        if breakout_direction == 'UP':
            # Close PE, hold CE
            pe_exit_price = self.get_option_price(
                options_data, pe_leg['strike'], 'PE', self.breakout_check_time, 'close')
            if pe_exit_price:
                exits[pe_leg['ticker']] = {
                    'exit_price': pe_exit_price,
                    'exit_time': self.breakout_check_time,
                    'exit_reason': 'SIGNAL'
                }
            # Monitor CE with target/SL
            surviving_leg = ce_leg
        elif breakout_direction == 'DOWN':
            # Close CE, hold PE
            ce_exit_price = self.get_option_price(
                options_data, ce_leg['strike'], 'CE', self.breakout_check_time, 'close')
            if ce_exit_price:
                exits[ce_leg['ticker']] = {
                    'exit_price': ce_exit_price,
                    'exit_time': self.breakout_check_time,
                    'exit_reason': 'SIGNAL'
                }
            surviving_leg = pe_leg
        else:
            # No breakout — check if it happens later, or close at 11:00
            surviving_leg = None
            for t in post_orb_times:
                if t >= self.no_breakout_exit_time:
                    # Close both legs
                    for leg in [ce_leg, pe_leg]:
                        if leg['ticker'] not in exits:
                            close_p = self.get_option_price(
                                options_data, leg['strike'], leg['option_type'],
                                self.no_breakout_exit_time, 'close')
                            if close_p:
                                exits[leg['ticker']] = {
                                    'exit_price': close_p,
                                    'exit_time': self.no_breakout_exit_time,
                                    'exit_reason': 'TIME'
                                }
                    return exits

        # Phase 2: Monitor surviving leg
        if surviving_leg and surviving_leg['ticker'] not in exits:
            target_price = surviving_leg['entry_price'] * (1 + self.surviving_target_pct)
            sl_price = surviving_leg['entry_price'] * (1 - self.surviving_sl_pct)

            for t in post_orb_times:
                bar = self.get_option_bar(options_data, surviving_leg['strike'],
                                          surviving_leg['option_type'], t)
                if bar is None:
                    continue

                high = float(bar['high'])
                low = float(bar['low'])

                # Target (long position — check high)
                if high >= target_price:
                    exits[surviving_leg['ticker']] = {
                        'exit_price': target_price,
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                    return exits

                # SL (long position — check low)
                if low <= sl_price:
                    exits[surviving_leg['ticker']] = {
                        'exit_price': sl_price,
                        'exit_time': t,
                        'exit_reason': 'SL'
                    }
                    return exits

        return exits
