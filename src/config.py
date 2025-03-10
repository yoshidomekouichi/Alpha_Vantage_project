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
            # Force override existing environment variables
            load_dotenv(self.env_path, override=True)
            logger.debug(f"Loaded environment variables from {self.env_path}")
        else:
            logger.warning(f"⚠️ Environment file not found: {self.env_path}")
    
    def _init_config(self):
        """Initialize configuration from environment variables."""
        # Debug and mock modes
        self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
        
        # 環境設定 (test/prod)
        self.environment = os.getenv('ENVIRONMENT', 'test')
        
        # API configuration
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.api_base_url = os.getenv('ALPHA_VANTAGE_BASE_URL', 'https://www.alphavantage.co/query')
        
        # Stock symbols to fetch
        symbols_str = os.getenv('STOCK_SYMBOLS', 'NVDA')
        # Remove comments from the symbols string
        if '#' in symbols_str:
            symbols_str = symbols_str.split('#')[0].strip()
        self.stock_symbols = [s.strip() for s in symbols_str.split(',')]
        
        # S3 configuration
        s3_bucket = os.getenv('S3_BUCKET')
        # Remove comments from the bucket name
        if s3_bucket and '#' in s3_bucket:
            s3_bucket = s3_bucket.split('#')[0].strip()
        self.s3_bucket = s3_bucket
        self.s3_region = os.getenv('AWS_REGION', 'ap-northeast-1')
        self.s3_prefix = os.getenv('S3_PREFIX', 'stock-data')
        
        # S3保存設定
        self.save_to_s3 = os.getenv('SAVE_TO_S3', 'True').lower() == 'true'
        
        # Local storage configuration
        self.local_storage_dir = os.getenv('LOCAL_STORAGE_DIR', str(self.project_root / 'local_data'))
        
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
        
        # Slack Webhook URLの設定
        slack_webhook_url_error = os.getenv('SLACK_WEBHOOK_URL_ERROR')
        slack_webhook_url_warning = os.getenv('SLACK_WEBHOOK_URL_WARNING')
        slack_webhook_url_info = os.getenv('SLACK_WEBHOOK_URL_INFO')
        slack_webhook_url_local_test = os.getenv('SLACK_WEBHOOK_URL_LOCAL_TEST')
        
        # 後方互換性のために、SLACK_WEBHOOK_URLも読み込む
        default_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        # Webhook URLのログ出力（デバッグ用）
        logger.debug(f"SLACK_WEBHOOK_URL_ERROR環境変数: {slack_webhook_url_error}")
        logger.debug(f"SLACK_WEBHOOK_URL_WARNING環境変数: {slack_webhook_url_warning}")
        logger.debug(f"SLACK_WEBHOOK_URL_INFO環境変数: {slack_webhook_url_info}")
        logger.debug(f"SLACK_WEBHOOK_URL_LOCAL_TEST環境変数: {slack_webhook_url_local_test}")
        logger.debug(f"SLACK_WEBHOOK_URL環境変数（後方互換性）: {default_webhook_url}")
        
        if self.slack_enabled:
            # 各Webhook URLが設定されているか確認
            # デフォルトのWebhook URLがあれば、それを使用
            if not slack_webhook_url_error:
                slack_webhook_url_error = default_webhook_url
            if not slack_webhook_url_warning:
                slack_webhook_url_warning = default_webhook_url
            if not slack_webhook_url_info:
                slack_webhook_url_info = default_webhook_url
                
            # いずれかのWebhook URLが設定されているか確認
            if not (slack_webhook_url_error or slack_webhook_url_warning or slack_webhook_url_info):
                logger.warning("⚠️ No Slack webhook URLs are set, but Slack notifications are enabled")
                self.slack_enabled = False
                self.slack_webhook_url_error = None
                self.slack_webhook_url_warning = None
                self.slack_webhook_url_info = None
            else:
                # URLの形式を確認
                for url_name, url in [
                    ("SLACK_WEBHOOK_URL_ERROR", slack_webhook_url_error),
                    ("SLACK_WEBHOOK_URL_WARNING", slack_webhook_url_warning),
                    ("SLACK_WEBHOOK_URL_INFO", slack_webhook_url_info)
                ]:
                    if url and not url.startswith('https://hooks.slack.com/'):
                        logger.warning(f"⚠️ Invalid Slack webhook URL format for {url_name}: {url}")
                
                # Webhook URLを設定
                self.slack_webhook_url_error = slack_webhook_url_error
                self.slack_webhook_url_warning = slack_webhook_url_warning
                self.slack_webhook_url_info = slack_webhook_url_info
                self.slack_webhook_url_local_test = slack_webhook_url_local_test
                
                logger.debug(f"Slack通知が有効です")
                logger.debug(f"slack_webhook_url_error: {self.slack_webhook_url_error}")
                logger.debug(f"slack_webhook_url_warning: {self.slack_webhook_url_warning}")
                logger.debug(f"slack_webhook_url_info: {self.slack_webhook_url_info}")
                logger.debug(f"slack_webhook_url_local_test: {self.slack_webhook_url_local_test}")
        else:
            self.slack_webhook_url_error = None
            self.slack_webhook_url_warning = None
            self.slack_webhook_url_info = None
            self.slack_webhook_url_local_test = None
            logger.debug("Slack通知は無効です")
        
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
        
        if self.slack_enabled and not (self.slack_webhook_url_error or self.slack_webhook_url_warning or self.slack_webhook_url_info):
            missing_vars.append('SLACK_WEBHOOK_URL_* (at least one)')
        
        # Log warnings for missing variables
        if missing_vars:
            if self.mock_mode and 'ALPHA_VANTAGE_API_KEY' in missing_vars:
                # This is okay in mock mode
                missing_vars.remove('ALPHA_VANTAGE_API_KEY')
                
            if missing_vars:
                logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
    
    def get_s3_key(self, symbol: str, date: str = None, is_latest: bool = False) -> str:
        """
        Get the S3 key for storing stock data (旧バージョン).
        
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
        Get the S3 key for storing metadata (旧バージョン).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            S3 object key
        """
        return f"{self.s3_prefix}/{symbol}/metadata.json"
    
    def get_s3_key_v2(self, symbol: str, data_type: str = 'raw', date: str = None, is_latest: bool = False) -> str:
        """
        新しいフォルダ構造に基づいてS3キーを生成
        
        Args:
            symbol: 銘柄シンボル
            data_type: データタイプ ('raw' または 'processed')
            date: 日付文字列 (YYYY-MM-DD)
            is_latest: 最新データかどうか
            
        Returns:
            S3オブジェクトキー
        """
        # 環境設定（test/prod）
        env_prefix = 'test' if self.mock_mode else 'prod'
        
        # ベースパス
        base_path = f"{env_prefix}/stock/{data_type}/{symbol}"
        
        if is_latest:
            return f"{base_path}/latest.json"
        elif date:
            # YYYY-MM-DD形式から年/月/日のパスを生成
            year, month, day = date.split('-')
            return f"{base_path}/daily/{year}/{month}/{day}.json"
        else:
            return f"{base_path}/full.json"
    
    def get_metadata_key_v2(self, symbol: str, data_type: str = 'raw') -> str:
        """
        新しいフォルダ構造に基づいてメタデータのS3キーを生成
        
        Args:
            symbol: 銘柄シンボル
            data_type: データタイプ ('raw' または 'processed')
            
        Returns:
            S3オブジェクトキー
        """
        env_prefix = 'test' if self.mock_mode else 'prod'
        return f"{env_prefix}/stock/{data_type}/{symbol}/metadata.json"
    
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
            'save_to_s3': self.save_to_s3,
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
