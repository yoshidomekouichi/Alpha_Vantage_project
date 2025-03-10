#!/bin/bash

# SAMを使用してローカルでLambda関数をテスト実行するスクリプト

# 現在のディレクトリをスクリプトのディレクトリに変更
cd "$(dirname "$0")"

# 環境変数を設定
export ALPHA_VANTAGE_API_KEY="demo"
export S3_BUCKET="mock-bucket"
export REGION="ap-northeast-1"
export STOCK_SYMBOLS="NVDA,AAPL,MSFT"
export MOCK_MODE="true"
export DEBUG_MODE="true"
export SLACK_ENABLED="false"

echo "SAMを使用してLambda関数をローカルで実行します..."
echo "環境変数:"
echo "  ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}"
echo "  S3_BUCKET: ${S3_BUCKET}"
echo "  REGION: ${REGION}"
echo "  STOCK_SYMBOLS: ${STOCK_SYMBOLS}"
echo "  MOCK_MODE: ${MOCK_MODE}"
echo "  DEBUG_MODE: ${DEBUG_MODE}"
echo "  SLACK_ENABLED: ${SLACK_ENABLED}"
echo ""

# SAMを使用してLambda関数をローカルで実行
sam local invoke StockDataFetchFunction --event events/test-event.json --env-vars env.json

# 環境変数をクリア
unset ALPHA_VANTAGE_API_KEY
unset S3_BUCKET
unset REGION
unset STOCK_SYMBOLS
unset MOCK_MODE
unset DEBUG_MODE
unset SLACK_ENABLED
