#!/usr/bin/env python3
"""
Bulk Stock Data Fetcher

This script fetches historical stock data from Alpha Vantage API
and stores it in AWS S3. It is designed to be run as a one-time job
to populate the data store with historical data.
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

from src.core.config import Config
from src.api.alpha_vantage.client import AlphaVantageClient
from src.data.processing import DataProcessor
from src.data.validation import DataValidator
from src.storage.s3 import S3Storage
from src.storage.atomic import AtomicS3
from src.core.logging import LoggerManager, log_execution_time
from src.notifications.alerts import AlertManager

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
        "fetch_bulk",
        log_dir=config.log_dir,
        console_level=log_level,
        file_level=logging.DEBUG,
        add_timestamp_to_filename=True  # Add timestamp to avoid overwriting logs
    )
    logger = logger_manager.get_logger()
    
    # Enable debug mode if configured
    if config.debug_mode:
        logger_manager.set_debug_mode(True)
    
    # Set up API client
    api_client = AlphaVantageClient(config.api_key, config.api_base_url)
    api_client.set_logger(logger)
    
    # Set up data processor and validator
    data_processor = DataProcessor()
    data_processor.set_logger(logger)
    
    # Set up data validator
    data_validator = DataValidator()
    data_validator.set_logger(logger)
    
    # Set up S3 storage
    s3_storage = S3Storage(config.s3_bucket, config.s3_region)
    s3_storage.set_logger(logger)
    
    # Set up atomic S3 updates
    atomic_s3 = AtomicS3(s3_storage)
    atomic_s3.set_logger(logger)
    
    # Set up alert manager
    alert_manager = AlertManager(config.email_config, config.slack_webhook_url)
    alert_manager.set_logger(logger)
    
    return logger, api_client, data_processor, data_validator, s3_storage, atomic_s3, alert_manager

@log_execution_time(logging.getLogger(__name__))
def process_symbol(symbol, config, api_client, data_processor, data_validator, atomic_s3, logger):
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
    
    # Fetch full historical data from API
    logger.info(f"📥 Fetching full historical data for {symbol}")
    stock_data = api_client.fetch_daily_stock_data(symbol, outputsize="full")
    
    if not stock_data:
        logger.error(f"❌ Failed to fetch data for {symbol}")
        return False
    
    # First validate the API response
    logger.info(f"🔄 Validating API response for {symbol}")
    if not data_validator.validate_api_response(stock_data):
        logger.error(f"❌ API response validation failed for {symbol}")
        return False
        
    # Transform data to DataFrame
    logger.info(f"🔄 Transforming data for {symbol}")
    df = data_processor.transform_to_dataframe(stock_data)
    
    if df is None:
        logger.error(f"❌ Data transformation failed for {symbol}")
        return False
        
    # Validate the transformed data
    logger.info(f"🔄 Validating transformed data for {symbol}")
    if not data_validator.validate_dataframe(df):
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
    logger.info(f"💾 Saving data to S3 for {symbol}")
    
    # Save full data
    full_key = config.get_s3_key(symbol)
    if not atomic_s3.atomic_json_update(full_key, json_data):
        logger.error(f"❌ Failed to save full data for {symbol}")
        return False
    
    # Save latest data
    latest_key = config.get_s3_key(symbol, is_latest=True)
    if not atomic_s3.atomic_json_update(latest_key, latest_json_data):
        logger.error(f"❌ Failed to save latest data for {symbol}")
        return False
    
    # Save daily data for the latest date
    daily_key = config.get_s3_key(symbol, date=latest_date)
    if not atomic_s3.atomic_json_update(daily_key, latest_json_data):
        logger.warning(f"⚠️ Failed to save daily data for {symbol}, but full and latest data were saved")
    
    # Save individual daily data for each date
    logger.info(f"💾 Saving individual daily data for {symbol} (this may take a while)")
    
    # Only save individual files if explicitly requested (to avoid creating too many S3 objects)
    save_individual = os.getenv('SAVE_INDIVIDUAL_DAYS', 'False').lower() == 'true'
    
    if save_individual:
        for date, row in df.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            daily_df = df.loc[[date]]
            daily_json = data_processor.convert_to_json(daily_df)
            daily_json['symbol'] = symbol
            daily_json['last_updated'] = datetime.now().isoformat()
            
            daily_key = config.get_s3_key(symbol, date=date_str)
            if not atomic_s3.atomic_json_update(daily_key, daily_json):
                logger.warning(f"⚠️ Failed to save daily data for {symbol} on {date_str}")
    
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
    
    logger.info(f"✅ Successfully processed {symbol} with {len(df)} data points")
    return True

def main():
    """Main function."""
    start_time = time.time()
    
    # Load configuration
    config = Config()
    
    # Set up components
    logger, api_client, data_processor, data_validator, s3_storage, atomic_s3, alert_manager = setup_components(config)
    
    # Log execution start
    logger.info("=" * 80)
    logger.info(f"🚀 Starting bulk historical stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"📋 Configuration: {config}")
    logger.info("=" * 80)
    
    # Process each symbol
    results = {}
    success_count = 0
    failure_count = 0
    
    for symbol in config.stock_symbols:
        try:
            # Add a delay between API calls to avoid rate limiting
            if symbol != config.stock_symbols[0]:
                delay = 15  # 15 seconds between API calls
                logger.info(f"⏱ Waiting {delay} seconds before processing next symbol to avoid API rate limits")
                time.sleep(delay)
            
            success = process_symbol(symbol, config, api_client, data_processor, data_validator, atomic_s3, logger)
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
            alert_message = f"Bulk historical stock data fetch completed with {failure_count} failures"
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
                source="fetch_bulk.py"
            )
        else:
            # Send success alert
            alert_message = f"Bulk historical stock data fetch completed successfully"
            alert_details = f"""
Execution time: {execution_time:.2f} seconds
Processed symbols: {', '.join(config.stock_symbols)}
"""
            alert_manager.send_success_alert(
                alert_message,
                alert_details,
                source="fetch_bulk.py"
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
