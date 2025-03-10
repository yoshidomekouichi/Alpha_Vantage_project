#!/usr/bin/env python3
"""
Minimal AWS Lambda Function

This is a minimal Lambda function that outputs environment variables
and returns a simple response.
"""

import os
import json
import logging
from datetime import datetime

# ロガー初期化
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def test(event, context):
    """
    Simple test Lambda handler function.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Dictionary with execution results
    """
    # 開始時間を記録
    start_time = datetime.now()
    
    # 環境変数を取得
    # AWS_REGIONは予約語なのでLambdaの環境変数では使用できない
    # 代わりにLambdaが自動的に設定するAWS_REGIONを使用
    aws_region = os.environ.get('AWS_REGION', 'Not set')
    s3_bucket = os.environ.get('S3_BUCKET', 'Not set')
    environment = os.environ.get('ENVIRONMENT', 'Not set')
    debug_mode = os.environ.get('DEBUG_MODE', 'false')
    
    # ログ出力
    logger.info("=" * 50)
    logger.info(f"🚀 Starting Lambda function at {start_time.isoformat()}")
    logger.info(f"🔧 AWS Region: {aws_region}")
    logger.info(f"🪣 S3 Bucket: {s3_bucket}")
    logger.info(f"🌍 Environment: {environment}")
    logger.info(f"🐛 Debug Mode: {debug_mode}")
    logger.info("=" * 50)
    
    # イベント情報をログに出力
    logger.info(f"📥 Received event: {json.dumps(event)}")
    
    # コンテキスト情報をログに出力（存在する場合）
    if context:
        logger.info(f"⏱️ Function time remaining: {context.get_remaining_time_in_millis()}ms")
        logger.info(f"🔑 Function name: {context.function_name}")
        logger.info(f"📝 Function version: {context.function_version}")
    
    # 終了時間を記録
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    
    # レスポンスを作成
    response = {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Lambda function executed successfully',
            'timestamp': end_time.isoformat(),
            'execution_time': f"{execution_time:.2f} seconds",
            'environment_info': {
                'aws_region': aws_region,
                's3_bucket': s3_bucket,
                'environment': environment,
                'debug_mode': debug_mode
            }
        })
    }
    
    logger.info(f"📤 Response: {json.dumps(response)}")
    logger.info(f"✅ Lambda function completed in {execution_time:.2f} seconds")
    
    return response

# Lambda handler
def lambda_handler(event, context):
    """
    AWS Lambda handler function that calls the test function.
    """
    return test(event, context)

# ローカルテスト用
if __name__ == "__main__":
    # テスト用のイベントとコンテキスト
    test_event = {"test": "event"}
    test_context = None
    
    # Lambda関数を実行
    result = lambda_handler(test_event, test_context)
    print(f"Lambda function result: {json.dumps(result, indent=2)}")
