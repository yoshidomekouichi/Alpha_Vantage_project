"""
Alpha Vantage API Client Module

This module handles all interactions with the Alpha Vantage API,
including fetching stock data and handling API errors.
"""

import os
import requests
import logging
from typing import Dict, Optional, Any, Union, List
import time
import random

# Default logger - will be replaced by the configured logger
logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """Client for interacting with the Alpha Vantage API."""
    
    def __init__(self, api_key: str, base_url: str = 'https://www.alphavantage.co/query'):
        """
        Initialize the Alpha Vantage API client.
        
        Args:
            api_key: Alpha Vantage API key
            base_url: Base URL for the Alpha Vantage API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
        
    def set_logger(self, custom_logger):
        """Set a custom logger for the client."""
        global logger
        logger = custom_logger
        
    def fetch_daily_stock_data(self, symbol: str, outputsize: str = 'compact') -> Optional[Dict[str, Any]]:
        """
        Fetch daily stock data for a given symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'NVDA')
            outputsize: 'compact' for latest 100 data points, 'full' for up to 20 years of data
            
        Returns:
            Dictionary containing the stock data or None if an error occurred
        """
        # Check if MOCK_MODE is enabled in environment variables
        self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
        
        if self.mock_mode:
            logger.info(f"🔍 Using mock mode for {symbol}")
            return self._get_mock_data(symbol, outputsize)
            
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": outputsize,
            "datatype": "json"
        }
        
        return self._make_api_request(params)
    
    def _make_api_request(self, params: Dict[str, str], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Make a request to the Alpha Vantage API with exponential backoff retry.
        
        Args:
            params: API request parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response data or None if all retries failed
        """
        retry_count = 0
        while retry_count <= max_retries:
            try:
                logger.debug(f"🛠 Making API request with params: {params}")
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"🛠 API request URL: {response.url}")
                
                # Validate the response format
                if "Time Series (Daily)" not in data:
                    error_msg = f"❌ API specification may have changed: 'Time Series (Daily)' key not found! Response: {data}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Validate a sample data point
                sample_date = next(iter(data["Time Series (Daily)"]))
                sample_data = data["Time Series (Daily)"][sample_date]
                
                expected_keys = {"1. open", "2. high", "3. low", "4. close", "5. volume"}
                actual_keys = set(sample_data.keys())
                
                if actual_keys != expected_keys:
                    error_msg = f"❌ API response format change detected! Expected: {expected_keys}, Actual: {actual_keys}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ API request error (attempt {retry_count+1}/{max_retries+1}): {e}")
            except ValueError as ve:
                logger.error(f"❌ API response validation error: {ve}")
                return None  # Don't retry for validation errors
            except Exception as ex:
                logger.exception(f"❌ Unexpected error during API request: {ex}")
            
            # Exponential backoff with jitter
            if retry_count < max_retries:
                sleep_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.info(f"⏱ Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            
            retry_count += 1
        
        logger.error(f"❌ All {max_retries+1} API request attempts failed")
        return None
    
    def _get_mock_data(self, symbol: str, outputsize: str) -> Dict[str, Any]:
        """
        Generate mock data for testing without making actual API calls.
        
        Args:
            symbol: Stock symbol
            outputsize: 'compact' or 'full'
            
        Returns:
            Mock stock data
        """
        logger.info(f"🔍 Using MOCK data for {symbol} (outputsize: {outputsize})")
        
        # Generate dates (today and previous days)
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # Determine how many days of data to generate
        num_days = 100 if outputsize == 'compact' else 500
        
        # Generate mock time series data
        time_series = {}
        base_price = 100.0  # Starting price
        
        for i in range(num_days):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Generate some price movement
            daily_change = random.uniform(-5, 5)
            open_price = base_price + daily_change
            high_price = open_price * random.uniform(1.0, 1.05)
            low_price = open_price * random.uniform(0.95, 1.0)
            close_price = random.uniform(low_price, high_price)
            volume = int(random.uniform(1000000, 10000000))
            
            # Update base price for next iteration
            base_price = close_price
            
            # Format as API would return
            time_series[date] = {
                "1. open": f"{open_price:.4f}",
                "2. high": f"{high_price:.4f}",
                "3. low": f"{low_price:.4f}",
                "4. close": f"{close_price:.4f}",
                "5. volume": f"{volume}"
            }
        
        # Create the full response structure
        mock_data = {
            "Meta Data": {
                "1. Information": f"Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": symbol,
                "3. Last Refreshed": today.strftime('%Y-%m-%d'),
                "4. Output Size": outputsize,
                "5. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": time_series
        }
        
        return mock_data
