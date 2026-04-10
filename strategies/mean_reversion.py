"""
Strategy 1: Mean Reversion — Short Straddle with Combined SL
=============================================================
- Entry: 09:20
- Sell 1 ATM CE + 1 ATM PE
- Combined SL: if (CE + PE) buyback > 1.5x entry premiums, exit both
- Target: if (CE + PE) buyback < 0.5x entry premiums, exit both
- Time exit: 15:15
- Skip expiry day (Thursday)
"""

import pandas as pd
from strategies.base_strategy import BaseStrategy
from config import NIFTY_LOT_SIZE, STRIKE_INTERVAL


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy:
    Sells ATM Straddle at 09:30 and holds until 15:15 or combined SL.
    """

    def __init__(self, capital, lot_size=NIFTY_LOT_SIZE):
        super().__init__("MeanReversion", capital, lot_size)
        self.entry_time = "09:30"
        self.exit_time_limit = "15:15"
        self.sl_multiplier = 1.5  # Combined SL: 1.5x entry premiums
        self.target_multiplier = 0.5  # Target: 50% of entry premiums

    def generate_signals(self, date, spot_data, options_data, prev_day_spot=None):
        """Generate short straddle signals at 09:30 on non-expiry days."""
        # Skip expiry day
        if self.is_expiry_day(date):
            return []

        # Get spot at entry time
        spot = self.get_spot_at_time(spot_data, self.entry_time)
        if spot is None:
            return []

        # Get ATM strike
        atm_strike = self.get_atm_strike(spot, STRIKE_INTERVAL)

        # Get CE and PE prices at entry time
        ce_price = self.get_option_price(options_data, atm_strike, 'CE',
                                          self.entry_time, 'close')
        pe_price = self.get_option_price(options_data, atm_strike, 'PE',
                                          self.entry_time, 'close')

        if ce_price is None or pe_price is None:
            return []

        # Dynamic Size calculation: 90% of Capital / 1,50,000 margin per straddle lot
        margin_per_lot = 150000
        num_lots = max(1, int((self.capital * 0.90) // margin_per_lot))

        # Skip if premiums are too low (< 5)
        if ce_price < 5 or pe_price < 5:
            return []

        leg_group = f"MR_{date}_{atm_strike}"

        # Get tickers from options data
        ce_rows = options_data[(options_data['strike'] == atm_strike) &
                                (options_data['option_type'] == 'CE')]
        pe_rows = options_data[(options_data['strike'] == atm_strike) &
                                (options_data['option_type'] == 'PE')]

        ce_ticker = ce_rows['ticker'].iloc[0] if len(ce_rows) > 0 else f"NIFTY_{atm_strike}_CE"
        pe_ticker = pe_rows['ticker'].iloc[0] if len(pe_rows) > 0 else f"NIFTY_{atm_strike}_PE"

        signals = [
            {
                'ticker': ce_ticker,
                'strike': atm_strike,
                'option_type': 'CE',
                'action': 'SELL',
                'entry_time': self.entry_time,
                'entry_price': ce_price,
                'quantity': self.lot_size * num_lots,
                'sl_price': None,  # Combined SL handled in exit logic
                'target_price': None,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            },
            {
                'ticker': pe_ticker,
                'strike': atm_strike,
                'option_type': 'PE',
                'action': 'SELL',
                'entry_time': self.entry_time,
                'entry_price': pe_price,
                'quantity': self.lot_size * num_lots,
                'sl_price': None,
                'target_price': None,
                'exit_time_limit': self.exit_time_limit,
                'leg_group': leg_group,
            }
        ]

        return signals

    def check_exit_conditions(self, positions, trading_times, options_data, entry_time):
        """
        Check combined SL/target for the straddle.
        Uses High for SL check (worst case for shorts) and Low for target check.
        """
        exits = {}

        if not positions or len(positions) < 2:
            return exits

        # Get entry premiums
        ce_leg = None
        pe_leg = None
        for leg in positions:
            if leg['option_type'] == 'CE':
                ce_leg = leg
            elif leg['option_type'] == 'PE':
                pe_leg = leg

        if ce_leg is None or pe_leg is None:
            return exits

        total_entry_premium = ce_leg['entry_price'] + pe_leg['entry_price']
        sl_threshold = total_entry_premium * self.sl_multiplier
        target_threshold = total_entry_premium * self.target_multiplier

        for t in trading_times:
            # Get current prices for SL check (use High — worst case for shorts)
            ce_high = self.get_option_price(options_data, ce_leg['strike'],
                                             'CE', t, 'high')
            pe_high = self.get_option_price(options_data, pe_leg['strike'],
                                             'PE', t, 'high')

            # Get current prices for target check (use Low — best case for shorts)
            ce_low = self.get_option_price(options_data, ce_leg['strike'],
                                            'CE', t, 'low')
            pe_low = self.get_option_price(options_data, pe_leg['strike'],
                                            'PE', t, 'low')

            if ce_high is None or pe_high is None:
                continue

            # Combined SL check
            combined_high = ce_high + pe_high
            if combined_high >= sl_threshold:
                # SL hit — exit both at SL threshold (approximate)
                # Distribute proportionally
                ce_exit = ce_high
                pe_exit = pe_high
                exits[ce_leg['ticker']] = {
                    'exit_price': ce_exit,
                    'exit_time': t,
                    'exit_reason': 'COMBINED_SL'
                }
                exits[pe_leg['ticker']] = {
                    'exit_price': pe_exit,
                    'exit_time': t,
                    'exit_reason': 'COMBINED_SL'
                }
                return exits

            # Combined target check
            if ce_low is not None and pe_low is not None:
                combined_low = ce_low + pe_low
                if combined_low <= target_threshold:
                    ce_exit = ce_low
                    pe_exit = pe_low
                    exits[ce_leg['ticker']] = {
                        'exit_price': ce_exit,
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                    exits[pe_leg['ticker']] = {
                        'exit_price': pe_exit,
                        'exit_time': t,
                        'exit_reason': 'TARGET'
                    }
                    return exits

        return exits
