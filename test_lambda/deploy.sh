#!/bin/bash
# 最小構成のLambda関数デプロイパッケージを作成するスクリプト

set -e  # エラーが発生したら停止

# 作業ディレクトリを設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

echo "===== 最小構成Lambda デプロイパッケージの作成を開始します ====="

# デプロイ用の一時ディレクトリを作成
DEPLOY_DIR="$SCRIPT_DIR/deploy"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Lambda関数のコードをコピー
echo "Lambda関数のコードをコピーしています..."
cp -r "$SCRIPT_DIR/function/lambda_function.py" "$DEPLOY_DIR/"

# Lambda関数のZIPパッケージを作成
echo "Lambda関数のZIPパッケージを作成しています..."
cd "$DEPLOY_DIR"
zip -r "$SCRIPT_DIR/function.zip" .
cd "$SCRIPT_DIR"

echo "Lambda関数のZIPパッケージを作成しました: $SCRIPT_DIR/function.zip"

# 一時ディレクトリを削除
rm -rf "$DEPLOY_DIR"

echo "===== デプロイパッケージの作成が完了しました ====="
echo "Lambda関数: $SCRIPT_DIR/function.zip"

# 環境変数の設定
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "環境変数ファイル(.env)が見つかりました。環境変数を読み込みます..."
    # 環境変数を読み込む
    ENV_VARS=$(grep -v '^#' "$ENV_FILE" | grep '=' | sed 's/^/      /' | sed 's/=/=/' | sed 's/$/,/' | tr '\n' ' ' | sed 's/,$//')
    
    # 最後のカンマを削除
    ENV_VARS=${ENV_VARS%,}
    
    # Lambda関数用の環境変数設定
    LAMBDA_ENV_VARS="{\"Variables\":{$ENV_VARS}}"
    echo "Lambda関数用の環境変数を設定しました"
else
    echo "環境変数ファイル(.env)が見つかりません。デフォルトの環境変数を使用します。"
    LAMBDA_ENV_VARS="{\"Variables\":{\"AWS_REGION\":\"ap-northeast-1\",\"S3_BUCKET\":\"<バケット名>\",\"ENVIRONMENT\":\"test\"}}"
fi

# AWS CLIを使用してデプロイする方法の説明
echo ""
echo "===== AWS CLIを使用してデプロイする方法 ====="
echo "1. Lambda関数を作成:"
echo "   aws lambda create-function \\"
echo "     --function-name test-lambda-minimal \\"
echo "     --runtime python3.9 \\"
echo "     --handler lambda_function.lambda_handler \\"
echo "     --role arn:aws:iam::<アカウントID>:role/lambda-test-role \\"
echo "     --zip-file fileb://$SCRIPT_DIR/function.zip \\"
echo "     --environment '$LAMBDA_ENV_VARS'"
echo ""
echo "   または既存の関数を更新:"
echo "   aws lambda update-function-code \\"
echo "     --function-name test-lambda-minimal \\"
echo "     --zip-file fileb://$SCRIPT_DIR/function.zip"
echo ""
echo "2. 環境変数を更新:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name test-lambda-minimal \\"
echo "     --environment '$LAMBDA_ENV_VARS'"
echo ""
echo "3. Lambda関数をテスト実行:"
echo "   aws lambda invoke \\"
echo "     --function-name test-lambda-minimal \\"
echo "     --payload '{}' \\"
echo "     response.json"
echo ""
echo "   テスト結果を確認:"
echo "   cat response.json"
