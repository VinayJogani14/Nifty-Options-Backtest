"""
Strategy 3: Semi-Directional — Ratio Put/Call Credit Spread
============================================================
- Bias determination at 09:25 using overnight gap + first 10min momentum
- BULLISH: Sell 2 OTM PE (ATM-200), Buy 1 OTM PE (ATM-100)
- BEARISH: Sell 2 OTM CE (ATM+200), Buy 1 OTM CE (ATM+100)
- Entry: 09:30
- SL: Combined MTM loss > 2x net credit
- Target: 60% of net credit
- Time exit: 15:15
- Skip expiry day
"""

import pandas as pd
from strategies.base_strategy import BaseStrategy
from config import NIFTY_LOT_SIZE, STRIKE_INTERVAL


class SemiDirectionalStrategy(BaseStrategy):

    def __init__(self, capital, lot_size=NIFTY_LOT_SIZE):
        super().__init__("SemiDirectional", capital, lot_size)
        self.entry_time = "09:30"
        self.exit_time_limit = "15:15"
        self.gap_threshold = 0.001  # 0.1% first 10-min move
        self.sell_offset = 200  # 4 strikes OTM for selling
        self.buy_offset = 100  # 2 strikes OTM for buying (hedge)
        self.sl_multiplier = 2.0  # Exit if MTM loss > 2x net credit
        self.target_pct = 0.60  # Target: 60% of net credit

    def generate_signals(self, date, spot_data, options_data, prev_day_spot=None):
        """Generate ratio spread signals based on bias at 09:25."""
        # Skip expiry day
        if self.is_expiry_day(date):
            return []

        if prev_day_spot is None:
            return []

        # Get spot at 09:15 and 09:25
        spot_open = self.get_spot_at_time(spot_data, "09:15")
        spot_0925 = self.get_spot_at_time(spot_data, "09:25")

        if spot_open is None or spot_0925 is None:
            return []

        # Dynamic Size calculation: 90% of Capital / 1,20,000 margin per ratio lot
        margin_per_lot = 120000
        num_lots = max(1, int((self.capital * 0.90) // margin_per_lot))

        # Determine bias
        overnight_gap = spot_0925 > prev_day_spot
        first_10min_move = (spot_0925 - spot_open) / spot_open

        if overnight_gap and first_10min_move > self.gap_threshold:
            bias = 'BULLISH'
        elif not overnight_gap and first_10min_move < -self.gap_threshold:
            bias = 'BEARISH'
        else:
            return []  # NEUTRAL — skip

        atm_strike = self.get_atm_strike(spot_0925, STRIKE_INTERVAL)

        if bias == 'BULLISH':
            # Sell 2 OTM PE, Buy 1 OTM PE
            sell_strike = atm_strike - self.sell_offset
            buy_strike = atm_strike - self.buy_offset
            option_type = 'PE'
        else:
            # Sell 2 OTM CE, Buy 1 OTM CE
            sell_strike = atm_strike + self.sell_offset
            buy_strike = atm_strike + self.buy_offset
            option_type = 'CE'

        # Get prices at entry time
        sell_price = self.get_option_price(options_data, sell_strike, option_type,
                                            self.entry_time, 'close')
        buy_price = self.get_option_price(options_data, buy_strike, option_type,
                                           self.entry_time, 'close')

        if sell_price is None or buy_price is None:
            return []

        if sell_price < 2 or buy_price < 1:
            return []

        # Net credit = 2 * sell_premium - 1 * buy_premium (per lot)
        net_credit = (2 * sell_price - buy_price) * self.lot_size

        if net_credit <= 0:
            return []  # No credit — skip

        # Get tickers
        sell_rows = options_data[(options_data['strike'] == sell_strike) &
                                  (options_data['option_type'] == option_type)]
        buy_rows = options_data[(options_data['strike'] == buy_strike) &
                                 (options_data['option_type'] == option_type)]

        sell_ticker = sell_rows['ticker'].iloc[0] if len(sell_rows) > 0 else f"NIFTY_{sell_strike}_{option_type}"
        buy_ticker = buy_rows['ticker'].iloc[0] if len(buy_rows) > 0 else f"NIFTY_{buy_strike}_{option_type}"

        leg_group = f"SD_{date}_{bias}_{sell_strike}"

        signals = [
            {
                'ticker': sell_ticker,
                'strike': sell_strike,
                'option_type': option_type,
                'action': 'SELL',
                'entry_time': self.entry_time,
                'entry_price': sell_price,
                'quantity': self.lot_size * 2 * num_lots,  # Ratio 2:1
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
            {
                'ticker': buy_ticker,
                'strike': buy_strike,
                'option_type': option_type,
                'action': 'BUY',
                'entry_time': self.entry_time,
                'entry_price': buy_price,
                'quantity': self.lot_size * num_lots,  # 1 lot hedge
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            }
        ]

        # Store net credit for exit logic
        for s in signals:
            s['_net_credit'] = net_credit
            s['_bias'] = bias

        return signals

    def check_exit_conditions(self, positions, trading_times, options_data, entry_time):
        """
        Check combined MTM loss vs net credit for the ratio spread.
        SL: Combined MTM loss > 2x net credit
        Target: MTM profit > 60% of net credit
        """
        exits = {}

        if not positions or len(positions) < 2:
            return exits

        # Identify legs
        sell_leg = None
        buy_leg = None
        for leg in positions:
            if leg['action'] == 'SELL':
                sell_leg = leg
            elif leg['action'] == 'BUY':
                buy_leg = leg

        if sell_leg is None or buy_leg is None:
            return exits

        # Calculate net credit at entry
        net_credit_entry = (sell_leg['entry_price'] * sell_leg['quantity'] -
                            buy_leg['entry_price'] * buy_leg['quantity'])
        sl_loss_threshold = net_credit_entry * self.sl_multiplier
        target_profit = net_credit_entry * self.target_pct

        for t in trading_times:
            # Get current prices
            sell_high = self.get_option_price(options_data, sell_leg['strike'],
                                              sell_leg['option_type'], t, 'high')
            sell_low = self.get_option_price(options_data, sell_leg['strike'],
                                             sell_leg['option_type'], t, 'low')
            buy_high = self.get_option_price(options_data, buy_leg['strike'],
                                             buy_leg['option_type'], t, 'high')
            buy_low = self.get_option_price(options_data, buy_leg['strike'],
                                            buy_leg['option_type'], t, 'low')

            if sell_high is None or buy_low is None:
                continue

            # Worst case MTM for shorts (using highest buyback cost)
            # For the short legs: cost to close = sell_high * sell_qty
            # For the long leg: value = buy_low * buy_qty
            worst_mtm = (sell_leg['entry_price'] * sell_leg['quantity'] -
                         sell_high * sell_leg['quantity'] +
                         buy_low * buy_leg['quantity'] -
                         buy_leg['entry_price'] * buy_leg['quantity'])

            # SL check: if loss exceeds threshold
            if worst_mtm < -sl_loss_threshold:
                sell_close = self.get_option_price(options_data, sell_leg['strike'],
                                                    sell_leg['option_type'], t, 'close')
                buy_close = self.get_option_price(options_data, buy_leg['strike'],
                                                   buy_leg['option_type'], t, 'close')
                exits[sell_leg['ticker']] = {
                    'exit_price': sell_close or sell_high,
                    'exit_time': t,
                    'exit_reason': 'COMBINED_SL'
                }
                exits[buy_leg['ticker']] = {
                    'exit_price': buy_close or buy_low,
                    'exit_time': t,
                    'exit_reason': 'COMBINED_SL'
                }
                return exits

            # Best case MTM for target (using lowest buyback for shorts)
            if sell_low is not None and buy_high is not None:
                best_mtm = (sell_leg['entry_price'] * sell_leg['quantity'] -
                            sell_low * sell_leg['quantity'] +
                            buy_high * buy_leg['quantity'] -
                            buy_leg['entry_price'] * buy_leg['quantity'])

                if best_mtm >= target_profit:
                    exits[sell_leg['ticker']] = {
                        'exit_price': sell_low,
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                    exits[buy_leg['ticker']] = {
                        'exit_price': buy_high,
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                    return exits

        return exits
