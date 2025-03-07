"""
Alpha Vantage API Models

This module defines data models for Alpha Vantage API responses.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class StockPrice:
    """Stock price data for a single day."""
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    @classmethod
    def from_api_response(cls, date_str: str, data: Dict[str, str]) -> 'StockPrice':
        """
        Create a StockPrice instance from API response data.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            data: API response data for a single day
            
        Returns:
            StockPrice instance
        """
        return cls(
            date=datetime.strptime(date_str, '%Y-%m-%d'),
            open=float(data['1. open']),
            high=float(data['2. high']),
            low=float(data['3. low']),
            close=float(data['4. close']),
            volume=int(data['5. volume'])
        )


@dataclass
class StockMetadata:
    """Metadata for stock price data."""
    symbol: str
    last_refreshed: datetime
    time_zone: str
    
    @classmethod
    def from_api_response(cls, metadata: Dict[str, str]) -> 'StockMetadata':
        """
        Create a StockMetadata instance from API response metadata.
        
        Args:
            metadata: API response metadata
            
        Returns:
            StockMetadata instance
        """
        return cls(
            symbol=metadata['2. Symbol'],
            last_refreshed=datetime.strptime(metadata['3. Last Refreshed'], '%Y-%m-%d'),
            time_zone=metadata['5. Time Zone']
        )


@dataclass
class StockTimeSeries:
    """Complete time series data for a stock."""
    metadata: StockMetadata
    prices: List[StockPrice]
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'StockTimeSeries':
        """
        Create a StockTimeSeries instance from a complete API response.
        
        Args:
            response: Complete API response
            
        Returns:
            StockTimeSeries instance
        """
        metadata = StockMetadata.from_api_response(response['Meta Data'])
        
        time_series = response['Time Series (Daily)']
        prices = [
            StockPrice.from_api_response(date, data)
            for date, data in time_series.items()
        ]
        
        # Sort prices by date (newest first)
        prices.sort(key=lambda x: x.date, reverse=True)
        
        return cls(metadata=metadata, prices=prices)
