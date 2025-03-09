#!/usr/bin/env python3
"""
S3 Path Utilities

This module provides utility functions for generating S3 paths according to
the standard hierarchy structure (V2) used in the Alpha Vantage project.
"""

import os
from typing import Optional, Tuple


def get_s3_key(
    symbol: str,
    data_type: str = "raw",
    date: Optional[str] = None,
    is_latest: bool = False,
    is_mock: Optional[bool] = None,
) -> str:
    """
    Generate an S3 key according to the standard hierarchy structure (V2).

    Args:
        symbol: Stock symbol (e.g., 'NVDA')
        data_type: Data type ('raw' or 'processed')
        date: Date string in YYYY-MM-DD format (for daily data)
        is_latest: Whether this is the latest data
        is_mock: Whether to use test environment (overrides MOCK_MODE env var)

    Returns:
        S3 object key
    """
    # Determine environment prefix (test/prod)
    if is_mock is None:
        # Use environment variable if is_mock is not specified
        is_mock = os.environ.get("MOCK_MODE", "false").lower() == "true"

    env_prefix = "test" if is_mock else "prod"

    # Base path
    base_path = f"{env_prefix}/stock/{data_type}/{symbol}"

    if is_latest:
        return f"{base_path}/latest.json"
    elif date:
        # Split YYYY-MM-DD format into year/month/day path
        year, month, day = date.split("-")
        return f"{base_path}/daily/{year}/{month}/{day}.json"
    else:
        return f"{base_path}/full.json"


def get_metadata_key(symbol: str, data_type: str = "raw", is_mock: Optional[bool] = None) -> str:
    """
    Generate an S3 key for metadata according to the standard hierarchy structure (V2).

    Args:
        symbol: Stock symbol (e.g., 'NVDA')
        data_type: Data type ('raw' or 'processed')
        is_mock: Whether to use test environment (overrides MOCK_MODE env var)

    Returns:
        S3 object key for metadata
    """
    # Determine environment prefix (test/prod)
    if is_mock is None:
        # Use environment variable if is_mock is not specified
        is_mock = os.environ.get("MOCK_MODE", "false").lower() == "true"

    env_prefix = "test" if is_mock else "prod"

    return f"{env_prefix}/stock/{data_type}/{symbol}/metadata.json"


def parse_s3_key(s3_key: str) -> dict:
    """
    Parse an S3 key to extract its components according to the standard hierarchy structure (V2).

    Args:
        s3_key: S3 object key

    Returns:
        Dictionary containing the extracted components
    """
    parts = s3_key.split("/")
    
    # Handle different key formats
    if len(parts) >= 5 and parts[1] == "stock":
        # Standard V2 format: {env}/stock/{data_type}/{symbol}/...
        env = parts[0]
        data_type = parts[2]
        symbol = parts[3]
        
        if len(parts) >= 7 and parts[4] == "daily":
            # Daily data: .../daily/{year}/{month}/{day}.json
            key_type = "daily"
            year = parts[5]
            month = parts[6]
            day = parts[7].split(".")[0]  # Remove .json extension
            date = f"{year}-{month}-{day}"
            return {
                "version": "v2",
                "environment": env,
                "data_type": data_type,
                "symbol": symbol,
                "key_type": key_type,
                "date": date,
                "year": year,
                "month": month,
                "day": day,
            }
        elif parts[4] == "latest.json":
            # Latest data
            return {
                "version": "v2",
                "environment": env,
                "data_type": data_type,
                "symbol": symbol,
                "key_type": "latest",
            }
        elif parts[4] == "full.json":
            # Full data
            return {
                "version": "v2",
                "environment": env,
                "data_type": data_type,
                "symbol": symbol,
                "key_type": "full",
            }
        elif parts[4] == "metadata.json":
            # Metadata
            return {
                "version": "v2",
                "environment": env,
                "data_type": data_type,
                "symbol": symbol,
                "key_type": "metadata",
            }
    elif len(parts) >= 3 and parts[0] == "daily":
        # Lambda format: daily/{symbol}/{date}.json
        symbol = parts[1]
        date = parts[2].split(".")[0]  # Remove .json extension
        return {
            "version": "lambda",
            "symbol": symbol,
            "key_type": "daily",
            "date": date,
        }
    elif len(parts) >= 3 and (parts[0].startswith("stock-data")):
        # V1 format: {prefix}/{symbol}/...
        prefix = parts[0]
        symbol = parts[1]
        
        if len(parts) >= 4 and parts[2] == "daily":
            # Daily data: .../daily/{date}.json
            date = parts[3].split(".")[0]  # Remove .json extension
            return {
                "version": "v1",
                "prefix": prefix,
                "symbol": symbol,
                "key_type": "daily",
                "date": date,
            }
        elif parts[2] == "latest.json":
            # Latest data
            return {
                "version": "v1",
                "prefix": prefix,
                "symbol": symbol,
                "key_type": "latest",
            }
        elif parts[2] == "full.json":
            # Full data
            return {
                "version": "v1",
                "prefix": prefix,
                "symbol": symbol,
                "key_type": "full",
            }
        elif parts[2] == "metadata.json":
            # Metadata
            return {
                "version": "v1",
                "prefix": prefix,
                "symbol": symbol,
                "key_type": "metadata",
            }
    
    # Unknown format
    return {
        "version": "unknown",
        "key": s3_key,
    }


def convert_key_format(s3_key: str, target_version: str = "v2", **kwargs) -> str:
    """
    Convert an S3 key from one format to another.

    Args:
        s3_key: Source S3 object key
        target_version: Target version format ('v1', 'v2', or 'lambda')
        **kwargs: Additional parameters for the target format

    Returns:
        Converted S3 object key
    """
    # Parse the source key
    key_info = parse_s3_key(s3_key)
    
    # Extract common parameters
    symbol = key_info.get("symbol")
    key_type = key_info.get("key_type")
    
    if not symbol or not key_type:
        raise ValueError(f"Could not parse S3 key: {s3_key}")
    
    # Convert to target format
    if target_version == "v2":
        data_type = kwargs.get("data_type", "raw")
        is_mock = kwargs.get("is_mock", key_info.get("environment") == "test")
        
        if key_type == "daily":
            date = key_info.get("date")
            if not date:
                raise ValueError(f"Missing date in S3 key: {s3_key}")
            return get_s3_key(symbol, data_type, date, False, is_mock)
        elif key_type == "latest":
            return get_s3_key(symbol, data_type, None, True, is_mock)
        elif key_type == "full":
            return get_s3_key(symbol, data_type, None, False, is_mock)
        elif key_type == "metadata":
            return get_metadata_key(symbol, data_type, is_mock)
    elif target_version == "lambda":
        if key_type == "daily":
            date = key_info.get("date")
            if not date:
                raise ValueError(f"Missing date in S3 key: {s3_key}")
            return f"daily/{symbol}/{date}.json"
        else:
            raise ValueError(f"Cannot convert {key_type} to lambda format")
    elif target_version == "v1":
        prefix = kwargs.get("prefix", "stock-data-mock")
        
        if key_type == "daily":
            date = key_info.get("date")
            if not date:
                raise ValueError(f"Missing date in S3 key: {s3_key}")
            return f"{prefix}/{symbol}/daily/{date}.json"
        elif key_type == "latest":
            return f"{prefix}/{symbol}/latest.json"
        elif key_type == "full":
            return f"{prefix}/{symbol}/full.json"
        elif key_type == "metadata":
            return f"{prefix}/{symbol}/metadata.json"
    
    raise ValueError(f"Unsupported target version: {target_version}")
