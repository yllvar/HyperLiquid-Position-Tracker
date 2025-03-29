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
import nice_funcs as n
import argparse 
import sys 
import traceback
import random 
from termcolor import colored
import schedule 

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api import MoonDevAPI

colorama.init(autoreset=True)

pd.set_option('display.float_format', '{:.2f}'.format)

# configuration 
DATA_DIR = '/Users/md/Dropbox/dev/github/short-crypto-to-0-trading-bot/data'
MIN_POSITION_VALUE = 25000
TOP_N_POSITIONS = 30 

# tokens to analyze 
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'XRP', 'SOL']

HIGHLIGHT_THRESHOLD = 2000000

def ensure_data_dir():
    """ensure the data dir exists"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        print(f"Error creating data directory: {e}")
        return False
        
    return True

def display_top_individual_positions(df, n=TOP_N_POSITIONS):
    """displays top poistions long and short"""
    if df is None or df.empty:
        print(f'{Fore.RED}No positions to display!')
        return None, None 
    
    display_df = df.copy()

    valid_liq_df = display_df[display_df['liquidation_price'] > 0].copy()
    if not valid_liq_df.empty:
        valid_liq_df['position_type_verified'] = np.where(
            valid_liq_df['is_long'],
            valid_liq_df['liquidation_price'] > valid_liq_df['entry_price'],
            valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']
        )
        
        inconsistent_positions = valid_liq_df[~valid_liq_df['position_type_verified']]

        if len(inconsistent_positions) > 0:
            print(f'{Fore.YELLOW} Note: some positions have been reclassified based on their liquidation price')

            valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']

            valid_liq_df['is_long'] = valid_liq_df['is_long_corrected']

            display_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long']

    # sort position values 
    longs = display_df[display_df['is_long']].sort_values(by='position_value', ascending=False)
    shorts = display_df[~display_df['is_long']].sort_values(by='position_value', ascending=False)

    # display top n positions 
    print(f'{Fore.GREEN}{Style.BRIGHT}Top {n} Long Positions:')
    print(f"{Fore.GREEN}{'-'*80}")

    if len(longs) > 0:
        for i, (_, row) in enumerate(longs.head(n).iterrows(), 1):
            liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else 'N/A'
            liq_display = f"${liq_price:,.2f}" if liq_price != 'N/A' else "N/A"

            print(f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " +
                  f"{Fore.BLUE} | Entry: ${row['entry_price']:,.2f} " +
                  # do same from PnL, Leverage, Liq, Adderess
                  f"{Fore.MAGENTA}| PnL: {row['unrealized_pnl']:.2f}% " +
                  f"{Fore.CYAN}| Leverage: {row['leverage']:.2f}x " +
                  f"{Fore.RED}| Liq: {liq_display} " +
                  f"{Fore.CYAN}| Address: {row['address']}")

    else:
        print(f"{Fore.GREEN}No long positions to display")

    print(f'\n{Fore.RED}{Style.BRIGHT}Top {n} Short Positions:')
    print(f"{Fore.RED}{'-'*80}")

    if len(shorts) > 0:
        for i, (_, row) in enumerate(shorts.head(n).iterrows(), 1):
            liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else 'N/A'
            liq_display = f"${liq_price:,.2f}" if liq_price != 'N/A' else "N/A"

            print(f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " +
                  f"{Fore.BLUE} | Entry: ${row['entry_price']:,.2f} " +
                  # do same from PnL, Leverage, Liq, Adderess
                  f"{Fore.MAGENTA}| PnL: {row['unrealized_pnl']:.2f}% " +
                  f"{Fore.CYAN}| Leverage: {row['leverage']:.2f}x " +
                  f"{Fore.RED}| Liq: {liq_display} " +
                  f"{Fore.CYAN}| Address: {row['address']}")    

    else:
        print(f"{Fore.YELLOW}No short positions to display")

    return longs.head(n), shorts.head(n)

def display_risk_metrics(df):
    """ display metrics for positions cloases to liquidation"""
    if df is None or df.empty:
        return None, None, None 
    
    risk_df = df.copy()

    risk_df = risk_df[risk_df['liquidation_price'] > 0]

    if risk_df.empty:
        print(f"{Fore.YELLOW}No positions close to liquidation")
        return None, None, None 
    risk_df = risk_df[risk_df['coin'].isin(TOKENS_TO_ANALYZE)]

    unique_coins = risk_df['coin'].unique()
    current_prices = {coin: n.get_current_price(coin) for coin in unique_coins}

    risk_df['current_price'] = risk_df['coin'].map(current_prices)

    # calculate standardisxed distance to liquidation using current price 
    risk_df['distance_to_liq_pct'] = np.where(
        risk_df['is_long'],
        abs((risk_df['current_price'] - risk_df['liquidation_price']) / risk_df['current_price'] * 100),
        abs((risk_df['liquidation_price'] - risk_df['current_price']) / risk_df['current_price'] * 100),
    )

    risk_df['is_long_corrected'] = risk_df['liquidation_price'] < risk_df['entry_price']

    risk_df['is_long'] = risk_df['is_long_corrected']
    
    risk_df = risk_df.sort_values('distance_to_liq_pct')

    # split into longs and shorts 
    risky_longs = risk_df[risk_df['is_long']].sort_values('distance_to_liq_pct')
    risky_shorts = risk_df[~risk_df['is_long']].sort_values('distance_to_liq_pct')

    # display liqs closes to liquidation 
    print(f'{Fore.GREEN}{Style.BRIGHT} TOP {TOP_N_POSITIONS} CLOSE TO LIQUIDATION:')
    print(f"{Fore.GREEN}{'-'*80}")

    if len(risky_longs) > 0:
        running_total_value = 0
        highest_distance = 0 
        last_pct_threshold = 0 

        for i, (_, row) in enumerate(risky_longs.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            running_total_value += row['position_value']
            highest_distance = max(highest_distance, row['distance_to_liq_pct'])
            
            display_text = f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} {Fore.GREEN}${row['position_value']:,.2f} " + \
                           f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " + \
                           f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                           f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            if highlight:
                display_text = colored(f"#{i} {row['coin']} ${row['position_value']:,.2f} " + \
                               f"| Entry: ${row['entry_price']:,.2f} " + \
                               f"| Liq: ${row['liquidation_price']:,.2f} " + \
                               f"| Current: ${row['current_price']:,.2f} " + \
                               f"| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                               f"| Leverage: {row['leverage']}x", 'black', 'on_yellow')
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")

            if i % 10 == 0:
                agg_display = f"📊 AGGREGATE (1-{i}): Total Long Positions: ${running_total_value:,.2f} | All Liquidated Within: {highest_distance:.2f}%"
                print(colored(agg_display, 'black', 'on_cyan'))
                print(f"{Fore.GREEN}{'-'*80}")


            current_pct_threshold = int(row['distance_to_liq_pct'] / 2) * 2 
            if current_pct_threshold > last_pct_threshold:
                pct_agg_display = f'LIQUIDATION THRESHOLD 0-{current_pct_threshold}% Total Long Value: {Fore.GREEN}${running_total_value:,.2f}'
                print(colored(pct_agg_display, 'white', 'on_blue'))
                last_pct_threshold = current_pct_threshold

    else:
        print(f"{Fore.YELLOW}No long positions close to liquidation")

    # display positions closest to liquidation - SHORTS
    print(f"{Fore.RED}{Style.BRIGHT}TOP {TOP_N_POSITIONS} SHORT POSITIONS CLOSE TO LIQUIDATION:")
    print(f"{Fore.RED}{'-'*80}")

    if len(risky_shorts) > 0:
        running_total_value = 0
        highest_distance = 0 
        last_pct_threshold = 0 

        for i, (_, row) in enumerate(risky_shorts.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            running_total_value += row['position_value']
            highest_distance = max(highest_distance, row['distance_to_liq_pct'])

            display_text = f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} {Fore.RED}${row['position_value']:,.2f} " + \
                           f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " + \
                           f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} " + \
                           f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                           f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            if highlight:
                display_text = colored(f"#{i} {row['coin']} ${row['position_value']:,.2f} " + \
                               f"| Entry: ${row['entry_price']:,.2f} " + \
                               f"| Liq: ${row['liquidation_price']:,.2f} " + \
                               f"| Current: ${row['current_price']:,.2f} " + \
                               f"| Distance: {row['distance_to_liq_pct']:.2f}% " + \
                               f"| Leverage: {row['leverage']}x", 'black', 'on_yellow')
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")

            if i % 10 == 0:
                agg_display = f"📊 AGGREGATE (1-{i}): Total Short Positions: ${running_total_value:,.2f} | All Liquidated Within: {highest_distance:.2f}%"
                print(colored(agg_display, 'black', 'on_cyan'))
                print(f"{Fore.RED}{'-'*80}")

            current_pct_threshold = int(row['distance_to_liq_pct'] / 2) * 2 
            if current_pct_threshold > last_pct_threshold:
                pct_agg_display = f'LIQUIDATION THRESHOLD 0-{current_pct_threshold}% Total Short Value: {Fore.RED}${running_total_value:,.2f}'
                print(colored(pct_agg_display, 'white', 'on_blue'))
                last_pct_threshold = current_pct_threshold

    else:
        print(f"{Fore.YELLOW}No short positions close to liquidation")
        
    return risky_longs.head(TOP_N_POSITIONS), risky_shorts.head(TOP_N_POSITIONS), current_prices

def save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df):
    """save liquidation risk data to csv"""
    if risky_longs_df is None and risky_shorts_df is None:
        print(f"{Fore.YELLOW}No liquidation risk data to save")
        return 
    
    if risky_longs_df is not None and not risky_longs_df.empty:
        risky_longs_df = risky_longs_df.copy()
        risky_longs_df['direction'] = 'LONG'

        # save to csv
        longs_file = os.path.join(DATA_DIR, 'liquidation_closest_long_positions.csv')
        risky_longs_df.to_csv(longs_file, index=False, float_format='%.2f')

    # save risky short positions 
    if risky_shorts_df is not None and not risky_shorts_df.empty:
        risky_shorts_df = risky_shorts_df.copy()
        risky_shorts_df['direction'] = 'SHORT'

        # save to csv
        shorts_file = os.path.join(DATA_DIR, 'liquidation_closest_short_positions.csv')
        risky_shorts_df.to_csv(shorts_file, index=False, float_format='%.2f')

    if (risky_longs_df is not None and not risky_longs_df.empty) or (risky_shorts_df is not None and not risky_shorts_df.empty):

        combined_df = pd.concat([risky_longs_df, risky_shorts_df]) if risky_longs_df is not None and risky_shorts_df is not None else (risky_longs_df if risky_longs_df is not None else risky_shorts_df)

        combined_df = combined_df.sort_values('distance_to_liq_pct')

        # dave to csv 
        combined_file = os.path.join(DATA_DIR, 'liquidation_closest_positions.csv')
        combined_df.to_csv(combined_file, index=False, float_format='%.2f')

        print(f"{Fore.GREEN}Liquidation risk data saved to {combined_file}")

        long_count = 0 if risky_longs_df is None else len(risky_longs_df)
        short_count = 0 if risky_shorts_df is None else len(risky_shorts_df)

        print(f"{Fore.GREEN}Total positions saved: {long_count + short_count}")


def save_top_whale_positions_to_csv(longs_df, shorts_df):
    """save top whale positions to csv"""
    if longs_df is None and shorts_df is None:
        print(f"{Fore.YELLOW}No whale positions to save")
        return 
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if longs_df is not None and not longs_df.empty:
        longs_df = longs_df.copy()
        longs_df['direction'] = 'LONG'

        # save to csv
        longs_file = os.path.join(DATA_DIR, f'top_whale_long_positions.csv')
        longs_df.to_csv(longs_file, index=False, float_format='%.2f')

    if shorts_df is not None and not shorts_df.empty:
        shorts_df = shorts_df.copy()
        shorts_df['direction'] = 'SHORT'

        # save to csv
        shorts_file = os.path.join(DATA_DIR, f'top_whale_short_positions.csv')
        shorts_df.to_csv(shorts_file, index=False, float_format='%.2f')

    if (longs_df is not None and not longs_df.empty) or (shorts_df is not None and not shorts_df.empty):
        combined_df = pd.concat([longs_df, shorts_df]) if longs_df is not None and shorts_df is not None else (longs_df if longs_df is not None else shorts_df)

        combined_df = combined_df.sort_values('position_value', ascending=False)

        # save to csv
        combined_file = os.path.join(DATA_DIR, f'top_whale_positions.csv')
        combined_df.to_csv(combined_file, index=False, float_format='%.2f')
        print(f'{Fore.GREEN}Top whale positions saved to {combined_file}')

def process_positions(df, coin_filter=None):
    """ process the position data into a mor eusable format fiiltering positions below min value and optionolyy by coin"""
    if df is None or df.empty:
        print(f"{Fore.YELLOW}No position data to process")
        return None 
    
    filtered_df = df[df['position_value'] >= MIN_POSITION_VALUE].copy()

    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price']

    for col in numeric_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce')

    if 'is_long' in filtered_df.columns and filtered_df['is_long'].dtype != bool:
        filtered_df['is_long'] = filtered_df['is_long'].map({'True': True, 'False': False})

    # validate postion types for positions with valid liq prices
    valid_liq_df = filtered_df[filtered_df['liquidation_price'] > 0].copy()
    if not valid_liq_df.empty:
        valid_liq_df['position_type_verified'] = np.where(
            valid_liq_df['is_long'],
            valid_liq_df['liquidation_price'] < valid_liq_df['entry_price'],
            valid_liq_df['liquidation_price'] > valid_liq_df['entry_price']
        )

        inconsistent_positions = valid_liq_df[~valid_liq_df['position_type_verified']]

        if len(inconsistent_positions) > 0:
            print(f"{Fore.YELLOW}Note: some positions have been reclassified based on their liquidation price")

            valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']

            valid_liq_df['is_long'] = valid_liq_df['is_long_corrected']

            filtered_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long']

            print(f"{Fore.YELLOW}Reclassified {len(inconsistent_positions)} positions")

        if coin_filter:
            coin_filter = coin_filter.upper()
            filtered_df = filtered_df[filtered_df['coin'] == coin_filter]
            print(f"{Fore.YELLOW}Filtered to {coin_filter} positions")

        print(f"{Fore.YELLOW}Total positions after filtering: {len(filtered_df)}")

        return filtered_df
    
def save_positions_to_csv(df, current_prices=None, quiet=False):
    if df is None or df.empty:
        print(f"{Fore.YELLOW}No positions to save")
        return 
    
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    positions_file = os.path.join(DATA_DIR, f'all_positions.csv')
    df.to_csv(positions_file, index=False, float_format='%.2f')

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

    agg_file = os.path.join(DATA_DIR, f'aggregated_positions.csv')
    agg_df.to_csv(agg_file, index=False, float_format='%.2f')

    print(f"\n{Fore.CYAN}{'='*30} POSITION SUMMARY {'='*30}")
    display_cols = ['coin', 'direction', 'total_value', 'num_traders', 'avg_value_per_trader', 'avg_leverage']

    with pd.option_context('display.float_format', '{:.2f}'.format):
        print(f'{Fore.WHITE}{agg_df[display_cols]}')

        print(f"\n{Fore.GREEN}🔝 TOP LONG POSITIONS (AGGREGATED):")
        print(f"{Fore.GREEN}{agg_df[agg_df['is_long']][display_cols].head()}")
        
        print(f"\n{Fore.RED}🔝 TOP SHORT POSITIONS (AGGREGATED):")
        print(f"{Fore.RED}{agg_df[~agg_df['is_long']][display_cols].head()}")

    longs_df, shorts_df = display_top_individual_positions(df)

    save_top_whale_positions_to_csv(longs_df, shorts_df)

    risky_longs_df, risky_shorts_df, fetched_price = display_risk_metrics(df)

    save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df)

    if current_prices is None:
        unique_coins = df[df['coin'].isin(TOKENS_TO_ANALYZE)]['coin'].unique()
        current_prices = {coin: n.get_current_price(coin) for coin in unique_coins}

    # use current prices for liquidation impact analysrs
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*20} 💥 LIQUIDATION IMPACT FOR 3% PRICE MOVE 💥 {'='*20}")
    print(f"{Fore.CYAN}{'='*80}")

    total_long_liquidations = {}
    total_short_liquidations = {}
    all_long_liquidations = 0 
    all_short_liquidations = 0 

    for coin in TOKENS_TO_ANALYZE:
        if coin not in current_prices:
            continue 

        coin_positions = df[df['coin'] == coin].copy()
        if coin_positions.empty:
            continue 

        current_price = current_prices[coin]
        coin_positions['current_price'] = current_price

        price_3pct_down = current_price * 0.97 
        price_3pct_up = current_price * 1.03 

        long_liquidations = coin_positions[(coin_positions['is_long']) & 
                                          (coin_positions['liquidation_price'] >= price_3pct_down)&
                                          (coin_positions['liquidation_price'] <= current_price)]
        
        total_long_liquidation_value = long_liquidations['position_value'].sum()

        short_liquidations = coin_positions[(~coin_positions['is_long']) & 
                                          (coin_positions['liquidation_price'] <= price_3pct_up) & 
                                          (coin_positions['liquidation_price'] >= current_price)]
        
        total_short_liquidation_value = short_liquidations['position_value'].sum()
        
        total_long_liquidations[coin] = total_long_liquidation_value
        total_short_liquidations[coin] = total_short_liquidation_value

        all_long_liquidations += total_long_liquidation_value
        all_short_liquidations += total_short_liquidation_value
        
        if not quiet:
            print(f"{Fore.GREEN}{coin} Long Liquidations (3% move DOWN to ${price_3pct_down:,.2f}): ${total_long_liquidation_value:,.2f}")
            print(f"{Fore.RED}{coin} Short Liquidations (3% move UP to ${price_3pct_up:,.2f}): ${total_short_liquidation_value:,.2f}")

    # Display summary of total liquidations
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*25} 💰 TOTAL LIQUIDATION SUMMARY 💰 {'='*25}")
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.GREEN}Total Long Liquidations (3% move DOWN): ${all_long_liquidations:,.2f}")
    print(f"{Fore.RED}Total Short Liquidations (3% move UP): ${all_short_liquidations:,.2f}")
    
    # Generate trading recommendations based on liquidation imbalance
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*20} 🚀 MARKET DIRECTION (NFA) 🚀 {'='*20}")
    print(f"{Fore.CYAN}{'='*80}")
    
    # Overall market direction
    if all_long_liquidations > all_short_liquidations:
        direction = f"MARKET DIRECTION (NFA): SHORT THE MARKET (${all_long_liquidations:,.2f} long liquidations at risk within a 3% move of current price)"
        print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{direction}{Style.RESET_ALL}")
    else:
        direction = f"MARKET DIRECTION (NFA): LONG THE MARKET (${all_short_liquidations:,.2f} short liquidations at risk within a 3% move of current price)"
        print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{direction}{Style.RESET_ALL}")
    
    # Individual coin directions
    print(f"\n{Fore.CYAN}{'='*30} INDIVIDUAL COIN DIRECTION (NFA) {'='*30}")
    
    liquidation_imbalance = {}
    for coin in total_long_liquidations.keys():
        if coin in total_short_liquidations:
            liquidation_imbalance[coin] = abs(total_long_liquidations[coin] - total_short_liquidations[coin])

    sorted_coins = sorted(liquidation_imbalance.keys(), key=lambda x: liquidation_imbalance[x], reverse=True)

    for coin in sorted_coins:
        long_liq = total_long_liquidations[coin]
        short_liq = total_short_liquidations[coin]
        
        if long_liq < 100000 and short_liq < 100000:
            continue 

        if long_liq > short_liq:
            rec = f"{coin}: SHORT (${long_liq:,.2f} long liquidations vs ${short_liq:,.2f} short within a 3% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{rec}{Style.RESET_ALL}")
        else:
            rec = f"{coin}: LONG (${short_liq:,.2f} short liquidations vs ${long_liq:,.2f} long within a 3% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}{rec}{Style.RESET_ALL}")
    
    print(f"\n{Fore.MAGENTA}💡 Trading strategy: Target coins with largest liquidation imbalance for potential cascade liquidations")
    print(f"{Fore.YELLOW}⚠️ NFA: This analysis is NOT financial advice. Always do your own research! 📚")
    

    create_liquidation_thresholds_table(df, current_prices, quiet)

    long_count = len(longs_df) if longs_df is not None else 0 
    short_count = len(shorts_df) if shorts_df is not None else 0 

    return df, agg_df

def create_liquidation_thresholds_table(df, current_prices, quiet=False):
    """ create and display a table of liquidation thresholds at different price move percentages"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*15} 📊 LIQUIDATION THRESHOLDS BY PERCENTAGE MOVE 📊 {'='*15}")
    print(f"{Fore.CYAN}{'='*80}")

    thresholds = [2, 4, 6, 8, 10]

    table_data = {
        'Threshold': [f'0-{t}%' for t in thresholds],
        'Long Liquidations ($)': [],
        'Short Liquidations ($)': [],
        'Total Liquidations ($)': [],
        'Net Imbalance ($)': [],
        'NFA': []
    }

    for threshold in thresholds:
        total_long_liquidations = 0 
        total_short_liquidations = 0 

        for coin in TOKENS_TO_ANALYZE:
            if coin not in current_prices:
                continue 
            
            coin_positions = df[df['coin'] == coin].copy()
            if coin_positions.empty:
                continue 

            current_price = current_prices[coin]
            price_down = current_price * (1 - threshold / 100)
            price_up = current_price * (1 + threshold / 100)

            long_liquidations = coin_positions[(coin_positions['is_long']) & 
                                              (coin_positions['liquidation_price'] >= price_down) & 
                                              (coin_positions['liquidation_price'] <= current_price)]
            long_value = long_liquidations['position_value'].sum()

            short_liquidations = coin_positions[(~coin_positions['is_long']) & 
                                                (coin_positions['liquidation_price'] <= price_up) & 
                                                (coin_positions['liquidation_price'] >= current_price)]
            short_value = short_liquidations['position_value'].sum()

            total_long_liquidations += long_value
            total_short_liquidations += short_value
            

        total_liquidations = total_long_liquidations + total_short_liquidations
        imbalance = total_long_liquidations - total_short_liquidations

        if abs(imbalance) < 100000:
            direction = "NEUTRAL"
        elif imbalance > 0:
            direction = "SHORT"
        else:
            direction = "LONG"

        table_data['Long Liquidations ($)'].append(total_long_liquidations)
        table_data['Short Liquidations ($)'].append(total_short_liquidations)
        table_data['Total Liquidations ($)'].append(total_liquidations)
        table_data['Net Imbalance ($)'].append(imbalance)
        table_data['NFA'].append(direction)

    table_df = pd.DataFrame(table_data)
    
    for col in ['Long Liquidations ($)', 'Short Liquidations ($)', 'Total Liquidations ($)', 'Net Imbalance ($)']:
        table_df[col] = table_df[col].apply(lambda x: f"{x:,.2f}")

    styled_table = f"\n{Fore.CYAN}{'='*120}\n"
    styled_table += f"{Fore.YELLOW}{'Threshold':<12} | {'Long Liquidations':<25} | {'Short Liquidations':<25} | {'Total Liquidations':<25} | {'Net Imbalance':<25} | {'NFA':<15}\n"  # Changed 'Recommendation' to 'NFA'
    styled_table += f"{Fore.CYAN}{'-'*120}\n"

    for i, row in table_df.iterrows():
        direction = row['NFA']
        direction_color = Fore.GREEN if direction == 'LONG' else Fore.RED if direction == 'SHORT' else Fore.YELLOW
        styled_table += f"{Fore.WHITE}{row['Threshold']:<12} | "
        styled_table += f"{Fore.GREEN}{row['Long Liquidations ($)']:<25} | "
        styled_table += f"{Fore.RED}{row['Short Liquidations ($)']:<25} | "
        styled_table += f"{Fore.CYAN}{row['Total Liquidations ($)']:<25} | "
        styled_table += f"{Fore.MAGENTA}{row['Net Imbalance ($)']:<25} | "
        styled_table += f"{direction_color}{direction:<15}\n"
        
    styled_table += f"{Fore.CYAN}{'='*120}"
    print(styled_table)

    table_file = os.path.join(DATA_DIR, 'liquidation_thresholds_table.csv')
    table_df.to_csv(table_file, index=False)
        
def fetch_positions_from_api():
    """feth positions from moon dev api """
    try:
        print(f"{Fore.CYAN} Moon Dev API Fetching Hyperliquid Positions...")

        api = MoonDevAPI()

        positions_df = api.get_positions_hlp()

        if positions_df is None or positions_df.empty:
            print(f"{Fore.YELLOW}No positions found in Moon Dev API")
            return None 
        
        print(f"{Fore.GREEN}Successfully fetched {len(positions_df)} positions from Moon Dev API")

        return positions_df
    
    except Exception as e:
        print(f"{Fore.RED}Error fetching positions from Moon Dev API: {e}")
        return None 
    
def fetch_aggregated_positions_from_api():
    """fetch aggregated positions from moon dev api"""

    try:
        print(f"{Fore.CYAN} Moon Dev API Fetching Aggregated Positions...")

        api = MoonDevAPI()

        agg_positions_df = api.get_agg_positions_hlp()

        if agg_positions_df is None or agg_positions_df.empty:
            print(f"{Fore.YELLOW}No aggregated positions found in Moon Dev API")
            return None 
        
        print(f"{Fore.GREEN}Successfully fetched {len(agg_positions_df)} aggregated positions from Moon Dev API")

        return agg_positions_df

    except Exception as e:
        print(f"{Fore.RED}Error fetching aggregated positions from Moon Dev API: {e}")
        return None 
    
def bot():
    """main function to run the script"""

    global MIN_POSITION_VALUE, TOP_N_POSITIONS 

    parser = argparse.ArgumentParser(description="🌙 Moon Dev's Hyperliquid Whale Position Tracker (API Version)")
    parser.add_argument('--min-value', type=int, default=MIN_POSITION_VALUE, 
                        help=f'Minimum position value to consider (default: ${MIN_POSITION_VALUE:,})')
    parser.add_argument('--top-n', type=int, default=TOP_N_POSITIONS,
                        help=f'Number of top positions to display (default: {TOP_N_POSITIONS})')
    parser.add_argument('--agg-only', action='store_true',
                        help='Only show aggregated data (faster, less detailed)')
    parser.add_argument('--coin', type=str, default=None,
                        help='Filter positions by coin (e.g., BTC, ETH, SOL)')
    parser.add_argument('--verify-positions', action='store_true', default=True,
                        help='Verify and correct position types based on liquidation prices')
    parser.add_argument('--quiet', action='store_true', default=False,
                        help='Reduce verbosity of output')
    parser.add_argument('--no-symbol-debug', action='store_true', default=True,
                        help='Disable printing of individual symbols during analysis')
    args = parser.parse_args()
    
    MIN_POSITION_VALUE = args.min_value 
    TOP_N_POSITIONS = args.top_n 
    start_time = time.time()

    ensure_data_dir()

    agg_df = fetch_aggregated_positions_from_api()

    if agg_df is not None:
        agg_file = os.path.join(DATA_DIR, 'aggregated_positions_from_api.csv')
        agg_df.to_csv(agg_file, index=False, float_format='%.2f')

        agg_df['direction'] = agg_df['is_long'].apply(lambda x: 'LONG' if x else 'SHORT')

        if args.coin:
            coin = args.coin.upper()
            agg_df = agg_df[agg_df['coin'] == coin]

        if not args.quiet:
            print(f"\n{Fore.CYAN}{'='*80}")
            print(f"{Fore.CYAN}{'='*20} 🐳 AGGREGATED POSITIONS {'='*20}")
            print(f"{Fore.CYAN}{'='*80}")
            display_cols = ['coin', 'direction', 'total_value', 'num_traders', 'liquidation_price']

        with pd.option_context('display.float_format', '{:,.2f}'.format):
            print(f"{Fore.WHITE}{agg_df[display_cols]}")
                
            print(f"\n{Fore.GREEN}🔝 TOP LONG POSITIONS (AGGREGATED):")
            print(f"{Fore.GREEN}{agg_df[agg_df['is_long']][display_cols].head()}")
            
            print(f"\n{Fore.RED}🔝 TOP SHORT POSITIONS (AGGREGATED):")
            print(f"{Fore.RED}{agg_df[~agg_df['is_long']][display_cols].head()}")

        if not args.agg_only:
            positions_df = fetch_positions_from_api()

            if positions_df is not None:
                processed_df = process_positions(positions_df, args.coin)

                if not processed_df.empty:
                    longs_df, shorts_df = display_top_individual_positions(processed_df)

                    save_top_whale_positions_to_csv(longs_df, shorts_df)

                    risky_longs_df, risky_shorts_df, current_prices = display_risk_metrics(processed_df)

                    save_liquidation_risk_to_csv(risky_longs_df, risky_shorts_df)

                    positions_df, _ = save_positions_to_csv(processed_df, current_prices, quiet=args.quiet)

                else:
                    print(f"{Fore.YELLOW}No positions found in Moon Dev API")

    execution_time = time.time() - start_time 
    print(f"\n{Fore.CYAN}🚀 Completed in {execution_time:.2f} seconds")

if __name__ == "__main__":
    bot()
    schedule.every(1).minutes.do(bot)

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}Error in scheduler: {e}")
            time.sleep(10)
                    
            

    
    