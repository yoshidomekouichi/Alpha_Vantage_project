#!/usr/bin/env python3
"""
S3 Data Checker

This script checks the data stored in S3 for a given stock symbol.
"""

import os
import sys
import json
from pathlib import Path

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
        "check_s3_data",
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
    
    logger.info(f"Checking S3 data for symbols: {symbols}")
    
    for symbol in symbols:
        logger.info(f"=== Data for {symbol} ===")
        
        # Get S3 keys
        latest_key = config.get_s3_key(symbol, is_latest=True)
        full_key = config.get_s3_key(symbol)
        metadata_key = config.get_metadata_key(symbol)
        
        # Load latest data
        logger.info(f"Loading latest data from {latest_key}")
        latest_data = s3_storage.load_json(latest_key)
        if latest_data:
            logger.info(f"Latest data: {json.dumps(latest_data, indent=2)}")
        else:
            logger.warning(f"No latest data found for {symbol}")
        
        # Load metadata
        logger.info(f"Loading metadata from {metadata_key}")
        metadata = s3_storage.load_json(metadata_key)
        if metadata:
            logger.info(f"Metadata: {json.dumps(metadata, indent=2)}")
        else:
            logger.warning(f"No metadata found for {symbol}")
        
        logger.info("=" * 50)

if __name__ == "__main__":
    main()
