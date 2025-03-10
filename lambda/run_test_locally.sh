#!/bin/bash

# ローカルテスト用の環境変数を設定
export ALPHA_VANTAGE_API_KEY="demo"
export S3_BUCKET="local_data"
export REGION="ap-northeast-1"
export STOCK_SYMBOLS="NVDA,AAPL,MSFT"
export MOCK_MODE="false"
export DEBUG_MODE="true"
export SLACK_ENABLED="false"

# 現在のディレクトリをLambdaディレクトリに変更
cd "$(dirname "$0")"

# Lambda関数をローカルでテスト実行
python test_lambda_locally.py

# 環境変数をクリア
unset ALPHA_VANTAGE_API_KEY
unset S3_BUCKET
unset REGION
unset STOCK_SYMBOLS
unset MOCK_MODE
unset DEBUG_MODE
unset SLACK_ENABLED
