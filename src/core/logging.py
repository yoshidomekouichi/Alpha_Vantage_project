"""
Logging Utilities Module

This module provides logging functionality with configurable outputs
to console and file, with support for different log levels and formatting.
"""

import os
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

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
        is_mock: bool = False
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
            self.logger.info(f"📋 Parameters: {params}")
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


def create_default_logger(name: str, debug_mode: bool = False, is_mock: bool = False) -> logging.Logger:
    """
    Create a logger with default settings.
    
    Args:
        name: Logger name
        debug_mode: Whether to enable debug mode
        is_mock: Whether this is a mock environment
        
    Returns:
        Configured logger instance
    """
    console_level = logging.DEBUG if debug_mode else logging.INFO
    manager = LoggerManager(name, console_level=console_level, is_mock=is_mock)
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
