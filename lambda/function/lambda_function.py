#!/usr/bin/env python3
"""
AWS Lambda Function for Daily Stock Data Fetching

This Lambda function fetches the latest daily stock data from Alpha Vantage API
and stores it in AWS S3. It is designed to be triggered on a schedule.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
import traceback

# タイムゾーン処理用
try:
    # Python 3.9以降の標準ライブラリ
    from zoneinfo import ZoneInfo
    def get_jst_time():
        return datetime.now(ZoneInfo("Asia/Tokyo"))
except ImportError:
    # Python 3.9未満またはzoneinfo非対応環境用
    try:
        import pytz
        def get_jst_time():
            return datetime.now(pytz.timezone('Asia/Tokyo'))
    except ImportError:
        # pytzも利用できない場合は、UTCに9時間を加算
        def get_jst_time():
            return datetime.now() + timedelta(hours=9)

# Lambda環境変数を設定
os.environ['AWS_LAMBDA_EXECUTION'] = 'true'

# ロガー初期化
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# srcディレクトリをインポートパスに追加
sys.path.append('.')
sys.path.append('/var/task')  # Lambda環境でのルートディレクトリ

# 依存関係のインポートを遅延させる（Lambda実行時に必要なものだけをインポート）
try:
    from utils.alerts import AlertManager
except ImportError:
    # Lambda環境では直接インポートを試みる
    try:
        from alerts import AlertManager
    except ImportError:
        logger.error("AlertManagerのインポートに失敗しました")

def setup_logging():
    """
    Set up logging configuration.
    
    Returns:
        Logger object
    """
    # ロガー初期化
    logger = logging.getLogger(__name__)
    
    # Lambda環境ではログディレクトリを/tmp以下に設定
    log_dir = '/tmp/logs'
    
    # ログディレクトリが存在しない場合は作成
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"ログディレクトリを作成しました: {log_dir}")
    except Exception as e:
        logger.error(f"ログディレクトリの作成に失敗しました: {e}")
        logger.error(traceback.format_exc())
    
    # ハンドラーを設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # フォーマッターを設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # ロガーにハンドラーを追加
    logger.addHandler(console_handler)
    
    return logger

def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Dictionary with execution results
    """
    start_time = time.time()
    
    # ロギングの設定
    logger = setup_logging()
    
    # 環境変数を取得
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')
    s3_bucket = os.environ.get('S3_BUCKET', 'Not set')
    region = os.environ.get('REGION', 'ap-northeast-1')
    stock_symbols = os.environ.get('STOCK_SYMBOLS', 'NVDA,AAPL,MSFT')
    mock_mode = os.environ.get('MOCK_MODE', 'false').lower() == 'true'
    debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
    
    # Slack通知の設定を取得
    slack_enabled = os.environ.get('SLACK_ENABLED', 'false').lower() == 'true'
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL', '')
    slack_webhook_url_error = os.environ.get('SLACK_WEBHOOK_URL_ERROR', slack_webhook_url)
    slack_webhook_url_warning = os.environ.get('SLACK_WEBHOOK_URL_WARNING', slack_webhook_url)
    slack_webhook_url_info = os.environ.get('SLACK_WEBHOOK_URL_INFO', slack_webhook_url)
    
    # AlertManagerの初期化
    alert_manager = None
    if slack_enabled:
        try:
            alert_manager = AlertManager(
                None,  # email_config
                slack_webhook_url,
                slack_webhook_url_error,
                slack_webhook_url_warning,
                slack_webhook_url_info
            )
            alert_manager.set_logger(logger)
            logger.info("AlertManagerを初期化しました")
            
            # デバッグモードの場合はSlack設定の詳細をログに出力
            if debug_mode:
                logger.debug("=" * 80)
                logger.debug("Slack設定の詳細:")
                logger.debug(f"slack_enabled: {slack_enabled}")
                logger.debug(f"slack_webhook_url: {slack_webhook_url}")
                logger.debug(f"slack_webhook_url_error: {slack_webhook_url_error}")
                logger.debug(f"slack_webhook_url_warning: {slack_webhook_url_warning}")
                logger.debug(f"slack_webhook_url_info: {slack_webhook_url_info}")
                logger.debug("=" * 80)
        except Exception as e:
            logger.error(f"AlertManagerの初期化に失敗しました: {e}")
            logger.error(traceback.format_exc())
    
    # 実行モードを設定
    env_type = "Lambda"
    if mock_mode:
        env_type += " (Mock)"
    
    # 実行開始ログ
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Lambda function for daily stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"🔧 Environment: {env_type}")
    logger.info(f"🔑 API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'}")
    logger.info(f"🪣 S3 Bucket: {s3_bucket}")
    logger.info(f"🌐 Region: {region}")
    logger.info(f"📊 Stock Symbols: {stock_symbols}")
    logger.info(f"🐛 Debug Mode: {debug_mode}")
    logger.info("=" * 80)
    
    try:
        # モックモードの場合はダミーデータを返す
        if mock_mode:
            logger.info("モックモードで実行中です。ダミーデータを返します。")
            
            # 実行時間を計算
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'execution_time': f"{execution_time:.2f} seconds",
                    'message': 'Mock mode execution successful',
                    'data': {
                        'symbols': stock_symbols.split(','),
                        'timestamp': datetime.now().isoformat()
                    }
                })
            }
        
        # 実際のデータ取得処理
        logger.info("Alpha Vantage APIからデータを取得します...")
        
        # ここで実際のデータ取得処理を行う
        # 注意: 依存関係のインポートはここで行う
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # S3クライアントを初期化
            s3_client = boto3.client('s3', region_name=region)
            
            # 株式シンボルのリスト
            symbols = stock_symbols.split(',')
            
            # 各シンボルに対して処理を実行
            results = {}
            error_details = {}  # エラーの詳細を記録する辞書
            for symbol in symbols:
                logger.info(f"シンボル {symbol} の処理を開始します...")
                
                # Alpha Vantage APIからデータを取得
                try:
                    import requests
                    
                    # APIリクエストURLを構築
                    base_url = "https://www.alphavantage.co/query"
                    params = {
                        "function": "TIME_SERIES_DAILY",
                        "symbol": symbol,
                        "apikey": api_key,
                        "outputsize": "compact"  # 最新の100件のデータを取得
                    }
                    
                    # APIリクエストを送信
                    logger.info(f"Alpha Vantage APIにリクエストを送信します: {base_url}?function={params['function']}&symbol={params['symbol']}&outputsize={params['outputsize']}")
                    response = requests.get(base_url, params=params)
                    
                    # レスポンスを確認
                    if response.status_code != 200:
                        error_msg = f"APIリクエストが失敗しました: ステータスコード {response.status_code}"
                        logger.error(error_msg)
                        logger.error(f"レスポンス: {response.text}")
                        results[symbol] = 'error'
                        error_details[symbol] = {
                            'error_type': 'API Request Error',
                            'status_code': response.status_code,
                            'message': error_msg,
                            'response': response.text[:200] + '...' if len(response.text) > 200 else response.text
                        }
                        continue
                    
                    # JSONデータを解析
                    data = response.json()
                    
                    # エラーチェック
                    if "Error Message" in data:
                        error_msg = f"APIエラー: {data['Error Message']}"
                        logger.error(error_msg)
                        results[symbol] = 'error'
                        error_details[symbol] = {
                            'error_type': 'API Error',
                            'message': error_msg,
                            'api_error': data['Error Message']
                        }
                        continue
                    
                    if "Time Series (Daily)" not in data:
                        error_msg = f"予期しないAPIレスポンス形式"
                        logger.error(f"{error_msg}: {data}")
                        results[symbol] = 'error'
                        error_details[symbol] = {
                            'error_type': 'Unexpected Response Format',
                            'message': error_msg,
                            'response_keys': list(data.keys())
                        }
                        continue
                    
                    # 最新の日付のデータを取得
                    time_series = data["Time Series (Daily)"]
                    latest_date = list(time_series.keys())[0]  # 最初のキーが最新の日付
                    latest_data = time_series[latest_date]
                    
                    # 必要なデータを抽出
                    stock_data = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'date': latest_date,
                        'open': float(latest_data['1. open']),
                        'high': float(latest_data['2. high']),
                        'low': float(latest_data['3. low']),
                        'close': float(latest_data['4. close']),
                        'volume': int(latest_data['5. volume'])
                    }
                    
                    logger.info(f"データを取得しました: {symbol} ({latest_date})")
                    
                except Exception as e:
                    error_msg = f"データ取得中にエラーが発生しました: {e}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    results[symbol] = 'error'
                    error_details[symbol] = {
                        'error_type': 'Data Fetch Error',
                        'message': error_msg,
                        'symbol': symbol,
                        'error': str(e)
                    }
                    continue
                
                # S3にデータを保存
                try:
                    s3_key = f"daily/{symbol}/{latest_date}.json"
                    s3_client.put_object(
                        Bucket=s3_bucket,
                        Key=s3_key,
                        Body=json.dumps(stock_data),
                        ContentType='application/json'
                    )
                    logger.info(f"データをS3に保存しました: s3://{s3_bucket}/{s3_key}")
                    results[symbol] = 'success'
                except ClientError as e:
                    error_msg = f"S3へのデータ保存に失敗しました: {e}"
                    logger.error(error_msg)
                    results[symbol] = 'error'
                    error_details[symbol] = {
                        'error_type': 'S3 Storage Error',
                        'message': error_msg,
                        's3_bucket': s3_bucket,
                        's3_key': s3_key,
                        'error': str(e)
                    }
                except Exception as e:
                    error_msg = f"S3へのデータ保存中に予期しないエラーが発生しました: {e}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    results[symbol] = 'error'
                    error_details[symbol] = {
                        'error_type': 'Unexpected S3 Error',
                        'message': error_msg,
                        'error': str(e)
                    }
            
            # 実行時間を計算
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 結果を集計
            success_count = sum(1 for result in results.values() if result == 'success')
            failure_count = sum(1 for result in results.values() if result != 'success')
            
            # Slack通知を送信
            if slack_enabled and alert_manager:
                try:
                    # 実行環境情報を取得
                    env_info = f"Environment: {env_type}"
                    utc_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    jst_timestamp = get_jst_time().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 共通のフィールド
                    common_fields = [
                        {"title": "Environment", "value": env_type, "short": True},
                        {"title": "Execution Time", "value": f"{execution_time:.2f} seconds", "short": True},
                        {"title": "Timestamp (UTC)", "value": utc_timestamp, "short": True},
                        {"title": "Timestamp (JST)", "value": jst_timestamp, "short": True},
                    ]
                    
                    # 結果に基づいて通知を送信
                    if failure_count > 0:
                        # 失敗したシンボルを抽出
                        failed_symbols = [symbol for symbol, result in results.items() if result != 'success']
                        
                        # 失敗情報を詳細に含める
                        failure_fields = [
                            {"title": "Failed Symbols", "value": ", ".join(failed_symbols), "short": False},
                            {"title": "Success Count", "value": str(success_count), "short": True},
                            {"title": "Failure Count", "value": str(failure_count), "short": True}
                        ]
                        
                        # エラーの詳細情報を追加
                        for symbol in failed_symbols:
                            if symbol in error_details:
                                error_info = error_details[symbol]
                                failure_fields.append({
                                    "title": f"Error Details for {symbol}",
                                    "value": f"Type: {error_info.get('error_type', 'Unknown')}\nMessage: {error_info.get('message', 'No message')}",
                                    "short": False
                                })
                        
                        # 詳細な結果情報
                        detailed_results = "\n".join([f"{symbol}: {result}" for symbol, result in results.items()])
                        
                        # 警告アラートを送信
                        alert_message = f"⚠️ Lambda: Daily stock data fetch completed with {failure_count} failures"
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
                        alert_manager.send_warning_alert(
                            alert_message,
                            alert_details,
                            source="lambda_function.py",
                            send_email=False,
                            send_slack=True,
                            additional_fields=common_fields + failure_fields
                        )
                        logger.info("✅ 警告通知を送信しました")
                    else:
                        # 成功したシンボルを抽出
                        successful_symbols = [symbol for symbol, result in results.items() if result == 'success']
                        
                        # 成功情報を詳細に含める
                        success_fields = [
                            {"title": "Successful Symbols", "value": ", ".join(successful_symbols), "short": False},
                            {"title": "Total Successful", "value": str(success_count), "short": True}
                        ]
                        
                        # 成功アラートを送信
                        alert_message = f"✅ Lambda: Daily stock data fetch completed successfully for all {success_count} symbols"
                        alert_details = f"""
INFO: Stock data fetch summary.

Execution time: {execution_time:.2f} seconds
Environment: {env_type}
Successful symbols: {', '.join(successful_symbols)}
Total successful: {success_count}
"""
                        alert_manager.send_success_alert(
                            alert_message,
                            alert_details,
                            source="lambda_function.py",
                            send_email=False,
                            send_slack=True,
                            additional_fields=common_fields + success_fields
                        )
                        logger.info("✅ 成功通知を送信しました")
                except Exception as e:
                    logger.error(f"❌ Slack通知処理中にエラーが発生しました: {e}")
                    logger.error(traceback.format_exc())
            elif slack_enabled:
                logger.warning("AlertManagerが初期化されていないため、Slack通知を送信できません")
            else:
                logger.info("Slack通知は無効化されています")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'execution_time': f"{execution_time:.2f} seconds",
                    'results': results,
                    'success_count': success_count,
                    'failure_count': failure_count
                })
            }
        except ImportError as e:
            logger.error(f"依存関係のインポートに失敗しました: {e}")
            logger.error(traceback.format_exc())
            raise
    except Exception as e:
        # エラーが発生した場合
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.error(f"❌ Lambda関数でエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        
        # エラー通知をSlackに送信
        if slack_enabled and alert_manager:
            try:
                # 実行環境情報を取得
                env_info = f"Environment: {env_type}"
                utc_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                jst_timestamp = get_jst_time().strftime("%Y-%m-%d %H:%M:%S")
                
                # エラー情報を詳細に含める
                error_fields = [
                    {"title": "Environment", "value": env_type, "short": True},
                    {"title": "Execution Time", "value": f"{execution_time:.2f} seconds", "short": True},
                    {"title": "Timestamp (UTC)", "value": utc_timestamp, "short": True},
                    {"title": "Timestamp (JST)", "value": jst_timestamp, "short": True},
                    {"title": "Error", "value": str(e), "short": False}
                ]
                
                # エラーアラートを送信
                alert_message = f"❌ Lambda: Daily stock data fetch failed with error"
                alert_details = f"""
ERROR: Lambda function execution failed.

Execution time: {execution_time:.2f} seconds
Environment: {env_type}
Error: {str(e)}

Stack trace:
{traceback.format_exc()}
"""
                alert_manager.send_error_alert(
                    alert_message,
                    alert_details,
                    source="lambda_function.py",
                    send_email=False,
                    send_slack=True,
                    additional_fields=error_fields
                )
                logger.info("✅ エラー通知を送信しました")
            except Exception as notify_error:
                logger.error(f"❌ Slack通知処理中にエラーが発生しました: {notify_error}")
                logger.error(traceback.format_exc())
        
        # Lambda関数の戻り値（エラー）
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'execution_time': f"{execution_time:.2f} seconds",
                'error': str(e)
            })
        }

# ローカルテスト用
if __name__ == "__main__":
    try:
        # テスト用のイベントとコンテキスト
        test_event = {}
        test_context = None
        
        # Lambda関数を実行
        result = lambda_handler(test_event, test_context)
        print(f"Lambda function result: {json.dumps(result, indent=2)}")
    except Exception as e:
        # Catch any unexpected exceptions
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)
