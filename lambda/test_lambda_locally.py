#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

# テスト用のコンテキストクラス
class LambdaContext:
    def __init__(self):
        self.function_name = "FetchDailyLambda"
        self.function_version = "$LATEST"
        self.aws_request_id = "test-request-id"
        self.memory_limit_in_mb = 256
        self.log_group_name = "/aws/lambda/FetchDailyLambda"
        self.log_stream_name = f"test-stream-{datetime.now().strftime('%Y/%m/%d')}"
        self.invoked_function_arn = "arn:aws:lambda:ap-northeast-1:123456789012:function:FetchDailyLambda"
        self.remaining_time_in_millis = 300000  # 5分

# テスト用のイベントを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
test_event_path = os.path.join(script_dir, 'test_event.json')
with open(test_event_path, 'r') as f:
    event = json.load(f)

# Lambda関数のハンドラーをインポート
sys.path.insert(0, './package')  # パッケージディレクトリをパスに追加
sys.path.insert(0, '.')  # カレントディレクトリをパスに追加
from fetch_daily_lambda import handler

# Lambda関数を実行
print("Lambda関数を実行中...")
result = handler(event, LambdaContext())

# 結果を表示
print("\n--- 実行結果 ---")
print(json.dumps(result, indent=2, ensure_ascii=False))
