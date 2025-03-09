"""
Data Processing Module

This module handles data validation, transformation, and quality checks
for stock data retrieved from the Alpha Vantage API.
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional, Tuple, List
import json

# Default logger - will be replaced by the configured logger
logger = logging.getLogger(__name__)

class StockDataProcessor:
    """Processes and validates stock data."""
    
    def __init__(self):
        """Initialize the stock data processor."""
        pass
        
    def set_logger(self, custom_logger):
        """Set a custom logger for the processor."""
        global logger
        logger = custom_logger
    
    def validate_and_transform(self, stock_data: Dict[str, Any]) -> Tuple[bool, Optional[pd.DataFrame]]:
        """
        Validate stock data and transform it into a pandas DataFrame.
        
        Args:
            stock_data: Raw stock data from Alpha Vantage API
            
        Returns:
            Tuple of (is_valid, dataframe)
            - is_valid: Boolean indicating if data passed validation
            - dataframe: Pandas DataFrame of the processed data, or None if validation failed
        """
        # Check if data exists
        time_series = stock_data.get("Time Series (Daily)", {})
        if not time_series:
            logger.warning("⚠️ Empty data received! Check API response.")
            return False, None
        
        # Convert to DataFrame
        try:
            df = pd.DataFrame.from_dict(time_series, orient="index")
            
            # Rename columns to more user-friendly names
            df.columns = [col.split('. ')[1] for col in df.columns]
            
            # Convert string values to appropriate numeric types
            df = df.apply(pd.to_numeric, errors='coerce')
            
            # Convert index to datetime
            df.index = pd.to_datetime(df.index)
            
            # Sort by date (descending)
            df = df.sort_index(ascending=False)
            
            # Run quality checks
            validation_result = self._run_quality_checks(df)
            
            return validation_result, df if validation_result else None
            
        except Exception as e:
            logger.exception(f"❌ Error processing stock data: {e}")
            return False, None
    
    def _run_quality_checks(self, df: pd.DataFrame) -> bool:
        """
        Run quality checks on the processed DataFrame.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Boolean indicating if data passed all quality checks
        """
        # Check for missing values
        if df.isnull().any().any():
            missing_counts = df.isnull().sum()
            logger.warning(f"⚠️ Data contains missing values:\n{missing_counts}")
            return False
        
        # Check for zero volume
        if (df["volume"] == 0).any():
            zero_volume_dates = df[df["volume"] == 0].index.tolist()
            logger.warning(f"⚠️ Zero volume detected on dates: {zero_volume_dates}")
            return False
        
        # Check for negative prices
        if (df[["open", "high", "low", "close"]] < 0).any().any():
            negative_prices = df[(df[["open", "high", "low", "close"]] < 0).any(axis=1)]
            logger.warning(f"⚠️ Negative prices detected:\n{negative_prices}")
            return False
        
        # Check for extreme price outliers (10x the 99th percentile)
        for col in ["open", "high", "low", "close"]:
            threshold = df[col].quantile(0.99) * 10
            outliers = df[df[col] > threshold]
            if not outliers.empty:
                logger.warning(f"⚠️ Extreme {col} price outliers detected:\n{outliers}")
                return False
        
        # Check for price inconsistencies (low > high, close outside range)
        if (df["low"] > df["high"]).any():
            inconsistent = df[df["low"] > df["high"]]
            logger.warning(f"⚠️ Price inconsistency detected (low > high):\n{inconsistent}")
            return False
        
        if ((df["close"] > df["high"]) | (df["close"] < df["low"])).any():
            inconsistent = df[(df["close"] > df["high"]) | (df["close"] < df["low"])]
            logger.warning(f"⚠️ Price inconsistency detected (close outside range):\n{inconsistent}")
            return False
        
        if ((df["open"] > df["high"]) | (df["open"] < df["low"])).any():
            inconsistent = df[(df["open"] > df["high"]) | (df["open"] < df["low"])]
            logger.warning(f"⚠️ Price inconsistency detected (open outside range):\n{inconsistent}")
            return False
        
        logger.info("✅ Data quality check passed!")
        return True
    
    def extract_latest_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract the latest data point from the DataFrame.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            DataFrame containing only the latest data point
        """
        return df.head(1)
    
    def convert_to_json(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert DataFrame to a JSON-serializable dictionary.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary representation of the DataFrame
        """
        # Make a copy of the DataFrame to avoid modifying the original
        df_copy = df.copy()
        
        # Name the index 'date' before resetting
        df_copy.index.name = 'date'
        
        # Reset index to make date a column
        df_reset = df_copy.reset_index()
        
        # Convert to dictionary with date as string
        df_reset['date'] = df_reset['date'].dt.strftime('%Y-%m-%d')
        
        # Convert to records format (list of dictionaries)
        records = df_reset.to_dict(orient='records')
        
        return {"data": records}
    
    def convert_to_csv(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to CSV string.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            CSV string representation of the DataFrame
        """
        return df.reset_index().to_csv(index=False)
