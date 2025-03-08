import os
import sys
import json
import logging
import traceback
from datetime import datetime

# Lambda関数のログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# デバッグ情報を出力
logger.info("=" * 80)
logger.info("Lambda関数の初期化を開始します")
logger.info(f"Python バージョン: {sys.version}")
logger.info(f"sys.path: {json.dumps(sys.path)}")
logger.info(f"環境変数: {json.dumps({k: v for k, v in os.environ.items() if not k.startswith('AWS')})}")
logger.info("=" * 80)

# 環境変数の設定（既存の環境変数を上書きしない）
if 'MOCK_MODE' not in os.environ:
    os.environ['MOCK_MODE'] = 'False'  # 本番モード
if 'SAVE_TO_S3' not in os.environ:
    os.environ['SAVE_TO_S3'] = 'True'  # S3に保存する
os.environ['AWS_LAMBDA_EXECUTION'] = 'true'  # Lambda環境フラグは常に設定

# Slack通知は無効化し、代わりにCloudWatch Logsに詳細なログを出力
os.environ['SLACK_ENABLED'] = 'False'

# モジュールのインポートを試みる
logger.info("モジュールのインポートを試みます...")
try:
    logger.info("src.fetch_daily からのインポートを試みます...")
    from src.fetch_daily import main
    logger.info("✅ src.fetch_daily からのインポートに成功しました")
except ImportError as e:
    logger.error(f"❌ src.fetch_daily からのインポートに失敗しました: {e}")
    logger.info("フォールバックパスを追加します...")
    
    # Lambda パッケージ環境用のフォールバック
    sys.path.append('/opt/python')  # Lambda Layerのパス
    sys.path.append('/var/task')    # Lambda関数のルートパス
    
    try:
        logger.info("fetch_daily からのインポートを試みます...")
        from fetch_daily import main
        logger.info("✅ fetch_daily からのインポートに成功しました")
    except ImportError as e:
        logger.error(f"❌ fetch_daily からのインポートに失敗しました: {e}")
        
        # ディレクトリ内のファイルを確認
        logger.info("ディレクトリ内のファイルを確認します...")
        try:
            import os
            for path in ['/var/task', '.']:
                logger.info(f"ディレクトリ {path} の内容:")
                for root, dirs, files in os.walk(path):
                    logger.info(f"  {root}: {files}")
        except Exception as e:
            logger.error(f"ディレクトリ確認中にエラーが発生しました: {e}")
        
        # エラーを再発生させる
        raise

def handler(event, context):
    """
    AWS Lambda handler for daily stock data fetch.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Dictionary with execution status and details
    """
    # Lambda実行情報をログに出力
    logger.info("=" * 80)
    logger.info(f"Lambda関数の実行を開始します: {datetime.now().isoformat()}")
    logger.info(f"Lambda function: {context.function_name}, version: {context.function_version}")
    logger.info(f"Request ID: {context.aws_request_id}")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 80)
    
    # Lambda実行情報を環境変数に設定
    os.environ['LAMBDA_FUNCTION_NAME'] = context.function_name
    os.environ['LAMBDA_FUNCTION_VERSION'] = context.function_version
    os.environ['LAMBDA_REQUEST_ID'] = context.aws_request_id
    
    # 開始ログ
    logger.info(f"🚀 Lambda関数 {context.function_name} (v{context.function_version}) が開始されました。Request ID: {context.aws_request_id}")
    
    # メイン処理
    exit_code = 1  # デフォルトはエラー
    error_message = None
    error_traceback = None
    
    try:
        # main関数の実行前にログ
        logger.info("main関数を実行します...")
        
        # Execute the main function
        exit_code = main()
        
        # main関数の実行後にログ
        logger.info(f"main関数の実行が完了しました。Exit Code: {exit_code}")
        
        # 完了ログ
        if exit_code == 0:
            logger.info(f"✅ Lambda関数 {context.function_name} が正常に完了しました。")
        else:
            logger.warning(f"⚠️ Lambda関数 {context.function_name} が警告付きで完了しました。Exit Code: {exit_code}")
        
        # 正常終了レスポンス
        return {
            'statusCode': 200 if exit_code == 0 else 500,
            'body': {
                'message': 'Stock data fetch completed successfully' if exit_code == 0 else 'Stock data fetch failed',
                'exitCode': exit_code,
                'function': context.function_name,
                'version': context.function_version,
                'requestId': context.aws_request_id
            }
        }
        
    except Exception as e:
        # エラー情報を取得
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        # エラーの詳細情報をログに出力
        logger.error("=" * 80)
        logger.error(f"❌ Lambda関数でエラーが発生しました: {error_message}")
        logger.error(f"エラータイプ: {type(e).__name__}")
        logger.error(f"スタックトレース:\n{error_traceback}")
        
        # エラーの詳細な分析
        logger.error("エラーの詳細な分析:")
        
        # モジュールのインポートエラーの場合
        if isinstance(e, ImportError):
            logger.error(f"インポートエラー: {error_message}")
            logger.error(f"sys.path: {json.dumps(sys.path)}")
            
            # ディレクトリ内のファイルを確認
            try:
                for path in ['/var/task', '.']:
                    logger.error(f"ディレクトリ {path} の内容:")
                    for root, dirs, files in os.walk(path):
                        logger.error(f"  {root}: {files}")
            except Exception as dir_error:
                logger.error(f"ディレクトリ確認中にエラーが発生しました: {dir_error}")
        
        # 属性エラーの場合
        elif isinstance(e, AttributeError):
            logger.error(f"属性エラー: {error_message}")
            # オブジェクトの属性を確認
            if hasattr(e, '__dict__'):
                logger.error(f"オブジェクト属性: {json.dumps(e.__dict__, default=str)}")
        
        logger.error("=" * 80)
        
        # エラー情報をより詳細に含める
        error_details = {
            'error_message': error_message,
            'error_type': type(e).__name__,
            'traceback': error_traceback,
            'lambda_function_name': context.function_name,
            'lambda_function_version': context.function_version,
            'lambda_request_id': context.aws_request_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # エラー終了レスポンス
        return {
            'statusCode': 500,
            'body': {
                'message': f'Error executing stock data fetch: {error_message}',
                'error': error_message,
                'error_details': error_details
            }
        }
