"""
Strategy 2: Directional — Momentum Breakout
============================================
- Observation: 09:15 to 09:45
- If spot moved > +0.5% from open: BUY OTM CE (ATM + 150)
- If spot moved > -0.5% from open: BUY OTM PE (ATM - 150)
- Entry: 09:46
- SL: 40% of premium (option drops to 60% of entry)
- Target: 100% gain (option doubles)
- Trailing SL: at 50%+ profit, SL to breakeven; at 80%+, SL to 50% profit
- Time exit: 15:15
- Trade every day including expiry
"""

import pandas as pd
from strategies.base_strategy import BaseStrategy
from config import NIFTY_LOT_SIZE, STRIKE_INTERVAL, MAX_LOTS


class DirectionalStrategy(BaseStrategy):

    def __init__(self, capital, lot_size=NIFTY_LOT_SIZE):
        super().__init__("Directional", capital, lot_size)
        self.observation_start = "09:15"
        self.observation_end = "09:45"
        self.entry_time = "09:46"
        self.exit_time_limit = "15:15"
        self.breakout_threshold = 0.005  # 0.5%
        self.otm_offset = 150  # 3 strikes OTM
        self.sl_pct = 0.40  # 40% SL (exit when option at 60% of entry)
        self.target_pct = 1.00  # 100% gain (option doubles)
        self.trailing_start_pct = 0.50  # Start trailing at 50% profit
        self.trailing_lock_pct = 0.50  # Lock 50% at 80%+ profit

    def generate_signals(self, date, spot_data, options_data, prev_day_spot=None):
        """Generate directional signals based on 09:15-09:45 momentum."""
        # Get spot at observation start and end
        spot_open = self.get_spot_at_time(spot_data, self.observation_start)
        spot_close = self.get_spot_at_time(spot_data, self.observation_end)

        if spot_open is None or spot_close is None:
            return []

        pct_move = (spot_close - spot_open) / spot_open
        atm_strike = self.get_atm_strike(spot_close, STRIKE_INTERVAL)

        if pct_move > self.breakout_threshold:
            # Bullish breakout — buy OTM CE
            strike = atm_strike + self.otm_offset
            option_type = 'CE'
        elif pct_move < -self.breakout_threshold:
            # Bearish breakout — buy OTM PE
            strike = atm_strike - self.otm_offset
            option_type = 'PE'
        else:
            return []  # No trade

        # Get entry price at 09:46
        entry_price = self.get_option_price(options_data, strike, option_type,
                                             self.entry_time, 'close')
        if entry_price is None or entry_price < 2:
            return []

        # Get ticker
        rows = options_data[(options_data['strike'] == strike) &
                             (options_data['option_type'] == option_type)]
        ticker = rows['ticker'].iloc[0] if len(rows) > 0 else f"NIFTY_{strike}_{option_type}"

        leg_group = f"DIR_{date}_{strike}_{option_type}"

        return [{
            'ticker': ticker,
            'strike': strike,
            'option_type': option_type,
            'action': 'BUY',
            'entry_time': self.entry_time,
            'entry_price': entry_price,
            'quantity': self.lot_size * MAX_LOTS,
            'sl_price': entry_price * (1 - self.sl_pct),
            'target_price': entry_price * (1 + self.target_pct),
            'exit_time_limit': self.exit_time_limit,
            'leg_group': leg_group,
        }]

    def check_exit_conditions(self, positions, trading_times, options_data, entry_time):
        """
        Check SL, target, and trailing SL for the long option.
        - SL: Low <= 60% of entry
        - Target: High >= 200% of entry
        - Trailing: at 50%+ profit, SL to breakeven; at 80%+, SL to 50% profit level
        """
        exits = {}

        for leg in positions:
            entry_price = leg['entry_price']
            sl_price = entry_price * (1 - self.sl_pct)
            target_price = entry_price * (1 + self.target_pct)
            trailing_sl = None
            max_price_seen = entry_price

            for t in trading_times:
                bar = self.get_option_bar(options_data, leg['strike'],
                                          leg['option_type'], t)
                if bar is None:
                    continue

                high = float(bar['high'])
                low = float(bar['low'])
                close = float(bar['close'])

                # Update max price seen
                max_price_seen = max(max_price_seen, high)

                # Update trailing SL
                profit_pct = (max_price_seen - entry_price) / entry_price
                if profit_pct >= 0.80:
                    trailing_sl = entry_price * 1.50  # Lock 50% profit
                elif profit_pct >= 0.50:
                    trailing_sl = entry_price  # Breakeven

                # Determine effective SL
                effective_sl = max(sl_price, trailing_sl) if trailing_sl else sl_price

                # Target check (using High for long position)
                if high >= target_price:
                    exits[leg['ticker']] = {
                        'exit_price': target_price,
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                    return exits

                # SL check (using Low for long position)
                if low <= effective_sl:
                    reason = 'TRAILING_SL' if trailing_sl and effective_sl == trailing_sl else 'SL'
                    exits[leg['ticker']] = {
                        'exit_price': effective_sl,
                        'exit_time': t,
                        'exit_reason': reason
                    }
                    return exits

        return exits
