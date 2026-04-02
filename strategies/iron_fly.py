"""
Strategy 5: Iron Fly — Defined-Risk Mean Reversion
====================================================
- Entry: 09:20
- Sell 1 ATM CE + 1 ATM PE (straddle core)
- Buy 1 OTM CE at ATM+150 (wing) + Buy 1 OTM PE at ATM-150 (wing)
- Net credit = (ATM_CE + ATM_PE) - (OTM_CE + OTM_PE)
- SL: Combined MTM loss > 1.5x net credit, exit all 4 legs
- Target: 50% of net credit
- Time exit: 15:15
- Trade every day including expiry (risk is capped)
"""

import pandas as pd
from strategies.base_strategy import BaseStrategy
from config import NIFTY_LOT_SIZE, STRIKE_INTERVAL


class IronFlyStrategy(BaseStrategy):

    def __init__(self, capital, lot_size=NIFTY_LOT_SIZE):
        super().__init__("IronFly", capital, lot_size)
        self.entry_time = "09:20"
        self.exit_time_limit = "15:15"
        self.wing_offset = 150  # 3 strikes for wings
        self.sl_multiplier = 1.5  # SL: 1.5x net credit
        self.target_pct = 0.50  # Target: 50% of net credit

    def generate_signals(self, date, spot_data, options_data, prev_day_spot=None):
        """Generate Iron Fly signals at 09:20."""
        spot = self.get_spot_at_time(spot_data, self.entry_time)
        if spot is None:
            return []

        atm_strike = self.get_atm_strike(spot, STRIKE_INTERVAL)
        ce_wing_strike = atm_strike + self.wing_offset
        pe_wing_strike = atm_strike - self.wing_offset

        # Get all 4 leg prices
        atm_ce = self.get_option_price(options_data, atm_strike, 'CE',
                                        self.entry_time, 'close')
        atm_pe = self.get_option_price(options_data, atm_strike, 'PE',
                                        self.entry_time, 'close')
        otm_ce = self.get_option_price(options_data, ce_wing_strike, 'CE',
                                        self.entry_time, 'close')
        otm_pe = self.get_option_price(options_data, pe_wing_strike, 'PE',
                                        self.entry_time, 'close')

        if any(p is None for p in [atm_ce, atm_pe, otm_ce, otm_pe]):
            return []

        net_credit = (atm_ce + atm_pe - otm_ce - otm_pe) * self.lot_size
        if net_credit <= 0:
            return []

        leg_group = f"IF_{date}_{atm_strike}"

        # Helper to get ticker
        def get_ticker(strike, opt_type):
            rows = options_data[(options_data['strike'] == strike) &
                                 (options_data['option_type'] == opt_type)]
            return rows['ticker'].iloc[0] if len(rows) > 0 else f"NIFTY_{strike}_{opt_type}"

        signals = [
            # Sell ATM CE
            {
                'ticker': get_ticker(atm_strike, 'CE'),
                'strike': atm_strike,
                'option_type': 'CE',
                'action': 'SELL',
                'entry_time': self.entry_time,
                'entry_price': atm_ce,
                'quantity': self.lot_size,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
            # Sell ATM PE
            {
                'ticker': get_ticker(atm_strike, 'PE'),
                'strike': atm_strike,
                'option_type': 'PE',
                'action': 'SELL',
                'entry_time': self.entry_time,
                'entry_price': atm_pe,
                'quantity': self.lot_size,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
            # Buy OTM CE (wing)
            {
                'ticker': get_ticker(ce_wing_strike, 'CE'),
                'strike': ce_wing_strike,
                'option_type': 'CE',
                'action': 'BUY',
                'entry_time': self.entry_time,
                'entry_price': otm_ce,
                'quantity': self.lot_size,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
            # Buy OTM PE (wing)
            {
                'ticker': get_ticker(pe_wing_strike, 'PE'),
                'strike': pe_wing_strike,
                'option_type': 'PE',
                'action': 'BUY',
                'entry_time': self.entry_time,
                'entry_price': otm_pe,
                'quantity': self.lot_size,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
        ]

        # Store net credit for exit logic
        for s in signals:
            s['_net_credit'] = net_credit

        return signals

    def check_exit_conditions(self, positions, trading_times, options_data, entry_time):
        """
        Check combined MTM for all 4 legs of the Iron Fly.
        SL: Combined MTM loss > 1.5x net credit
        Target: Combined MTM profit > 50% of net credit
        """
        exits = {}

        if len(positions) < 4:
            return exits

        # Identify legs
        sell_ce = sell_pe = buy_ce = buy_pe = None
        for leg in positions:
            if leg['action'] == 'SELL' and leg['option_type'] == 'CE':
                sell_ce = leg
            elif leg['action'] == 'SELL' and leg['option_type'] == 'PE':
                sell_pe = leg
            elif leg['action'] == 'BUY' and leg['option_type'] == 'CE':
                buy_ce = leg
            elif leg['action'] == 'BUY' and leg['option_type'] == 'PE':
                buy_pe = leg

        if any(x is None for x in [sell_ce, sell_pe, buy_ce, buy_pe]):
            return exits

        # Compute net credit at entry
        net_credit = ((sell_ce['entry_price'] + sell_pe['entry_price']) -
                      (buy_ce['entry_price'] + buy_pe['entry_price'])) * self.lot_size

        sl_threshold = net_credit * self.sl_multiplier
        target_threshold = net_credit * self.target_pct

        for t in trading_times:
            # Get worst-case MTM (for SL): use High for shorts, Low for longs
            sc_high = self.get_option_price(options_data, sell_ce['strike'], 'CE', t, 'high')
            sp_high = self.get_option_price(options_data, sell_pe['strike'], 'PE', t, 'high')
            bc_low = self.get_option_price(options_data, buy_ce['strike'], 'CE', t, 'low')
            bp_low = self.get_option_price(options_data, buy_pe['strike'], 'PE', t, 'low')

            if any(p is None for p in [sc_high, sp_high, bc_low, bp_low]):
                continue

            # Worst case PnL
            worst_pnl = ((sell_ce['entry_price'] - sc_high + sell_pe['entry_price'] - sp_high +
                          bc_low - buy_ce['entry_price'] + bp_low - buy_pe['entry_price'])
                         * self.lot_size)

            if worst_pnl < -sl_threshold:
                # SL hit — exit all 4 legs at close prices
                for leg in [sell_ce, sell_pe, buy_ce, buy_pe]:
                    close_p = self.get_option_price(
                        options_data, leg['strike'], leg['option_type'], t, 'close')
                    exits[leg['ticker']] = {
                        'exit_price': close_p or leg['entry_price'],
                        'exit_time': t,
                        'exit_reason': 'COMBINED_SL'
                    }
                return exits

            # Best case MTM (for target): use Low for shorts, High for longs
            sc_low = self.get_option_price(options_data, sell_ce['strike'], 'CE', t, 'low')
            sp_low = self.get_option_price(options_data, sell_pe['strike'], 'PE', t, 'low')
            bc_high = self.get_option_price(options_data, buy_ce['strike'], 'CE', t, 'high')
            bp_high = self.get_option_price(options_data, buy_pe['strike'], 'PE', t, 'high')

            if any(p is None for p in [sc_low, sp_low, bc_high, bp_high]):
                continue

            best_pnl = ((sell_ce['entry_price'] - sc_low + sell_pe['entry_price'] - sp_low +
                         bc_high - buy_ce['entry_price'] + bp_high - buy_pe['entry_price'])
                        * self.lot_size)

            if best_pnl >= target_threshold:
                for leg in [sell_ce, sell_pe, buy_ce, buy_pe]:
                    price_col = 'low' if leg['action'] == 'SELL' else 'high'
                    exit_p = self.get_option_price(
                        options_data, leg['strike'], leg['option_type'], t, price_col)
                    exits[leg['ticker']] = {
                        'exit_price': exit_p or leg['entry_price'],
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                return exits

        return exits
