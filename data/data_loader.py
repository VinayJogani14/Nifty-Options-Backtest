"""
Data Loader Module (v3 - Fully Optimized)
==========================================
Processes raw CSV data folder-by-folder, derives spot per folder,
and saves lightweight parquet files. No massive concat needed.
"""

import os
import re
import pandas as pd
import numpy as np
from tqdm import tqdm
import gc
from config import (INSAMPLE_START, INSAMPLE_END, OOS_START, OOS_END,
                    MARKET_OPEN, MARKET_CLOSE, STRIKE_INTERVAL)

EXTENDED_OOS_END = "2026-03-31"


def parse_filename(filename):
    """Parse: NIFTY_{STRIKE}_{CE|PE}_{DD}_{MON}_{YY}.csv"""
    pattern = r'NIFTY_(\d+)_(CE|PE)_(\d{2})_([A-Z]{3})_(\d{2})\.csv'
    match = re.match(pattern, filename)
    if not match:
        return None
    strike = int(match.group(1))
    option_type = match.group(2)
    expiry_str = f"{match.group(3)}_{match.group(4)}_{match.group(5)}"
    ticker = f"NIFTY_{strike}_{option_type}_{expiry_str}"
    return strike, option_type, expiry_str, ticker


def load_folder(folder_path, folder_name):
    """Load all CSVs in a single expiry folder."""
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    dfs = []

    for csv_file in csv_files:
        parsed = parse_filename(csv_file)
        if parsed is None:
            continue
        strike, option_type, expiry_str, ticker = parsed

        try:
            df = pd.read_csv(os.path.join(folder_path, csv_file))
            if len(df) == 0:
                continue
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
            df['time'] = df['timestamp'].dt.strftime('%H:%M')
            df = df[(df['time'] >= MARKET_OPEN) & (df['time'] <= '15:29')].copy()
            if len(df) == 0:
                continue
            df['ticker'] = ticker
            df['strike'] = np.int32(strike)
            df['option_type'] = option_type
            df['expiry'] = expiry_str
            df['expiry_folder'] = folder_name
            df = df[['date', 'time', 'ticker', 'strike', 'option_type', 'expiry',
                      'expiry_folder', 'open', 'high', 'low', 'close', 'volume', 'oi']].copy()
            dfs.append(df)
        except Exception:
            continue

    if not dfs:
        return None

    combined = pd.concat(dfs, ignore_index=True)
    combined['strike'] = combined['strike'].astype('int32')
    combined['option_type'] = combined['option_type'].astype('category')
    for col in ['open', 'high', 'low', 'close']:
        combined[col] = combined[col].astype('float32')
    combined['volume'] = combined['volume'].astype('int32')
    combined['oi'] = combined['oi'].astype('int32')
    return combined


def derive_spot_from_folder(folder_df):
    """Derive spot price from a single folder's data. Much faster than global approach."""
    ce = folder_df[folder_df['option_type'] == 'CE'][['date', 'time', 'strike', 'close']].copy()
    pe = folder_df[folder_df['option_type'] == 'PE'][['date', 'time', 'strike', 'close']].copy()
    ce.rename(columns={'close': 'ce_close'}, inplace=True)
    pe.rename(columns={'close': 'pe_close'}, inplace=True)

    merged = ce.merge(pe, on=['date', 'time', 'strike'], how='inner')
    if len(merged) == 0:
        return pd.DataFrame()

    merged['prem_diff'] = (merged['ce_close'] - merged['pe_close']).abs()

    # For each (date, time), find ATM
    atm_idx = merged.groupby(['date', 'time'])['prem_diff'].idxmin()
    atm = merged.loc[atm_idx].copy()
    atm['spot_close'] = atm['strike'].astype(float) + atm['ce_close'] - atm['pe_close']

    return atm[['date', 'time', 'spot_close']].reset_index(drop=True)


def load_and_process_data(raw_dir='data/raw', processed_dir='data/processed'):
    """Load, process, derive spot, and save efficiently."""
    os.makedirs(processed_dir, exist_ok=True)

    # Check cache
    if all(os.path.exists(os.path.join(processed_dir, f)) for f in [
        'nifty_options_insample.parquet', 'nifty_options_oos.parquet',
        'nifty_spot_insample.parquet', 'nifty_spot_oos.parquet',
        'expiry_map.parquet'
    ]):
        print("Processed files already exist. Loading from cache...")
        return load_processed_data(processed_dir)

    all_folders = sorted([d for d in os.listdir(raw_dir)
                          if os.path.isdir(os.path.join(raw_dir, d))])

    print(f"Processing {len(all_folders)} expiry folders...")

    insample_opts_parts = []
    oos_opts_parts = []
    spot_parts = []
    expiry_dates_map = {}  # date -> nearest expiry folder

    for folder_name in tqdm(all_folders, desc="Processing folders"):
        folder_path = os.path.join(raw_dir, folder_name)
        folder_df = load_folder(folder_path, folder_name)
        if folder_df is None:
            continue

        # Filter to target date range
        folder_df = folder_df[folder_df['date'] >= INSAMPLE_START].copy()
        if len(folder_df) == 0:
            continue

        # Derive spot from this folder's data
        folder_spot = derive_spot_from_folder(folder_df)
        if len(folder_spot) > 0:
            folder_spot['expiry_folder'] = folder_name
            spot_parts.append(folder_spot)

        # Build expiry map: for each date in this folder, check if this is the nearest expiry
        try:
            folder_expiry_date = pd.Timestamp(folder_name)
        except:
            continue

        for d in folder_df['date'].unique():
            trade_date = pd.Timestamp(d)
            dte = (folder_expiry_date - trade_date).days
            if dte >= 0:
                if d not in expiry_dates_map or dte < expiry_dates_map[d][1]:
                    expiry_dates_map[d] = (folder_name, dte)

        # Split data
        is_mask = (folder_df['date'] >= INSAMPLE_START) & (folder_df['date'] <= INSAMPLE_END)
        oos_mask = (folder_df['date'] >= OOS_START) & (folder_df['date'] <= EXTENDED_OOS_END)

        if is_mask.any():
            insample_opts_parts.append(folder_df[is_mask].copy())
        if oos_mask.any():
            oos_opts_parts.append(folder_df[oos_mask].copy())

        del folder_df
        gc.collect()

    # Combine options
    print("Combining data...")
    insample_opts = pd.concat(insample_opts_parts, ignore_index=True) if insample_opts_parts else pd.DataFrame()
    del insample_opts_parts
    gc.collect()

    oos_opts = pd.concat(oos_opts_parts, ignore_index=True) if oos_opts_parts else pd.DataFrame()
    del oos_opts_parts
    gc.collect()

    # Sort
    for df in [insample_opts, oos_opts]:
        if len(df) > 0:
            df.sort_values(['date', 'time', 'strike', 'option_type'], inplace=True)
            df.reset_index(drop=True, inplace=True)

    # Combine spot - pick the nearest expiry's spot for each (date, time)
    print("Processing spot data...")
    all_spot = pd.concat(spot_parts, ignore_index=True) if spot_parts else pd.DataFrame()
    del spot_parts
    gc.collect()

    if len(all_spot) > 0:
        # For each (date, time), keep spot from nearest expiry
        all_spot['expiry_date'] = pd.to_datetime(all_spot['expiry_folder'], errors='coerce')
        all_spot['trade_date'] = pd.to_datetime(all_spot['date'])
        all_spot['dte'] = (all_spot['expiry_date'] - all_spot['trade_date']).dt.days
        all_spot = all_spot[all_spot['dte'] >= 0].copy()

        # Keep nearest expiry per (date, time)
        nearest_idx = all_spot.groupby(['date', 'time'])['dte'].idxmin()
        spot = all_spot.loc[nearest_idx][['date', 'time', 'spot_close']].reset_index(drop=True)
        spot['spot_close'] = spot['spot_close'].astype('float32')
    else:
        spot = pd.DataFrame(columns=['date', 'time', 'spot_close'])

    del all_spot
    gc.collect()

    # Split spot
    insample_spot = spot[(spot['date'] >= INSAMPLE_START) & (spot['date'] <= INSAMPLE_END)].copy()
    oos_spot = spot[(spot['date'] >= OOS_START) & (spot['date'] <= EXTENDED_OOS_END)].copy()

    # Build expiry map DataFrame
    expiry_map = pd.DataFrame([
        {'date': d, 'nearest_expiry': v[0]} for d, v in expiry_dates_map.items()
    ])
    expiry_map.sort_values('date', inplace=True)
    expiry_map.reset_index(drop=True, inplace=True)

    # Save
    print("Saving processed data...")
    insample_opts.to_parquet(os.path.join(processed_dir, 'nifty_options_insample.parquet'), index=False)
    oos_opts.to_parquet(os.path.join(processed_dir, 'nifty_options_oos.parquet'), index=False)
    insample_spot.to_parquet(os.path.join(processed_dir, 'nifty_spot_insample.parquet'), index=False)
    oos_spot.to_parquet(os.path.join(processed_dir, 'nifty_spot_oos.parquet'), index=False)
    expiry_map.to_parquet(os.path.join(processed_dir, 'expiry_map.parquet'), index=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"In-sample: {len(insample_opts):,} rows, {insample_opts['date'].nunique()} trading days, "
          f"{insample_opts['strike'].nunique()} unique strikes")
    if len(insample_opts) > 0:
        print(f"  Date range: {insample_opts['date'].min()} to {insample_opts['date'].max()}")
    print(f"Out-of-sample: {len(oos_opts):,} rows, {oos_opts['date'].nunique()} trading days, "
          f"{oos_opts['strike'].nunique()} unique strikes")
    if len(oos_opts) > 0:
        print(f"  Date range: {oos_opts['date'].min()} to {oos_opts['date'].max()}")
    if len(insample_spot) > 0:
        print(f"Spot IS: {len(insample_spot):,} rows, range "
              f"{insample_spot['spot_close'].min():.0f}-{insample_spot['spot_close'].max():.0f}")
    if len(oos_spot) > 0:
        print(f"Spot OOS: {len(oos_spot):,} rows, range "
              f"{oos_spot['spot_close'].min():.0f}-{oos_spot['spot_close'].max():.0f}")

    for name, df in [('IS options', insample_opts), ('OOS options', oos_opts)]:
        if len(df) > 0:
            nulls = df[['open', 'high', 'low', 'close']].isnull().sum().sum()
            print(f"{name} null OHLC count: {nulls}")
    print(f"{'='*60}")

    return {
        'insample_opts': insample_opts,
        'oos_opts': oos_opts,
        'insample_spot': insample_spot,
        'oos_spot': oos_spot,
        'expiry_map': expiry_map
    }


def load_processed_data(processed_dir='data/processed'):
    """Load preprocessed parquet files."""
    files = {
        'insample_opts': 'nifty_options_insample.parquet',
        'oos_opts': 'nifty_options_oos.parquet',
        'insample_spot': 'nifty_spot_insample.parquet',
        'oos_spot': 'nifty_spot_oos.parquet',
        'expiry_map': 'expiry_map.parquet'
    }

    data = {}
    for key, fname in files.items():
        path = os.path.join(processed_dir, fname)
        if not os.path.exists(path):
            return None
        data[key] = pd.read_parquet(path)
        print(f"Loaded {key}: {len(data[key]):,} rows")
    return data


if __name__ == '__main__':
    print("="*60)
    print("  NIFTY OPTIONS DATA PROCESSING PIPELINE")
    print("="*60)
    data = load_and_process_data()
    print("\nData processing complete!")
