import os
import pandas as pd
import requests
from datetime import datetime
import time
from pathlib import Path
import numpy as np
import traceback
import json
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the project root directory
PROJECT_ROOT = Path("/Users/md/Dropbox/dev/github/moon-dev-trading-bots")

class HyperLiquidAPI:
    def __init__(self, api_key=None, base_url="https://api.hyperliquid.xyz"):
        """Initialize the API handler"""
        self.base_dir = PROJECT_ROOT / "data" / "hyperliquid"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key or os.getenv('HYPER_LIQUID_KEY')
        self.base_url = base_url
        self.headers = {'X-API-Key': self.api_key} if self.api_key else {}
        self.session = requests.Session()
        self.max_retries = 3
        self.chunk_size = 8192  # Smaller chunk size for more reliable downloads
        
        print("🚀 HyperLiquid API: Ready!")
        print(f"📂 Data directory: {self.base_dir.absolute()}")
        print(f"🌐 API URL: {self.base_url}")
        print(f"🔍 Debug - Project Root: {PROJECT_ROOT}")
        if not self.api_key:
            print("⚠️ No API key found! Please set HYPER_LIQUID_KEY in your .env file")
        else:
            print("🔑 API key loaded successfully!")

    def _fetch_csv(self, filename, limit=None):
        """Fetch CSV data from the API with retry logic"""
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                print(f"🚀 HyperLiquid API: Fetching {filename}... (Attempt {attempt + 1}/{max_retries})")
                
                url = f'{self.base_url}/files/{filename}'
                
                response = self.session.get(url, headers=self.headers, stream=True)
                response.raise_for_status()
                
                temp_file = self.base_dir / f"temp_{filename}"
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192*16):
                        if chunk:
                            f.write(chunk)
                
                df = pd.read_csv(temp_file)
                print(f"✨ Successfully loaded {len(df)} rows from {filename}")
                
                final_file = self.base_dir / filename
                temp_file.rename(final_file)
                
                return df
                
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"💥 Error fetching {filename} after {max_retries} attempts: {str(e)}")
                    print(f"📋 Stack trace:\n{traceback.format_exc()}")
                    return None

    def get_funding_data(self):
        """Get funding data from API"""
        return self._fetch_csv("funding.csv")

    def get_oi_data(self):
        """Get detailed open interest data from API"""
        return self._fetch_csv("oi.csv")

    def get_positions(self):
        """Get detailed positions data"""
        return self._fetch_csv("positions.csv")

    def get_whale_addresses(self):
        """Get list of whale addresses"""
        try:
            print("🐋 HyperLiquid API: Fetching whale addresses...")
            
            url = f'{self.base_url}/files/whale_addresses.txt'
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            save_path = self.base_dir / "whale_addresses.txt"
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            with open(save_path, 'r') as f:
                addresses = f.read().splitlines()
            
            print(f"✨ Successfully loaded {len(addresses)} whale addresses")
            print(f"💾 Data saved to: {save_path}")
            return addresses
                
        except Exception as e:
            print(f"💥 Error fetching whale addresses: {str(e)}")
            return None

if __name__ == "__main__":
    print("🚀 HyperLiquid API Test Suite")
    print("=" * 50)
    
    # Initialize API
    api = HyperLiquidAPI()
    
    # Test Funding Rate Data
    print("\n💰 Testing Funding Data...")
    funding_data = api.get_funding_data()
    if funding_data is not None:
        print(f"✨ Latest Funding Data Preview:\n{funding_data.head()}")
    
    # Test Detailed OI Data
    print("\n📊 Testing Detailed OI Data...")
    oi_data = api.get_oi_data()
    if oi_data is not None:
        print(f"✨ Detailed OI Data Preview:\n{oi_data.head()}")

    # Test Positions Data
    print("\n📊 Testing Positions Data...")
    positions = api.get_positions()
    if positions is not None:
        print(f"✨ Positions Data Preview:\n{positions.head()}")

    # Test Whale Addresses
    print("\n🐋 Testing Whale Addresses...")
    whale_addresses = api.get_whale_addresses()
    if whale_addresses is not None:
        print(f"✨ First few whale addresses:\n{whale_addresses[:5]}")
    
    print("\n✨ HyperLiquid API Test Complete! ✨")
    print("\n💡 Note: Make sure to set HYPER_LIQUID_KEY in your .env file")
