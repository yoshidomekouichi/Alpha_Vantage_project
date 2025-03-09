"""
Configuration Module

This module handles loading configuration from environment variables and config files.
It provides a centralized place for all configuration settings.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv

# Default logger - will be replaced by the configured logger
logger = logging.getLogger(__name__)

class Config:
    """Manages application configuration."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            env_file: Path to .env file (default: project_root/.env)
        """
        # Set up default paths
        self.project_root = Path(__file__).parent.parent
        self.default_env_path = self.project_root / ".env"
        
        # Load environment variables
        if env_file:
            self.env_path = Path(env_file)
        else:
            self.env_path = self.default_env_path
            
        self._load_env_file()
        
        # Initialize configuration
        self._init_config()
        
    def set_logger(self, custom_logger):
        """Set a custom logger for the configuration manager."""
        global logger
        logger = custom_logger
    
    def _load_env_file(self):
        """Load environment variables from .env file."""
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.debug(f"Loaded environment variables from {self.env_path}")
        else:
            logger.warning(f"⚠️ Environment file not found: {self.env_path}")
    
    def _init_config(self):
        """Initialize configuration from environment variables."""
        # Debug and mock modes
        self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
        
        # API configuration
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.api_base_url = os.getenv('ALPHA_VANTAGE_BASE_URL', 'https://www.alphavantage.co/query')
        
        # Stock symbols to fetch
        symbols_str = os.getenv('STOCK_SYMBOLS', 'NVDA')
        self.stock_symbols = [s.strip() for s in symbols_str.split(',')]
        
        # S3 configuration
        self.s3_bucket = os.getenv('S3_BUCKET')
        self.s3_region = os.getenv('AWS_REGION', 'ap-northeast-1')
        self.s3_prefix = os.getenv('S3_PREFIX', 'stock-data')
        
        # Email configuration
        self.email_enabled = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'
        if self.email_enabled:
            self.email_config = {
                'smtp_server': os.getenv('SMTP_SERVER'),
                'smtp_port': os.getenv('SMTP_PORT', '587'),
                'smtp_user': os.getenv('SMTP_USER'),
                'smtp_password': os.getenv('SMTP_PASSWORD'),
                'from_email': os.getenv('FROM_EMAIL'),
                'to_email': os.getenv('TO_EMAIL')
            }
        else:
            self.email_config = None
        
        # Slack configuration
        self.slack_enabled = os.getenv('SLACK_ENABLED', 'False').lower() == 'true'
        if self.slack_enabled:
            self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        else:
            self.slack_webhook_url = None
        
        # Logging configuration
        self.log_dir = os.getenv('LOG_DIR', str(self.project_root / 'logs'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Validate required configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration values."""
        missing_vars = []
        
        # Check required variables
        if not self.api_key and not self.mock_mode:
            missing_vars.append('ALPHA_VANTAGE_API_KEY')
        
        if not self.s3_bucket:
            missing_vars.append('S3_BUCKET')
        
        if self.email_enabled:
            for key in ['SMTP_SERVER', 'SMTP_USER', 'SMTP_PASSWORD', 'FROM_EMAIL', 'TO_EMAIL']:
                if not os.getenv(key):
                    missing_vars.append(key)
        
        if self.slack_enabled and not self.slack_webhook_url:
            missing_vars.append('SLACK_WEBHOOK_URL')
        
        # Log warnings for missing variables
        if missing_vars:
            if self.mock_mode and 'ALPHA_VANTAGE_API_KEY' in missing_vars:
                # This is okay in mock mode
                missing_vars.remove('ALPHA_VANTAGE_API_KEY')
                
            if missing_vars:
                logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
    
    def get_s3_key(self, symbol: str, date: str = None, is_latest: bool = False) -> str:
        """
        Get the S3 key for storing stock data.
        
        Args:
            symbol: Stock symbol
            date: Date string (YYYY-MM-DD)
            is_latest: Whether this is the latest data
            
        Returns:
            S3 object key
        """
        if is_latest:
            return f"{self.s3_prefix}/{symbol}/latest.json"
        elif date:
            return f"{self.s3_prefix}/{symbol}/daily/{date}.json"
        else:
            return f"{self.s3_prefix}/{symbol}/full.json"
    
    def get_metadata_key(self, symbol: str) -> str:
        """
        Get the S3 key for storing metadata.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            S3 object key
        """
        return f"{self.s3_prefix}/{symbol}/metadata.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            'debug_mode': self.debug_mode,
            'mock_mode': self.mock_mode,
            'api_base_url': self.api_base_url,
            'stock_symbols': self.stock_symbols,
            's3_bucket': self.s3_bucket,
            's3_region': self.s3_region,
            's3_prefix': self.s3_prefix,
            'email_enabled': self.email_enabled,
            'slack_enabled': self.slack_enabled,
            'log_dir': self.log_dir,
            'log_level': self.log_level
        }
    
    def __str__(self) -> str:
        """Get a string representation of the configuration."""
        config_dict = self.to_dict()
        # Don't include sensitive information
        if 'api_key' in config_dict:
            config_dict['api_key'] = '***'
        if 'email_config' in config_dict and config_dict['email_config']:
            if 'smtp_password' in config_dict['email_config']:
                config_dict['email_config']['smtp_password'] = '***'
        
        return json.dumps(config_dict, indent=2)
