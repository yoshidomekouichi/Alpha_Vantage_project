#!/bin/bash
# Lambda関数とレイヤーのデプロイパッケージを作成するスクリプト

set -e  # エラーが発生したら停止

# 作業ディレクトリを設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "===== Lambda デプロイパッケージの作成を開始します ====="

# デプロイ用の一時ディレクトリを作成
DEPLOY_DIR="$SCRIPT_DIR/deploy"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Lambda関数のコードをコピー
echo "Lambda関数のコードをコピーしています..."
cp -r "$SCRIPT_DIR/function/lambda_function.py" "$DEPLOY_DIR/"

# srcディレクトリのファイルをルートディレクトリに直接コピー
echo "srcディレクトリのファイルをコピーしています..."
cp -r "$PROJECT_ROOT/src/"* "$DEPLOY_DIR/"

# 必要なディレクトリ構造を維持するために空のsrcディレクトリも作成
mkdir -p "$DEPLOY_DIR/src"

# S3パスユーティリティをルートディレクトリにもコピー（Lambda関数からのインポート用）
echo "S3パスユーティリティをルートディレクトリにコピーしています..."
cp "$PROJECT_ROOT/src/utils/s3_paths.py" "$DEPLOY_DIR/"

# Lambda関数のZIPパッケージを作成
echo "Lambda関数のZIPパッケージを作成しています..."
cd "$DEPLOY_DIR"
zip -r "$SCRIPT_DIR/function.zip" .
cd "$PROJECT_ROOT"

echo "Lambda関数のZIPパッケージを作成しました: $SCRIPT_DIR/function.zip"

# レイヤーパッケージの作成
echo "===== Lambda レイヤーパッケージの作成を開始します ====="

# レイヤー用の一時ディレクトリを作成
LAYER_DIR="$SCRIPT_DIR/layer_build"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"

# requirements.txtからライブラリをインストール（pyarrowを除外）
echo "依存ライブラリをインストールしています..."
# pyarrowを除外して依存ライブラリをインストール
grep -v "pyarrow" "$PROJECT_ROOT/requirements.txt" > "$LAYER_DIR/requirements_no_pyarrow.txt"
pip install -r "$LAYER_DIR/requirements_no_pyarrow.txt" --target "$LAYER_DIR/python"

# レイヤーのZIPパッケージを作成
echo "レイヤーのZIPパッケージを作成しています..."
cd "$LAYER_DIR"
zip -r "$SCRIPT_DIR/layer.zip" .
cd "$PROJECT_ROOT"

echo "レイヤーのZIPパッケージを作成しました: $SCRIPT_DIR/layer.zip"

# 一時ディレクトリを削除
rm -rf "$DEPLOY_DIR" "$LAYER_DIR"

echo "===== デプロイパッケージの作成が完了しました ====="
echo "Lambda関数: $SCRIPT_DIR/function.zip"
echo "Lambda レイヤー: $SCRIPT_DIR/layer.zip"

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
    LAMBDA_ENV_VARS="{\"Variables\":{\"ALPHA_VANTAGE_API_KEY\":\"<APIキー>\",\"S3_BUCKET\":\"<バケット名>\",\"AWS_REGION\":\"ap-northeast-1\"}}"
fi

# AWS CLIを使用してデプロイする方法の説明
echo ""
echo "===== AWS CLIを使用してデプロイする方法 ====="
echo "1. Lambda関数を作成:"
echo "   aws lambda create-function \\"
echo "     --function-name alpha-vantage-daily-fetch \\"
echo "     --runtime python3.9 \\"
echo "     --handler lambda_function.lambda_handler \\"
echo "     --role arn:aws:iam::<アカウントID>:role/lambda-alpha-vantage-role \\"
echo "     --zip-file fileb://$SCRIPT_DIR/function.zip \\"
echo "     --environment '$LAMBDA_ENV_VARS'"
echo ""
echo "   または既存の関数を更新:"
echo "   aws lambda update-function-code \\"
echo "     --function-name alpha-vantage-daily-fetch \\"
echo "     --zip-file fileb://$SCRIPT_DIR/function.zip"
echo ""
echo "2. レイヤーを作成:"
echo "   aws lambda publish-layer-version \\"
echo "     --layer-name alpha-vantage-dependencies \\"
echo "     --description \"Alpha Vantage API依存ライブラリ\" \\"
echo "     --zip-file fileb://$SCRIPT_DIR/layer.zip \\"
echo "     --compatible-runtimes python3.9"
echo ""
echo "3. 関数にレイヤーを追加:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name alpha-vantage-daily-fetch \\"
echo "     --layers arn:aws:lambda:<リージョン>:<アカウントID>:layer:alpha-vantage-dependencies:<バージョン>"
echo ""
echo "4. 環境変数を更新:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name alpha-vantage-daily-fetch \\"
echo "     --environment '$LAMBDA_ENV_VARS'"
