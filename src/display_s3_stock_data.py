#!/usr/bin/env python3
"""
Display S3 Stock Data

This script retrieves stock data from S3 and displays it.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config
from src.utils.storage import S3Storage
from src.utils.logging_utils import LoggerManager

def main():
    """Main function."""
    # Load configuration
    config = Config()
    
    # Set environment variables for mock mode and S3 saving
    os.environ['MOCK_MODE'] = 'True'
    os.environ['SAVE_TO_S3'] = 'True'
    
    # Set up logger
    logger_manager = LoggerManager(
        "display_s3_stock_data",
        log_dir=config.log_dir,
        console_level="INFO",
        file_level="DEBUG",
        is_mock=True
    )
    logger = logger_manager.get_logger()
    
    # Set up S3 storage
    s3_storage = S3Storage(config.s3_bucket, config.s3_region)
    s3_storage.set_logger(logger)
    
    # Get stock symbols from config
    symbols = config.stock_symbols
    
    logger.info(f"Retrieving stock data for symbols: {symbols}")
    
    for symbol in symbols:
        logger.info(f"=== Data for {symbol} ===")
        
        # Get S3 keys
        latest_key = config.get_s3_key(symbol, is_latest=True)
        full_key = config.get_s3_key(symbol)
        metadata_key = config.get_metadata_key(symbol)
        
        # Get today's date and yesterday's date
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Daily keys for today and yesterday
        daily_key_today = config.get_s3_key(symbol, date=today)
        daily_key_yesterday = config.get_s3_key(symbol, date=yesterday)
        
        # Load latest data
        logger.info(f"Loading latest data from {latest_key}")
        latest_data = s3_storage.load_json(latest_key)
        if latest_data:
            logger.info(f"Latest data: {json.dumps(latest_data, indent=2)}")
            
            # Extract and display stock price information
            if 'data' in latest_data and len(latest_data['data']) > 0:
                latest_price = latest_data['data'][0]
                logger.info(f"Latest price for {symbol}:")
                logger.info(f"  Date: {latest_price.get('date')}")
                logger.info(f"  Open: {latest_price.get('open')}")
                logger.info(f"  High: {latest_price.get('high')}")
                logger.info(f"  Low: {latest_price.get('low')}")
                logger.info(f"  Close: {latest_price.get('close')}")
                logger.info(f"  Volume: {latest_price.get('volume')}")
        else:
            logger.warning(f"No latest data found for {symbol}")
        
        # Load metadata
        logger.info(f"Loading metadata from {metadata_key}")
        metadata = s3_storage.load_json(metadata_key)
        if metadata:
            logger.info(f"Metadata: {json.dumps(metadata, indent=2)}")
            
            # Extract and display metadata information
            logger.info(f"Metadata for {symbol}:")
            logger.info(f"  Last updated: {metadata.get('last_updated')}")
            logger.info(f"  Latest date: {metadata.get('latest_date')}")
            logger.info(f"  Data points: {metadata.get('data_points')}")
            
            date_range = metadata.get('date_range', {})
            logger.info(f"  Date range: {date_range.get('start')} to {date_range.get('end')}")
        else:
            logger.warning(f"No metadata found for {symbol}")
        
        # Load daily data for today
        logger.info(f"Loading daily data for today from {daily_key_today}")
        daily_data_today = s3_storage.load_json(daily_key_today)
        if daily_data_today:
            logger.info(f"Daily data for today: {json.dumps(daily_data_today, indent=2)}")
        else:
            logger.warning(f"No daily data found for {symbol} for today")
        
        # Load daily data for yesterday
        logger.info(f"Loading daily data for yesterday from {daily_key_yesterday}")
        daily_data_yesterday = s3_storage.load_json(daily_key_yesterday)
        if daily_data_yesterday:
            logger.info(f"Daily data for yesterday: {json.dumps(daily_data_yesterday, indent=2)}")
        else:
            logger.warning(f"No daily data found for {symbol} for yesterday")
        
        # List all daily data files
        daily_prefix = f"{config.s3_prefix}/{symbol}/daily/"
        logger.info(f"Listing all daily data files with prefix {daily_prefix}")
        daily_files = s3_storage.list_objects(daily_prefix)
        
        logger.info(f"Found {len(daily_files)} daily data files:")
        for file in daily_files:
            logger.info(f"  - {file}")
        
        logger.info("=" * 50)

if __name__ == "__main__":
    main()