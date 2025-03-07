#!/usr/bin/env python3
"""
Daily Stock Data Fetcher

This script fetches the latest daily stock data from Alpha Vantage API
and stores it in AWS S3. It is designed to be run as a daily batch job.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import traceback

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config
from src.utils.api_client import AlphaVantageClient
from src.utils.data_processing import StockDataProcessor
from src.utils.storage import S3Storage
from src.utils.atomic_s3 import AtomicS3
from src.utils.logging_utils import LoggerManager, log_execution_time
from src.utils.alerts import AlertManager

def setup_components(config):
    """
    Set up all components with the given configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        Tuple of (logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager)
    """
    # Set up logger
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger_manager = LoggerManager(
        "fetch_daily",
        log_dir=config.log_dir,
        console_level=log_level,
        file_level=logging.DEBUG
    )
    logger = logger_manager.get_logger()
    
    # Enable debug mode if configured
    if config.debug_mode:
        logger_manager.set_debug_mode(True)
    
    # Set up API client
    api_client = AlphaVantageClient(config.api_key, config.api_base_url)
    api_client.set_logger(logger)
    
    # Set up data processor
    data_processor = StockDataProcessor()
    data_processor.set_logger(logger)
    
    # Set up S3 storage
    s3_storage = S3Storage(config.s3_bucket, config.s3_region)
    s3_storage.set_logger(logger)
    
    # Set up atomic S3 updates
    atomic_s3 = AtomicS3(s3_storage)
    atomic_s3.set_logger(logger)
    
    # Set up alert manager
    alert_manager = AlertManager(config.email_config, config.slack_webhook_url)
    alert_manager.set_logger(logger)
    
    return logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager

@log_execution_time(logging.getLogger(__name__))
def process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger):
    """
    Process a single stock symbol.
    
    Args:
        symbol: Stock symbol to process
        config: Configuration object
        api_client: Alpha Vantage API client
        data_processor: Data processor
        atomic_s3: Atomic S3 updater
        logger: Logger
        
    Returns:
        Boolean indicating success
    """
    logger.info(f"🔍 Processing symbol: {symbol}")
    
    # Fetch data from API
    stock_data = api_client.fetch_daily_stock_data(symbol)
    
    if not stock_data:
        logger.error(f"❌ Failed to fetch data for {symbol}")
        return False
    
    # Validate and transform data
    is_valid, df = data_processor.validate_and_transform(stock_data)
    
    if not is_valid or df is None:
        logger.error(f"❌ Data validation failed for {symbol}")
        return False
    
    # Extract latest data point
    latest_df = data_processor.extract_latest_data(df)
    latest_date = latest_df.index[0].strftime('%Y-%m-%d')
    
    # Convert to JSON
    json_data = data_processor.convert_to_json(df)
    latest_json_data = data_processor.convert_to_json(latest_df)
    
    # Add metadata
    json_data['symbol'] = symbol
    json_data['last_updated'] = datetime.now().isoformat()
    latest_json_data['symbol'] = symbol
    latest_json_data['last_updated'] = datetime.now().isoformat()
    
    # Save to S3
    full_key = config.get_s3_key(symbol)
    latest_key = config.get_s3_key(symbol, is_latest=True)
    daily_key = config.get_s3_key(symbol, date=latest_date)
    
    # Save latest data atomically
    if not atomic_s3.atomic_json_update(latest_key, latest_json_data):
        logger.error(f"❌ Failed to save latest data for {symbol}")
        return False
    
    # Save daily data atomically
    if not atomic_s3.atomic_json_update(daily_key, latest_json_data):
        logger.warning(f"⚠️ Failed to save daily data for {symbol}, but latest data was saved")
    
    # Update full data atomically
    if not atomic_s3.atomic_json_update(full_key, json_data):
        logger.warning(f"⚠️ Failed to update full data for {symbol}, but latest data was saved")
    
    # Update metadata
    metadata = {
        'symbol': symbol,
        'last_updated': datetime.now().isoformat(),
        'latest_date': latest_date,
        'data_points': len(df),
        'date_range': {
            'start': df.index[-1].strftime('%Y-%m-%d'),
            'end': latest_date
        }
    }
    
    metadata_key = config.get_metadata_key(symbol)
    if not atomic_s3.atomic_json_update(metadata_key, metadata):
        logger.warning(f"⚠️ Failed to update metadata for {symbol}")
    
    logger.info(f"✅ Successfully processed {symbol} for date {latest_date}")
    return True

def main():
    """Main function."""
    start_time = time.time()
    
    # Load configuration
    config = Config()
    
    # Set up components
    logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager = setup_components(config)
    
    # Log execution start
    logger.info("=" * 80)
    logger.info(f"🚀 Starting daily stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"📋 Configuration: {config}")
    logger.info("=" * 80)
    
    # Process each symbol
    results = {}
    success_count = 0
    failure_count = 0
    
    for symbol in config.stock_symbols:
        try:
            success = process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger)
            results[symbol] = "SUCCESS" if success else "FAILURE"
            
            if success:
                success_count += 1
            else:
                failure_count += 1
                
        except Exception as e:
            logger.exception(f"❌ Unexpected error processing {symbol}: {e}")
            results[symbol] = f"ERROR: {str(e)}"
            failure_count += 1
    
    # Calculate execution time
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Log execution summary
    logger.info("=" * 80)
    logger.info(f"📊 Execution summary:")
    logger.info(f"⏱ Total execution time: {execution_time:.2f} seconds")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failure_count}")
    logger.info(f"📋 Results by symbol: {json.dumps(results, indent=2)}")
    logger.info("=" * 80)
    
    # Send alerts if configured
    if config.email_enabled or config.slack_enabled:
        if failure_count > 0:
            # Send warning or error alert
            alert_message = f"Daily stock data fetch completed with {failure_count} failures"
            alert_details = f"""
Execution time: {execution_time:.2f} seconds
Successful: {success_count}
Failed: {failure_count}

Results by symbol:
{json.dumps(results, indent=2)}
"""
            alert_manager.send_warning_alert(
                alert_message,
                alert_details,
                source="fetch_daily.py"
            )
        else:
            # Send success alert
            alert_message = f"Daily stock data fetch completed successfully"
            alert_details = f"""
Execution time: {execution_time:.2f} seconds
Processed symbols: {', '.join(config.stock_symbols)}
"""
            alert_manager.send_success_alert(
                alert_message,
                alert_details,
                source="fetch_daily.py"
            )
    
    # Return exit code
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    # Import logging here to avoid circular imports
    import logging
    
    try:
        sys.exit(main())
    except Exception as e:
        # Catch any unexpected exceptions
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)
