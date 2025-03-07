import os
import sys
import json
import boto3
import logging
from datetime import datetime

# Lambda関数のログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数の設定
os.environ['MOCK_MODE'] = 'False'  # 本番モード
os.environ['SAVE_TO_S3'] = 'True'  # S3に保存する
os.environ['SLACK_ENABLED'] = 'True'  # Slack通知を有効化

def lambda_handler(event, context):
    """
    Lambda関数のハンドラー
    
    Args:
        event: Lambda関数のイベント
        context: Lambda関数のコンテキスト
        
    Returns:
        Lambda関数の実行結果
    """
    logger.info(f"Lambda function started at {datetime.now().isoformat()}")
    logger.info(f"Event: {json.dumps(event)}")
    
    # Slack Webhook URLsを環境変数から取得
    slack_webhook_url_error = os.environ.get('SLACK_WEBHOOK_URL_ERROR')
    slack_webhook_url_warning = os.environ.get('SLACK_WEBHOOK_URL_WARNING')
    slack_webhook_url_info = os.environ.get('SLACK_WEBHOOK_URL_INFO')
    
    # 環境変数にSlack Webhook URLsが設定されていることを確認
    if not (slack_webhook_url_error and slack_webhook_url_warning and slack_webhook_url_info):
        logger.warning("Slack Webhook URLs are not properly configured in environment variables")
    else:
        logger.info("Slack Webhook URLs are configured")
    
    try:
        # Lambda関数のパッケージをインポートパスに追加
        sys.path.append('/var/task')
        
        # fetch_daily.pyをインポート
        from fetch_daily import main
        
        # fetch_daily.pyのmain関数を実行
        result = main()
        
        # 実行結果をログに出力
        logger.info(f"fetch_daily.py execution completed with result: {result}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'fetch_daily.py execution completed successfully',
                'result': result
            })
        }
    except Exception as e:
        logger.error(f"Error executing fetch_daily.py: {str(e)}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(error_traceback)
        
        # エラー情報をより詳細に含める
        error_details = {
            'error_message': str(e),
            'error_type': type(e).__name__,
            'traceback': error_traceback,
            'lambda_function_name': context.function_name,
            'lambda_function_version': context.function_version,
            'lambda_request_id': context.aws_request_id,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error executing fetch_daily.py',
                'error': str(e),
                'error_details': error_details
            })
        }
