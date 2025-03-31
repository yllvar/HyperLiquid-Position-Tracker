'''
this allows us to see all positions on hyperliquid that are close to liquidation
this information will allow us to enter shorts when other shorts are getting liquidated
but our direction bias is bearish. 
'''

import os 
import json 
import time 
import pandas as pd
import numpy as np 
from datetime import datetime
import colorama
from colorama import Fore, Back, Style
import argparse 
import sys 
import traceback
import random 
from termcolor import colored
import schedule 
from hyperliquid.info import Info
from hyperliquid.utils import constants
from typing import Dict, List, Optional

colorama.init(autoreset=True)
pd.set_option('display.float_format', '{:.2f}'.format)

MIN_POSITION_VALUE = 25000
TOP_N_POSITIONS = 30 
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'XRP', 'SOL']
HIGHLIGHT_THRESHOLD = 2000000

# Initialize HyperLiquid Info client
info = Info(constants.MAINNET_API_URL)

def get_current_price(symbol: str) -> Optional[float]:
    """Get current price using HyperLiquid API"""
    try:
        l2_snapshot = info.l2_snapshot(symbol)
        best_bid = float(l2_snapshot['levels'][0][0]['px'])
        best_ask = float(l2_snapshot['levels'][1][0]['px'])
        return (best_bid + best_ask) / 2
    except Exception as e:
        print(f"{Fore.RED}Error fetching price for {symbol}: {e}")
        return None

def fetch_market_data(symbols: Optional[List[str]] = None) -> Optional[Dict]:
    """Fetch market data from HyperLiquid"""
    try:
        if symbols is None:
            symbols = TOKENS_TO_ANALYZE
        
        market_data = {}
        for symbol in symbols:
            l2_snapshot = info.l2_snapshot(symbol)
            best_bid = float(l2_snapshot['levels'][0][0]['px'])
            best_ask = float(l2_snapshot['levels'][1][0]['px'])
            current_price = (best_bid + best_ask) / 2
            
            # Get 24h stats
            meta = info.meta()
            symbol_info = next((x for x in meta['universe'] if x['name'] == symbol), None)
            
            market_data[symbol] = {
                'price': current_price,
                'ask': best_ask,
                'bid': best_bid,
                'timestamp': int(time.time() * 1000),
                'funding_rate': float(symbol_info['funding']) if symbol_info else 0,
                'open_interest': float(symbol_info['openInterest']) if symbol_info else 0
            }
        return market_data
    except Exception as e:
        print(f"{Fore.RED}Error fetching market data: {e}")
        return None

def fetch_all_positions() -> pd.DataFrame:
    """Fetch all positions from HyperLiquid"""
    try:
        # Get all active positions
        all_positions = info.active_positions()
        
        # Convert to DataFrame
        positions_list = []
        for position in all_positions:
            for coin in position['coins']:
                pos_data = {
                    'address': position['user'],
                    'coin': coin['name'],
                    'position_value': float(coin['positionValue']),
                    'entry_price': float(coin['entryPx']),
                    'leverage': float(coin['leverage']),
                    'liquidation_price': float(coin['liquidationPx']),
                    'unrealized_pnl': float(coin['unrealizedPnl']),
                    'is_long': coin['side'] == 'long'
                }
                positions_list.append(pos_data)
        
        df = pd.DataFrame(positions_list)
        return df
    
    except Exception as e:
        print(f"{Fore.RED}Error fetching positions from HyperLiquid: {e}")
        return pd.DataFrame()

def save_positions_to_memory(df, current_prices=None, quiet=False):
    """Store positions in memory"""
    if df is None or df.empty:
        print(f"{Fore.YELLOW}No positions to save")
        return None, None
    
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    agg_df = df.groupby(['coin', 'is_long']).agg({
        'position_value': 'sum',
        'unrealized_pnl': 'sum',
        'address': 'count',
        'leverage': 'mean',
        'liquidation_price': lambda x: np.nan if all(pd.isna(x)) else np.nanmean(x)
    }).reset_index()

    agg_df['direction'] = agg_df['is_long'].apply(lambda x: 'LONG' if x else 'SHORT')
    agg_df = agg_df.rename(columns={
        'address': 'num_traders',
        'position_value': 'total_value',
        'unrealized_pnl': 'total_pnl',
        'leverage': 'avg_leverage',
        'liquidation_price': 'avg_liquidation_price'
    })

    agg_df['avg_value_per_trader'] = agg_df['total_value'] / agg_df['num_traders']
    agg_df = agg_df.sort_values('total_value', ascending=False)

    if not quiet:
        print(f"\n{Fore.CYAN}{'='*30} POSITION SUMMARY {'='*30}")
        display_cols = ['coin', 'direction', 'total_value', 'num_traders', 'avg_value_per_trader', 'avg_leverage']
        print(agg_df[display_cols].to_string(index=False))

    return df, agg_df

def process_positions(df: pd.DataFrame, coin_filter: Optional[str] = None) -> pd.DataFrame:
    """Process the position data"""
    if df.empty:
        print(f"{Fore.YELLOW}No position data to process")
        return pd.DataFrame()
    
    filtered_df = df[df['position_value'] >= MIN_POSITION_VALUE].copy()

    if coin_filter:
        filtered_df = filtered_df[filtered_df['coin'] == coin_filter.upper()]

    # Update current prices
    market_data = fetch_market_data()
    if market_data:
        filtered_df['current_price'] = filtered_df['coin'].map(lambda x: market_data.get(x, {}).get('price'))

    return filtered_df

def display_top_individual_positions(df: pd.DataFrame, n: int = TOP_N_POSITIONS):
    """Display top positions long and short"""
    if df.empty:
        print(f'{Fore.RED}No positions to display!')
        return None, None 
    
    display_df = df.copy()

    # Sort positions by value
    longs = display_df[display_df['is_long']].sort_values(by='position_value', ascending=False)
    shorts = display_df[~display_df['is_long']].sort_values(by='position_value', ascending=False)

    # Display top n positions
    print(f'\n{Fore.GREEN}{Style.BRIGHT}Top {n} Long Positions:')
    print(f"{Fore.GREEN}{'-'*80}")

    if len(longs) > 0:
        for i, (_, row) in enumerate(longs.head(n).iterrows(), 1):
            position_color = Fore.MAGENTA if row['position_value'] >= HIGHLIGHT_THRESHOLD else Fore.GREEN
            print(
                f"{position_color}#{i} {row['coin']} ${row['position_value']:,.2f} "
                f"| Entry: ${row['entry_price']:,.2f} "
                f"| PnL: {row['unrealized_pnl']:,.2f}% "
                f"| Leverage: {row['leverage']:.2f}x "
                f"| Liq: ${row['liquidation_price']:,.2f}"
            )

    print(f'\n{Fore.RED}{Style.BRIGHT}Top {n} Short Positions:')
    print(f"{Fore.RED}{'-'*80}")

    if len(shorts) > 0:
        for i, (_, row) in enumerate(shorts.head(n).iterrows(), 1):
            position_color = Fore.MAGENTA if row['position_value'] >= HIGHLIGHT_THRESHOLD else Fore.RED
            print(
                f"{position_color}#{i} {row['coin']} ${row['position_value']:,.2f} "
                f"| Entry: ${row['entry_price']:,.2f} "
                f"| PnL: {row['unrealized_pnl']:,.2f}% "
                f"| Leverage: {row['leverage']:.2f}x "
                f"| Liq: ${row['liquidation_price']:,.2f}"
            )

    return longs.head(n), shorts.head(n)

def bot():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description="HyperLiquid Position Tracker")
    parser.add_argument('--min-value', type=int, default=MIN_POSITION_VALUE,
                      help=f'Minimum position value to consider (default: ${MIN_POSITION_VALUE:,})')
    parser.add_argument('--top-n', type=int, default=TOP_N_POSITIONS,
                      help=f'Number of top positions to display (default: {TOP_N_POSITIONS})')
    parser.add_argument('--coin', type=str, default=None,
                      help='Filter positions by coin (e.g., BTC, ETH, SOL)')
    args = parser.parse_args()

    start_time = time.time()

    # Fetch positions directly from HyperLiquid
    positions_df = fetch_all_positions()
    
    if not positions_df.empty:
        processed_df = process_positions(positions_df, args.coin)
        if not processed_df.empty:
            display_top_individual_positions(processed_df, args.top_n)
        else:
            print(f"{Fore.YELLOW}No positions found after processing")
    
    execution_time = time.time() - start_time 
    print(f"\n{Fore.CYAN}🚀 Completed in {execution_time:.2f} seconds")

if __name__ == "__main__":
    schedule.every(1).minutes.do(bot)
    while True:
        schedule.run_pending()
        time.sleep(1)
