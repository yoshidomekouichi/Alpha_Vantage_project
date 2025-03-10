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
from datetime import datetime, timedelta
from pathlib import Path
import traceback

# 現在のディレクトリをPythonパスに追加
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # プロジェクトルートからのインポート
    from src.config import Config
    from src.utils.api_client import AlphaVantageClient
    from src.utils.data_processing import StockDataProcessor
    from src.utils.storage import S3Storage
    from src.utils.atomic_s3 import AtomicS3
    from src.utils.logging_utils import LoggerManager, log_execution_time
    from src.utils.alerts import AlertManager
    from src.utils.local_storage import LocalStorage
except ImportError:
    # 相対インポート
    from config import Config
    from utils.api_client import AlphaVantageClient
    from utils.data_processing import StockDataProcessor
    from utils.storage import S3Storage
    from utils.atomic_s3 import AtomicS3
    from utils.logging_utils import LoggerManager, log_execution_time
    from utils.alerts import AlertManager
    from utils.local_storage import LocalStorage

def setup_components(config):
    """
    Set up all components with the given configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        Tuple of (logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager, local_storage)
    """
    # ロガー初期化
    logger = logging.getLogger(__name__)
    
    try:
        # Set up logger
        log_level = getattr(logging, config.log_level.upper(), logging.INFO)
        
        # Lambda環境の場合はログディレクトリを/tmp以下に設定
        if os.environ.get('AWS_LAMBDA_EXECUTION', '').lower() == 'true':
            log_dir = Path('/tmp/logs')
            logger.info(f"Lambda環境のため、ログディレクトリを {log_dir} に設定します")
        else:
            log_dir = config.log_dir
            logger.info(f"ローカル環境のため、ログディレクトリを {log_dir} に設定します")
            
        # ログディレクトリが存在しない場合は作成
        try:
            os.makedirs(log_dir, exist_ok=True)
            logger.info(f"ログディレクトリを作成しました: {log_dir}")
        except Exception as e:
            logger.error(f"ログディレクトリの作成に失敗しました: {e}")
            logger.error(traceback.format_exc())
        
        try:
            logger_manager = LoggerManager(
                "fetch_daily",
                log_dir=log_dir,
                console_level=log_level,
                file_level=logging.DEBUG,
                is_mock=config.mock_mode
            )
            logger = logger_manager.get_logger()
            logger.info("LoggerManagerの初期化に成功しました")
        except Exception as e:
            logger.error(f"LoggerManagerの初期化に失敗しました: {e}")
            logger.error(traceback.format_exc())
            # フォールバックロガーを使用
            logger.warning("フォールバックロガーを使用します")
        
        # Enable debug mode if configured
        if config.debug_mode:
            try:
                logger_manager.set_debug_mode(True)
                logger.info("デバッグモードを有効化しました")
            except Exception as e:
                logger.error(f"デバッグモードの有効化に失敗しました: {e}")
        
        # Log environment type
        env_type = "Lambda" if os.environ.get('AWS_LAMBDA_EXECUTION', '').lower() == 'true' else "Local"
        if config.mock_mode:
            env_type += " (Mock)"
        logger.info(f"🔧 Running in {env_type} environment")
        
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
        alert_manager = AlertManager(
            config.email_config,
            config.slack_webhook_url_error,
            config.slack_webhook_url_warning,
            config.slack_webhook_url_info
        )
        alert_manager.set_logger(logger)
        
        # Slack設定の詳細をログに出力（デバッグモードの場合のみ）
        if config.debug_mode:
            logger.debug("=" * 80)
            logger.debug("Slack設定の詳細:")
            logger.debug(f"config.slack_enabled: {config.slack_enabled}")
            logger.debug(f"config.slack_webhook_url_error: {config.slack_webhook_url_error}")
            logger.debug(f"config.slack_webhook_url_warning: {config.slack_webhook_url_warning}")
            logger.debug(f"config.slack_webhook_url_info: {config.slack_webhook_url_info}")
            
            # AlertManagerの内部状態を確認
            try:
                logger.debug("AlertManagerの内部状態:")
                if hasattr(alert_manager, 'slack_webhook_url_error'):
                    logger.debug(f"alert_manager.slack_webhook_url_error: {alert_manager.slack_webhook_url_error}")
                if hasattr(alert_manager, 'slack_webhook_url_warning'):
                    logger.debug(f"alert_manager.slack_webhook_url_warning: {alert_manager.slack_webhook_url_warning}")
                if hasattr(alert_manager, 'slack_webhook_url_info'):
                    logger.debug(f"alert_manager.slack_webhook_url_info: {alert_manager.slack_webhook_url_info}")
            except Exception as e:
                logger.error(f"AlertManagerの内部状態確認中にエラーが発生しました: {e}")
        
        # テスト用のSlack通知を送信（デバッグモードの場合のみ、かつローカルでない場合）
        if config.debug_mode and config.slack_enabled and not os.environ.get('AWS_LAMBDA_EXECUTION', '').lower() == 'true' and config.save_to_s3:
            try:
                logger.debug("テスト用のSlack通知を送信します...")
                test_message = "🔍 This is a test message from fetch_daily.py"
                test_details = "Debug mode is enabled. This is just a test to verify Slack notifications are working."
                
                # テスト用の通知を送信
                alert_manager.send_info_alert(
                    test_message,
                    test_details,
                    source="fetch_daily.py (DEBUG)",
                    send_email=False,
                    send_slack=True
                )
                logger.debug("✅ テスト通知の送信に成功しました")
            except Exception as e:
                logger.error(f"❌ テスト通知の送信に失敗しました: {e}")
                logger.error(traceback.format_exc())
        else:
            logger.debug("ローカル環境またはSAVE_TO_S3=falseのため、テスト通知をスキップします")
        
        # Set up local storage
        local_storage = None
        if not config.save_to_s3:
            try:
                local_storage = LocalStorage(config.local_storage_dir)
                local_storage.set_logger(logger)
                logger.info(f"🔧 LocalStorage initialized with directory: {config.local_storage_dir}")
            except Exception as e:
                logger.error(f"❌ LocalStorage initialization failed: {e}")
                logger.error(traceback.format_exc())
        
        if config.debug_mode:
            logger.debug("=" * 80)
        
        return logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager, local_storage
    except Exception as e:
        logger.error(f"setup_components 関数でエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        return None, None, None, None, None, None, None

@log_execution_time(logging.getLogger(__name__))
def process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger, local_storage=None):
    """
    Process a single stock symbol.
    
    Args:
        symbol: Stock symbol to process
        config: Configuration object
        api_client: Alpha Vantage API client
        data_processor: Data processor
        atomic_s3: Atomic S3 updater
        logger: Logger
        local_storage: Local storage (optional)
        
    Returns:
        Tuple of (Boolean indicating success, latest_date)
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
    api_date = latest_df.index[0].strftime('%Y-%m-%d')
    
    # 前日の日付を計算（JST基準）
    now = datetime.now()
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # APIから取得した日付を使用（JSONの日付とフォルダの日付を一致させる）
    logger.info(f"APIから取得した日付: {api_date}, 計算された前日の日付: {yesterday}")
    if api_date < yesterday:
        logger.warning(f"⚠️ APIから取得した日付({api_date})が前日({yesterday})より古いです。これは土日や祝日の可能性があります。")
    
    # JSONの日付とフォルダの日付を一致させるため、APIから取得した日付を使用
    latest_date = api_date
    
    # Convert to JSON
    json_data = data_processor.convert_to_json(df)
    latest_json_data = data_processor.convert_to_json(latest_df)
    
    # Add metadata
    json_data['symbol'] = symbol
    json_data['last_updated'] = datetime.now().isoformat()
    latest_json_data['symbol'] = symbol
    latest_json_data['last_updated'] = datetime.now().isoformat()
    
    # 処理済みデータの作成（今回は生データと同じ）
    # 将来的には、ここで追加の処理を行うことができます
    processed_json_data = json_data.copy()
    processed_latest_json_data = latest_json_data.copy()
    
    # 新しいフォルダ構造でのS3キーを生成
    # 生データ用のキー
    raw_full_key = config.get_s3_key_v2(symbol, 'raw')
    raw_latest_key = config.get_s3_key_v2(symbol, 'raw', is_latest=True)
    raw_daily_key = config.get_s3_key_v2(symbol, 'raw', date=latest_date)
    raw_metadata_key = config.get_metadata_key_v2(symbol, 'raw')
    
    # 処理済みデータ用のキー
    processed_full_key = config.get_s3_key_v2(symbol, 'processed')
    processed_latest_key = config.get_s3_key_v2(symbol, 'processed', is_latest=True)
    processed_daily_key = config.get_s3_key_v2(symbol, 'processed', date=latest_date)
    processed_metadata_key = config.get_metadata_key_v2(symbol, 'processed')
    
    # メタデータの作成
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
    
    # データの保存
    if config.save_to_s3:
        # S3に保存
        logger.info(f"🔄 Saving data to S3 for {symbol}...")
        
        # 生データの保存
        # 最新データの保存
        if not atomic_s3.atomic_json_update(raw_latest_key, latest_json_data):
            logger.error(f"❌ Failed to save raw latest data for {symbol}")
            return False
        
        # 日別データの保存
        if not atomic_s3.atomic_json_update(raw_daily_key, latest_json_data):
            logger.warning(f"⚠️ Failed to save raw daily data for {symbol}, but latest data was saved")
        
        # 全期間データの保存
        if not atomic_s3.atomic_json_update(raw_full_key, json_data):
            logger.warning(f"⚠️ Failed to update raw full data for {symbol}, but latest data was saved")
        
        # メタデータの保存
        if not atomic_s3.atomic_json_update(raw_metadata_key, metadata):
            logger.warning(f"⚠️ Failed to update raw metadata for {symbol}")
        
        # 処理済みデータの保存
        logger.info(f"🔄 Saving processed data to S3 for {symbol}...")
        
        # 最新データの保存
        if not atomic_s3.atomic_json_update(processed_latest_key, processed_latest_json_data):
            logger.warning(f"⚠️ Failed to save processed latest data for {symbol}")
        
        # 日別データの保存
        if not atomic_s3.atomic_json_update(processed_daily_key, processed_latest_json_data):
            logger.warning(f"⚠️ Failed to save processed daily data for {symbol}")
        
        # 全期間データの保存
        if not atomic_s3.atomic_json_update(processed_full_key, processed_json_data):
            logger.warning(f"⚠️ Failed to update processed full data for {symbol}")
        
        # メタデータの保存
        if not atomic_s3.atomic_json_update(processed_metadata_key, metadata):
            logger.warning(f"⚠️ Failed to update processed metadata for {symbol}")
    elif local_storage:
        # ローカルに保存
        logger.info(f"🔄 Saving data to local storage for {symbol}...")
        
        # Lambda関数と同じ構造でローカルに保存
        # 1. 日次データ
        local_daily_key = f"daily/{symbol}/{latest_date}.json"
        if not local_storage.put_object(local_daily_key, latest_json_data):
            logger.warning(f"⚠️ Failed to save daily data to local storage for {symbol}")
        else:
            logger.info(f"✅ Saved daily data to local storage: {local_daily_key}")
        
        # 2. 最新データ
        local_latest_key = f"{symbol}/latest.json"
        if not local_storage.put_object(local_latest_key, latest_json_data):
            logger.warning(f"⚠️ Failed to save latest data to local storage for {symbol}")
        else:
            logger.info(f"✅ Saved latest data to local storage: {local_latest_key}")
        
        # 3. 全期間データ
        local_full_key = f"{symbol}/full.json"
        if not local_storage.put_object(local_full_key, json_data):
            logger.warning(f"⚠️ Failed to save full data to local storage for {symbol}")
        else:
            logger.info(f"✅ Saved full data to local storage: {local_full_key}")
        
        # 4. メタデータ
        local_metadata_key = f"{symbol}/metadata.json"
        if not local_storage.put_object(local_metadata_key, metadata):
            logger.warning(f"⚠️ Failed to save metadata to local storage for {symbol}")
        else:
            logger.info(f"✅ Saved metadata to local storage: {local_metadata_key}")
    else:
        logger.warning(f"⚠️ No storage method available for {symbol}. Data will not be saved.")
        return False
    
    logger.info(f"✅ Successfully processed {symbol} for date {latest_date}")
    return True, latest_date

def main():
    """Main function."""
    # 標準ロガーを初期化
    logger = logging.getLogger(__name__)
    
    # 環境変数の設定をログに出力（標準ロガーを使用）
    print(f"Environment variables:")
    print(f"MOCK_MODE: {os.environ.get('MOCK_MODE', 'not set')}")
    print(f"DEBUG_MODE: {os.environ.get('DEBUG_MODE', 'not set')}")
    print(f"SAVE_TO_S3: {os.environ.get('SAVE_TO_S3', 'not set')}")
    
    start_time = time.time()
    
    # Load configuration
    config = Config()
    
    # Lambda環境かどうかを判定
    is_lambda = os.environ.get('AWS_LAMBDA_EXECUTION', '').lower() == 'true'
    
    if is_lambda:
        # Lambda環境では環境変数の設定を優先
        mock_mode_env = os.environ.get('MOCK_MODE', 'false').lower()
        debug_mode_env = os.environ.get('DEBUG_MODE', 'false').lower()
        config.mock_mode = mock_mode_env == 'true'
        config.debug_mode = debug_mode_env == 'true'
        config.save_to_s3 = True
    else:
        # 環境変数からモード設定を読み込む
        # MOCK_MODE: モックデータを使用するかどうか (true/false)
        # - true: APIからデータを取得せず、モックデータを使用
        # - false: 実際にAPIからデータを取得
        mock_mode_env = os.environ.get('MOCK_MODE', 'false').lower()
        
        # DEBUG_MODE: デバッグモードを有効にするかどうか (true/false)
        # - true: 詳細なログ出力、テスト通知の送信など
        # - false: 通常の動作
        debug_mode_env = os.environ.get('DEBUG_MODE', 'false').lower()
        
        # SAVE_TO_S3: S3にデータを保存するかどうか (true/false)
        # - true: S3にデータを保存
        # - false: ローカルファイルシステムにデータを保存
        save_to_s3_env = os.environ.get('SAVE_TO_S3', 'false').lower()
        
        config.mock_mode = mock_mode_env == 'true'
        config.debug_mode = debug_mode_env == 'true'
        config.save_to_s3 = save_to_s3_env == 'true'
        
        # 環境変数の設定をログに出力
        logger.debug(f"Environment variables:")
        logger.debug(f"MOCK_MODE: {os.environ.get('MOCK_MODE', 'not set')}")
        logger.debug(f"DEBUG_MODE: {os.environ.get('DEBUG_MODE', 'not set')}")
        logger.debug(f"SAVE_TO_S3: {os.environ.get('SAVE_TO_S3', 'not set')}")
        logger.debug(f"Parsed values:")
        logger.debug(f"mock_mode_env: {mock_mode_env}")
        logger.debug(f"debug_mode_env: {debug_mode_env}")
        logger.debug(f"save_to_s3_env: {save_to_s3_env}")
    
    # Set up components
    logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager, local_storage = setup_components(config)
    
    # env_typeの定義
    env_type = "Lambda" if is_lambda else "Local"
    if config.mock_mode:
        env_type += " (Mock)"
    
    # デバッグモードの場合のみSlack接続テスト
    if config.debug_mode and config.slack_enabled:
        logger.info("Slack接続テストを実行します...")
        try:
            # info用のWebhook URLを使用してテスト
            test_result = alert_manager.test_slack_connection(webhook_url=config.slack_webhook_url_info)
            if test_result:
                logger.info("✅ Slack接続テストに成功しました")
            else:
                logger.error("❌ Slack接続テストに失敗しました")
        except Exception as e:
            logger.error(f"❌ Slack接続テスト中にエラーが発生しました: {e}")
    
    # Log execution start
    logger.info("=" * 80)
    logger.info(f"🚀 Starting daily stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"📋 Configuration: {config}")
    logger.info(f"🔍 Environment STOCK_SYMBOLS: {os.getenv('STOCK_SYMBOLS')}")
    logger.info(f"🔍 Config stock_symbols: {config.stock_symbols}")
    logger.info(f"🔍 SAVE_TO_S3: {config.save_to_s3}")
    logger.info(f"🔍 LOCAL_STORAGE: {'Initialized' if local_storage else 'Not initialized'}")
    logger.info("=" * 80)
    
    # Process each symbol
    results = {}
    success_count = 0
    failure_count = 0
    latest_date = None  # 最新の日付を保持する変数
    symbol_dates = {}   # 各シンボルの日付を保持する辞書
    
    for symbol in config.stock_symbols:
        try:
            result = process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger, local_storage)
            
            if isinstance(result, tuple) and len(result) == 2:
                success, symbol_date = result
                # 各シンボルの日付を保存
                if success and symbol_date:
                    symbol_dates[symbol] = symbol_date
                    # 最新の日付を更新（初回のみ）
                    if not latest_date:
                        latest_date = symbol_date
            else:
                success = result
                symbol_date = None
                
            results[symbol] = "SUCCESS" if success else "FAILURE"
            
            if success:
                success_count += 1
            else:
                failure_count += 1
                
        except Exception as e:
            logger.exception(f"❌ Unexpected error processing {symbol}: {e}")
            results[symbol] = f"ERROR: {str(e)}"
            failure_count += 1
    
    # 最新の日付が取得できなかった場合のフォールバック
    if not latest_date:
        latest_date = datetime.now().strftime('%Y-%m-%d')
        logger.warning(f"最新の日付が取得できなかったため、現在の日付を使用します: {latest_date}")
    
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
    
    # 実行結果の通知
    if config.slack_enabled:
        try:
            # 実行環境情報を取得
            env_info = f"Environment: {env_type}"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # UTCとJSTのタイムスタンプを取得
            now_utc = datetime.utcnow()
            now_jst = datetime.now()
            timestamp_utc = now_utc.strftime("%Y-%m-%d %H:%M:%S")
            timestamp_jst = now_jst.strftime("%Y-%m-%d %H:%M:%S")
            
            # 共通のフィールド
            common_fields = [
                {"title": "Environment", "value": env_type, "short": True},
                {"title": "Execution Time", "value": f"{execution_time:.2f} seconds", "short": True},
                {"title": "Timestamp (UTC)", "value": timestamp_utc, "short": True},
                {"title": "Timestamp (JST)", "value": timestamp_jst, "short": True},
            ]
            
            # 結果に基づいて通知を送信
            if failure_count > 0:
                # 失敗したシンボルを抽出
                failed_symbols = [symbol for symbol, result in results.items() if result != "SUCCESS"]
                
                # 失敗情報を詳細に含める
                failure_fields = [
                    {"title": "Failed Symbols", "value": ", ".join(failed_symbols), "short": False},
                    {"title": "Success Count", "value": str(success_count), "short": True},
                    {"title": "Failure Count", "value": str(failure_count), "short": True}
                ]
                
                # 詳細な結果情報
                detailed_results = "\n".join([f"{symbol}: {result}" for symbol, result in results.items()])
                
                # 警告アラートを送信
                alert_message = f"⚠️ Daily stock data fetch completed with {failure_count} failures"
                alert_details = f"""
WARNING: Some stock data fetch operations failed.

Execution time: {execution_time:.2f} seconds
Environment: {env_type}
Successful: {success_count}
Failed: {failure_count}

Failed symbols: {', '.join(failed_symbols)}

Detailed results:
{detailed_results}
"""
                # ローカルに保存する場合は#local_testチャンネルに送信
                if not config.save_to_s3 and config.slack_webhook_url_local_test:
                    alert_manager.send_warning_alert(
                        alert_message,
                        alert_details,
                        source="fetch_daily.py",
                        send_email=config.email_enabled,
                        send_slack=True,
                        additional_fields=common_fields + failure_fields,
                        webhook_url=config.slack_webhook_url_local_test
                    )
                else:
                    alert_manager.send_warning_alert(
                        alert_message,
                        alert_details,
                        source="fetch_daily.py",
                        send_email=config.email_enabled,
                        send_slack=True,
                        additional_fields=common_fields + failure_fields
                    )
                logger.info("✅ 警告通知を送信しました")
            else:
                # 成功したシンボルを抽出
                successful_symbols = [symbol for symbol, result in results.items() if result == "SUCCESS"]
                
                # データサイズの計算とファイルパス情報の収集（ローカルの場合）
                data_size = 0
                data_sizes = {}
                local_file_paths = []
                
                if not config.save_to_s3 and local_storage:
                    try:
                        for symbol in successful_symbols:
                            # 日次データのサイズとパス
                            daily_path = os.path.join(config.local_storage_dir, f"daily/{symbol}/{latest_date}.json")
                            if os.path.exists(daily_path):
                                daily_size = os.path.getsize(daily_path) / 1024  # KB
                                if 'daily' not in data_sizes:
                                    data_sizes['daily'] = 0
                                data_sizes['daily'] += daily_size
                                data_size += daily_size
                                local_file_paths.append(f"- 日次データ: {daily_path}")
                            
                            # 最新データのサイズとパス
                            latest_path = os.path.join(config.local_storage_dir, f"{symbol}/latest.json")
                            if os.path.exists(latest_path):
                                latest_size = os.path.getsize(latest_path) / 1024  # KB
                                if 'latest' not in data_sizes:
                                    data_sizes['latest'] = 0
                                data_sizes['latest'] += latest_size
                                data_size += latest_size
                                local_file_paths.append(f"- 最新データ: {latest_path}")
                            
                            # 全期間データのサイズとパス
                            full_path = os.path.join(config.local_storage_dir, f"{symbol}/full.json")
                            if os.path.exists(full_path):
                                full_size = os.path.getsize(full_path) / 1024  # KB
                                if 'full' not in data_sizes:
                                    data_sizes['full'] = 0
                                data_sizes['full'] += full_size
                                data_size += full_size
                                local_file_paths.append(f"- 全期間データ: {full_path}")
                            
                            # メタデータのサイズとパス
                            metadata_path = os.path.join(config.local_storage_dir, f"{symbol}/metadata.json")
                            if os.path.exists(metadata_path):
                                metadata_size = os.path.getsize(metadata_path) / 1024  # KB
                                if 'metadata' not in data_sizes:
                                    data_sizes['metadata'] = 0
                                data_sizes['metadata'] += metadata_size
                                data_size += metadata_size
                                local_file_paths.append(f"- メタデータ: {metadata_path}")
                    except Exception as e:
                        logger.warning(f"データサイズの計算中にエラーが発生しました: {e}")
                
                # 成功情報を詳細に含める
                success_fields = [
                    {"title": "Successful Symbols", "value": ", ".join(successful_symbols), "short": False},
                    {"title": "Total Successful", "value": str(success_count), "short": True},
                    {"title": "Data Date", "value": latest_date, "short": True}
                ]
                
                # ローカルの場合はローカルファイルパス情報を追加
                if not config.save_to_s3 and local_storage and local_file_paths:
                    local_paths_info = "\n".join(local_file_paths)
                    success_fields.append({"title": "Local Storage Paths", "value": local_paths_info, "short": False})
                
                # S3の場合はS3パス情報を追加
                if config.save_to_s3:
                    s3_paths_info = f"""各シンボルにつき以下の4種類のファイルを更新しました：
- 日次データ: .../daily/{latest_date.split('-')[0]}/{latest_date.split('-')[1]}/{latest_date.split('-')[2]}.json
- 最新データ: .../latest.json
- 全期間データ: .../full.json
- メタデータ: .../metadata.json"""
                    
                    # S3パス例を追加
                    for symbol in successful_symbols:
                        s3_path_example = f"{symbol}: s3://{config.s3_bucket}/{config.s3_prefix}/stock/raw/{symbol}/daily/{latest_date.split('-')[0]}/{latest_date.split('-')[1]}/{latest_date.split('-')[2]}.json"
                        s3_paths_info += f"\n\n{s3_path_example}"
                    
                    success_fields.append({"title": "S3 Storage Paths", "value": s3_paths_info, "short": False})
                
                # UTCとJSTのタイムスタンプを取得
                now_utc = datetime.utcnow()
                now_jst = datetime.now()
                timestamp_utc = now_utc.strftime("%Y-%m-%d %H:%M:%S")
                timestamp_jst = now_jst.strftime("%Y-%m-%d %H:%M:%S")
                
                # 環境情報を含むメッセージ
                env_prefix = "Lambda: " if is_lambda else "Local: "
                alert_message = f"✅ {env_prefix}Daily stock data fetch completed successfully for all {success_count} symbols"
                
                # 詳細情報
                alert_details = f"""
INFO: Stock data fetch summary.

Execution time: {execution_time:.2f} seconds
Environment: {env_type}
Data date: {latest_date}
Successful symbols: {', '.join(successful_symbols)}
Total successful: {success_count}
"""
                
                # データサイズ情報を追加（ローカルの場合）
                if not config.save_to_s3 and data_size > 0:
                    alert_details += f"Total data size: {data_size:.2f} KB\n"
                    
                    # ファイル別サイズ情報
                    if data_sizes:
                        alert_details += "\nファイル別サイズ:\n"
                        for file_type, size in data_sizes.items():
                            alert_details += f" • {file_type}データ: {size:.2f} KB\n"
                # ローカルに保存する場合は#local_testチャンネルに送信
                if not config.save_to_s3 and config.slack_webhook_url_local_test:
                    alert_manager.send_success_alert(
                        alert_message,
                        alert_details,
                        source="fetch_daily.py",
                        send_email=config.email_enabled,
                        send_slack=True,
                        additional_fields=common_fields + success_fields,
                        webhook_url=config.slack_webhook_url_local_test
                    )
                else:
                    alert_manager.send_success_alert(
                        alert_message,
                        alert_details,
                        source="fetch_daily.py",
                        send_email=config.email_enabled,
                        send_slack=True,
                        additional_fields=common_fields + success_fields
                    )
                logger.info("✅ 成功通知を送信しました")
        except Exception as e:
            logger.error(f"❌ Slack通知処理中にエラーが発生しました: {e}")
    else:
        logger.info("Slack通知は無効化されています")
    
    # Return exit code
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Catch any unexpected exceptions
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)
