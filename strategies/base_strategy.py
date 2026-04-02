"""
Base Strategy Module
====================
Abstract base class for all trading strategies.
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str, capital: float, lot_size: int):
        self.name = name
        self.capital = capital
        self.lot_size = lot_size
        self.trades = []

    @abstractmethod
    def generate_signals(self, date: str, spot_data: pd.DataFrame,
                         options_data: pd.DataFrame, prev_day_spot: float = None) -> list:
        """
        Generate entry signals for a given trading day.

        Args:
            date: Trading date string (YYYY-MM-DD)
            spot_data: Spot price data for this day (all minutes)
            options_data: Options data for this day (all strikes, all minutes)
            prev_day_spot: Previous day's closing spot price (for semi-directional)

        Returns:
            List of dicts, each containing:
            {
                'ticker': str,
                'strike': float,
                'option_type': 'CE' or 'PE',
                'action': 'BUY' or 'SELL',
                'entry_time': str (HH:MM),
                'entry_price': float,
                'quantity': int (positive),
                'sl_price': float or None,
                'target_price': float or None,
                'exit_time_limit': str (HH:MM),
                'leg_group': str (to link legs of same strategy)
            }
        """
        pass

    @abstractmethod
    def check_exit_conditions(self, positions: list, current_time: str,
                               options_data: pd.DataFrame) -> list:
        """
        Check if any exit conditions are met for open positions.

        Args:
            positions: List of open position dicts
            current_time: Current time as 'HH:MM'
            options_data: Full day's options data (to get current prices)

        Returns:
            List of exit dicts, each containing:
            {
                'leg_group': str,
                'exit_price_map': {ticker: exit_price},  # prices per leg
                'exit_time': str,
                'exit_reason': 'SL' | 'TARGET' | 'TIME' | 'COMBINED_SL' | 'SIGNAL'
            }
        """
        pass

    def is_expiry_day(self, date_str):
        """Check if a date is Thursday (weekly expiry day)."""
        from config import EXPIRY_DAY
        return pd.Timestamp(date_str).weekday() == EXPIRY_DAY

    def get_atm_strike(self, spot_price, strike_interval=50):
        """Round spot price to nearest strike interval to get ATM strike."""
        return int(round(spot_price / strike_interval) * strike_interval)

    def get_spot_at_time(self, spot_data, time_str):
        """Get spot close price at a specific time."""
        row = spot_data[spot_data['time'] == time_str]
        if len(row) == 0:
            # Try nearest available time
            all_times = spot_data['time'].unique()
            nearest = min(all_times, key=lambda t: abs(
                pd.Timestamp(f'2000-01-01 {t}') - pd.Timestamp(f'2000-01-01 {time_str}')
            ))
            row = spot_data[spot_data['time'] == nearest]
        if len(row) == 0:
            return None
        return float(row.iloc[0]['spot_close'])

    def get_option_price(self, options_data, strike, option_type, time_str, price_col='close'):
        """Get option price at a specific time."""
        row = options_data[
            (options_data['strike'] == strike) &
            (options_data['option_type'] == option_type) &
            (options_data['time'] == time_str)
        ]
        if len(row) == 0:
            return None
        return float(row.iloc[0][price_col])

    def get_option_bar(self, options_data, strike, option_type, time_str):
        """Get full OHLCV bar for an option at a specific time."""
        row = options_data[
            (options_data['strike'] == strike) &
            (options_data['option_type'] == option_type) &
            (options_data['time'] == time_str)
        ]
        if len(row) == 0:
            return None
        return row.iloc[0].to_dict()
