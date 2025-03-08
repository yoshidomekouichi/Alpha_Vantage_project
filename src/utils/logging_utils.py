"""
Logging Utilities Module

This module provides logging functionality with configurable outputs
to console and file, with support for different log levels and formatting.
"""

import os
import logging
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Pattern, Union

class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages."""
    
    def __init__(self, sensitive_patterns: Dict[str, Pattern] = None):
        """
        Initialize the filter with patterns to mask.
        
        Args:
            sensitive_patterns: Dictionary of name:pattern pairs to mask
        """
        super().__init__()
        self.sensitive_patterns = sensitive_patterns or {}
        
        # Add default patterns for common sensitive data
        if not self.sensitive_patterns:
            self.sensitive_patterns = {
                'api_key': re.compile(r'([\'"][A-Za-z0-9]{20,}[\'"])', re.IGNORECASE),
                'webhook_url': re.compile(r'(https://hooks\.slack\.com/services/[A-Za-z0-9/]+)', re.IGNORECASE),
                'password': re.compile(r'([\'"]?password[\'"]?\s*[:=]\s*[\'"][^\'\"]+[\'"])', re.IGNORECASE),
                'secret_key': re.compile(r'([\'"]?secret[_-]?key[\'"]?\s*[:=]\s*[\'"][^\'\"]+[\'"])', re.IGNORECASE),
                'access_key': re.compile(r'([\'"]?access[_-]?key[\'"]?\s*[:=]\s*[\'"][^\'\"]+[\'"])', re.IGNORECASE),
            }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records to mask sensitive data.
        
        Args:
            record: The log record to filter
            
        Returns:
            True to include the record in the log
        """
        if isinstance(record.msg, str):
            # Mask sensitive data in string messages
            for name, pattern in self.sensitive_patterns.items():
                record.msg = pattern.sub(f'***MASKED_{name.upper()}***', record.msg)
        elif isinstance(record.msg, dict):
            # Mask sensitive data in dictionary messages
            record.msg = self._mask_dict(record.msg)
        
        # Always include the record
        return True
    
    def _mask_dict(self, data: Dict) -> Dict:
        """
        Recursively mask sensitive data in a dictionary.
        
        Args:
            data: Dictionary to mask
            
        Returns:
            Masked dictionary
        """
        result = {}
        sensitive_keys = {'password', 'api_key', 'secret', 'token', 'webhook', 'key', 'access_key', 'secret_key'}
        
        for key, value in data.items():
            # Check if this is a sensitive key
            is_sensitive = any(sk in key.lower() for sk in sensitive_keys)
            
            if is_sensitive and isinstance(value, str):
                # Mask sensitive string values
                result[key] = f"***MASKED_{key.upper()}***"
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self._mask_dict(value)
            elif isinstance(value, list):
                # Process lists
                result[key] = [
                    self._mask_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Keep other values as is
                result[key] = value
                
        return result

class LoggerManager:
    """Manages logging configuration and provides logger instances."""
    
    def __init__(
        self, 
        name: str, 
        log_dir: str = None, 
        console_level: int = logging.INFO, 
        file_level: int = logging.DEBUG,
        log_format: str = "%(asctime)s [%(levelname)s] %(message)s",
        date_format: str = "%Y-%m-%d %H:%M:%S",
        add_timestamp_to_filename: bool = False,
        is_mock: bool = False,
        mask_sensitive_data: bool = True
    ):
        """
        Initialize the logger manager.
        
        Args:
            name: Logger name
            log_dir: Directory for log files (default: project_root/logs)
            console_level: Logging level for console output
            file_level: Logging level for file output
            log_format: Format string for log messages
            date_format: Format string for timestamps
            add_timestamp_to_filename: Whether to add a timestamp to the log filename
            is_mock: Whether this is a mock environment
            mask_sensitive_data: Whether to mask sensitive data in logs
        """
        self.name = name
        self.log_format = log_format
        self.date_format = date_format
        self.is_mock = is_mock
        
        # Set up log directory
        if log_dir is None:
            # Default to project_root/logs
            self.log_dir = Path(__file__).parent.parent.parent / "logs"
        else:
            self.log_dir = Path(log_dir)
        
        # Use environment-specific subdirectory
        if self.is_mock:
            self.log_dir = self.log_dir / "mock"
        else:
            self.log_dir = self.log_dir / "prod"
            
        # Print for debugging
        print(f"Log directory: {self.log_dir}")
        
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating log directory: {e}")
            # Use a fallback directory
            self.log_dir = Path.cwd() / "logs"
            if self.is_mock:
                self.log_dir = self.log_dir / "mock"
            else:
                self.log_dir = self.log_dir / "prod"
            print(f"Using fallback log directory: {self.log_dir}")
            os.makedirs(self.log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
        self.logger.propagate = False  # Prevent propagation to root logger
        
        # Clear any existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        
        # Create formatter
        self.formatter = logging.Formatter(log_format, date_format)
        
        # Add sensitive data filter if requested
        if mask_sensitive_data:
            self.sensitive_filter = SensitiveDataFilter()
            self.logger.addFilter(self.sensitive_filter)
        
        # Set up console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(console_level)
        self.console_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.console_handler)
        
        # Set up file handler
        if add_timestamp_to_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{name}_{timestamp}.log"
        else:
            log_filename = f"{name}.log"
            
        log_file_path = self.log_dir / log_filename
        
        self.file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        self.file_handler.setLevel(file_level)
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)
        
        # Log the initialization
        env_type = "Mock" if self.is_mock else "Production"
        self.logger.debug(f"{env_type} logger initialized. Log file: {log_file_path}")
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger
    
    def add_separator(self, char: str = "-", length: int = 80):
        """Add a separator line to the log."""
        self.logger.info(char * length)
    
    def log_execution_start(self, script_name: str, params: Dict[str, Any] = None):
        """Log the start of script execution with a clear separator."""
        self.add_separator("=")
        self.logger.info(f"🚀 EXECUTION START: {script_name} at {datetime.now().strftime(self.date_format)}")
        if params:
            # Filter out sensitive environment variables before logging
            safe_params = self._filter_sensitive_env_vars(params)
            self.logger.info(f"📋 Parameters: {safe_params}")
        self.add_separator("=")
    
    def log_execution_end(self, script_name: str, success: bool = True, execution_time: float = None):
        """Log the end of script execution with a clear separator."""
        self.add_separator("=")
        status = "✅ SUCCESS" if success else "❌ FAILURE"
        self.logger.info(f"{status}: {script_name} at {datetime.now().strftime(self.date_format)}")
        if execution_time is not None:
            self.logger.info(f"⏱ Execution time: {execution_time:.2f} seconds")
        self.add_separator("=")
    
    def set_console_level(self, level: int):
        """Set the logging level for console output."""
        self.console_handler.setLevel(level)
    
    def set_file_level(self, level: int):
        """Set the logging level for file output."""
        self.file_handler.setLevel(level)
    
    def set_debug_mode(self, enabled: bool = True):
        """Enable or disable debug mode (sets console level to DEBUG)."""
        if enabled:
            self.set_console_level(logging.DEBUG)
            self.logger.debug("🔍 Debug mode enabled")
        else:
            self.set_console_level(logging.INFO)
            self.logger.info("🔍 Debug mode disabled")
    
    def _filter_sensitive_env_vars(self, env_vars: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter sensitive information from environment variables.
        
        Args:
            env_vars: Dictionary of environment variables
            
        Returns:
            Filtered dictionary with sensitive values masked
        """
        if not isinstance(env_vars, dict):
            return env_vars
            
        sensitive_keys = {
            'api_key', 'key', 'token', 'password', 'secret', 'webhook', 
            'access_key', 'secret_key', 'webhook_url'
        }
        
        result = {}
        for key, value in env_vars.items():
            # Check if this is a sensitive key
            key_lower = key.lower()
            is_sensitive = any(sk in key_lower for sk in sensitive_keys)
            
            if is_sensitive and isinstance(value, str):
                # Mask sensitive values
                result[key] = f"***MASKED_{key.upper()}***"
            else:
                # Keep other values as is
                result[key] = value
                
        return result


def create_default_logger(
    name: str, 
    debug_mode: bool = False, 
    is_mock: bool = False,
    mask_sensitive_data: bool = True
) -> logging.Logger:
    """
    Create a logger with default settings.
    
    Args:
        name: Logger name
        debug_mode: Whether to enable debug mode
        is_mock: Whether this is a mock environment
        mask_sensitive_data: Whether to mask sensitive data in logs
        
    Returns:
        Configured logger instance
    """
    console_level = logging.DEBUG if debug_mode else logging.INFO
    manager = LoggerManager(
        name, 
        console_level=console_level, 
        is_mock=is_mock,
        mask_sensitive_data=mask_sensitive_data
    )
    return manager.get_logger()


def log_execution_time(logger, func_name: str = None):
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger: Logger instance
        func_name: Optional name to use in the log (defaults to function name)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = func_name or func.__name__
            start_time = time.time()
            logger.debug(f"⏱ Starting {name}")
            
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time
                logger.debug(f"⏱ {name} completed in {execution_time:.2f} seconds")
                return result
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.error(f"❌ {name} failed after {execution_time:.2f} seconds: {e}")
                raise
                
        return wrapper
    return decorator


def safe_log_dict(logger, level: int, message: str, data: Dict[str, Any]):
    """
    Safely log a dictionary with sensitive data masked.
    
    Args:
        logger: Logger instance
        level: Logging level
        message: Message prefix
        data: Dictionary to log
    """
    # Create a copy to avoid modifying the original
    filtered_data = {}
    sensitive_keys = {
        'api_key', 'key', 'token', 'password', 'secret', 'webhook', 
        'access_key', 'secret_key', 'webhook_url'
    }
    
    for key, value in data.items():
        key_lower = key.lower()
        is_sensitive = any(sk in key_lower for sk in sensitive_keys)
        
        if is_sensitive and isinstance(value, str):
            filtered_data[key] = f"***MASKED_{key.upper()}***"
        elif isinstance(value, dict):
            # Recursively filter nested dictionaries
            filtered_data[key] = {}
            for k, v in value.items():
                k_lower = k.lower()
                is_k_sensitive = any(sk in k_lower for sk in sensitive_keys)
                
                if is_k_sensitive and isinstance(v, str):
                    filtered_data[key][k] = f"***MASKED_{k.upper()}***"
                else:
                    filtered_data[key][k] = v
        else:
            filtered_data[key] = value
    
    # Log the filtered data
    logger.log(level, f"{message}: {json.dumps(filtered_data, indent=2)}")
