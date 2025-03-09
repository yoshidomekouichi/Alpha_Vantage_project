#!/bin/bash

# Lambda関数のデプロイパッケージを作成するスクリプト（v2.1）
# 2025-03-08 更新: numpyのインポートエラーを修正

# エラーが発生したら終了
set -e

# 関数: エラーハンドリング
handle_error() {
    echo "エラーが発生しました: $1"
    exit 1
}

# 関数: 実行ステータスの表示
show_status() {
    echo "=================================================="
    echo "🔧 $1"
    echo "=================================================="
}

# 現在のディレクトリを取得
CURRENT_DIR=$(pwd)

# プロジェクトのルートディレクトリを取得
PROJECT_ROOT=$(cd $(dirname $0)/.. && pwd)
echo "プロジェクトルートディレクトリ: $PROJECT_ROOT"

# パッケージディレクトリを確認
PACKAGE_DIR="$PROJECT_ROOT/lambda/package"
echo "パッケージディレクトリ: $PACKAGE_DIR"

# 既存のパッケージディレクトリをクリーンアップ
show_status "パッケージディレクトリをクリーンアップしています..."
if [ -d "$PACKAGE_DIR" ]; then
    echo "既存のパッケージディレクトリを削除しています..."
    rm -rf $PACKAGE_DIR || handle_error "パッケージディレクトリの削除に失敗しました"
fi

# 新しいパッケージディレクトリを作成
echo "新しいパッケージディレクトリを作成しています..."
mkdir -p $PACKAGE_DIR || handle_error "パッケージディレクトリの作成に失敗しました"

# 必要なファイルをコピー
show_status "必要なファイルをコピーしています..."

# src/fetch_daily.pyをコピー（Lambda環境対応済み）
echo "fetch_daily.pyをコピーしています..."
cp $PROJECT_ROOT/src/fetch_daily.py $PACKAGE_DIR/ || handle_error "fetch_daily.pyのコピーに失敗しました"

# Lambda関数のハンドラーをコピー
echo "Lambda関数のハンドラーをコピーしています..."
cp $PROJECT_ROOT/lambda/fetch_daily_lambda.py $PACKAGE_DIR/ || handle_error "fetch_daily_lambda.pyのコピーに失敗しました"

# 必要なモジュールをコピー
echo "必要なモジュールをコピーしています..."
cp -r $PROJECT_ROOT/src/utils $PACKAGE_DIR/ || handle_error "utilsモジュールのコピーに失敗しました"
cp -r $PROJECT_ROOT/src/api $PACKAGE_DIR/ || handle_error "apiモジュールのコピーに失敗しました"
cp -r $PROJECT_ROOT/src/core $PACKAGE_DIR/ || handle_error "coreモジュールのコピーに失敗しました"
cp -r $PROJECT_ROOT/src/notifications $PACKAGE_DIR/ || handle_error "notificationsモジュールのコピーに失敗しました"
cp $PROJECT_ROOT/src/config.py $PACKAGE_DIR/ || handle_error "config.pyのコピーに失敗しました"

# 仮想環境を作成してライブラリをインストール
show_status "ライブラリをインストールしています..."

# 仮想環境のディレクトリ
VENV_DIR="$PROJECT_ROOT/lambda/venv"

# 既存の仮想環境を削除
if [ -d "$VENV_DIR" ]; then
    echo "既存の仮想環境を削除しています..."
    rm -rf $VENV_DIR || handle_error "仮想環境の削除に失敗しました"
fi

# 新しい仮想環境を作成
echo "新しい仮想環境を作成しています..."
python -m venv $VENV_DIR || handle_error "仮想環境の作成に失敗しました"

# 仮想環境をアクティベート
echo "仮想環境をアクティベートしています..."
source $VENV_DIR/bin/activate || handle_error "仮想環境のアクティベートに失敗しました"

# pipをアップグレード
echo "pipをアップグレードしています..."
pip install --upgrade pip || handle_error "pipのアップグレードに失敗しました"

# 必要なライブラリをインストール（numpyとpandasを除く）
echo "基本ライブラリをインストールしています..."
# requirements_lambda.txtからnumpyとpandasを除いたライブラリをインストール
grep -v "numpy\|pandas" $PROJECT_ROOT/lambda/requirements_lambda.txt > $PROJECT_ROOT/lambda/temp_requirements.txt
pip install -r $PROJECT_ROOT/lambda/temp_requirements.txt || handle_error "基本ライブラリのインストールに失敗しました"

# ライブラリをパッケージディレクトリにコピー
echo "基本ライブラリをパッケージディレクトリにコピーしています..."
pip install -r $PROJECT_ROOT/lambda/temp_requirements.txt -t $PACKAGE_DIR || handle_error "基本ライブラリのコピーに失敗しました"

# numpyとpandasを個別にインストール（特別な処理）
echo "numpyとpandasを個別にインストールしています..."
echo "numpyをインストールしています..."
pip install numpy==1.26.4 -t $PACKAGE_DIR || handle_error "numpyのインストールに失敗しました"

echo "pandasをインストールしています..."
pip install pandas==2.2.3 -t $PACKAGE_DIR || handle_error "pandasのインストールに失敗しました"

# numpyとpandasのソースディレクトリ問題を解決
echo "numpyとpandasのソースディレクトリ問題を解決しています..."
# __pycache__ディレクトリと.pycファイルを削除
find $PACKAGE_DIR -name "*.pyc" -delete
find $PACKAGE_DIR -name "__pycache__" -type d -exec rm -rf {} +

# numpyのソースディレクトリ問題を解決するための特別な処理
echo "numpyのテストファイルとドキュメントを削除しています..."
find $PACKAGE_DIR/numpy -name "tests" -type d -exec rm -rf {} +
find $PACKAGE_DIR/numpy -name "testing" -type d -exec rm -rf {} +
find $PACKAGE_DIR/numpy -name "docs" -type d -exec rm -rf {} +

# pandasのテストファイルとドキュメントを削除
echo "pandasのテストファイルとドキュメントを削除しています..."
find $PACKAGE_DIR/pandas -name "tests" -type d -exec rm -rf {} +
find $PACKAGE_DIR/pandas -name "testing" -type d -exec rm -rf {} +
find $PACKAGE_DIR/pandas -name "docs" -type d -exec rm -rf {} +

# 一時ファイルを削除
rm -f $PROJECT_ROOT/lambda/temp_requirements.txt

# 仮想環境を非アクティブ化
deactivate

# Lambda環境フラグを設定
echo "Lambda環境フラグを設定しています..."
echo "AWS_LAMBDA_EXECUTION=true" > $PACKAGE_DIR/.env

# デバッグモードを有効化
echo "デバッグモードを有効化します..."
echo "DEBUG_MODE=true" > $PACKAGE_DIR/.env
echo "LOG_LEVEL=DEBUG" >> $PACKAGE_DIR/.env

# パッケージ内容の確認
echo "パッケージ内容を確認しています..."
find $PACKAGE_DIR -type f -name "*.py" | sort > $PROJECT_ROOT/lambda/package_files.txt
echo "パッケージ内のPythonファイル一覧: $PROJECT_ROOT/lambda/package_files.txt"

# モジュール構造の確認
echo "モジュール構造を確認しています..."
cd $PACKAGE_DIR
echo "パッケージディレクトリ内のモジュール:"
find . -type d -name "__pycache__" -prune -o -type f -name "*.py" -print | sort

# 依存関係の確認
echo "依存関係を確認しています..."
if [ -f "$PACKAGE_DIR/requirements.txt" ]; then
    echo "requirements.txt の内容:"
    cat $PACKAGE_DIR/requirements.txt
else
    echo "requirements.txt が見つかりません"
fi

# デプロイパッケージを作成
show_status "デプロイパッケージを作成しています..."
cd $PACKAGE_DIR || handle_error "パッケージディレクトリへの移動に失敗しました"
echo "現在のディレクトリ: $(pwd)"

# zipファイルを作成
echo "zipファイルを作成しています..."
zip -r ../fetch_daily_lambda.zip . || handle_error "zipファイルの作成に失敗しました"

# 元のディレクトリに戻る
cd $CURRENT_DIR || handle_error "元のディレクトリへの移動に失敗しました"

show_status "デプロイパッケージが作成されました: $PROJECT_ROOT/lambda/fetch_daily_lambda.zip"
echo "パッケージサイズ: $(du -h $PROJECT_ROOT/lambda/fetch_daily_lambda.zip | cut -f1)"

# AWS Lambda関数へのデプロイ方法
echo ""
echo "=== AWS Lambda関数へのデプロイ方法 ==="
echo "1. AWS Management Consoleを使用する場合:"
echo "   - Lambda関数のページで「コード」タブを選択"
echo "   - 「.zipファイルをアップロード」を選択"
echo "   - 作成したZIPファイルをアップロード"
echo ""
echo "2. AWS CLIを使用する場合:"
echo "   aws lambda update-function-code --function-name YOUR_FUNCTION_NAME \\"
echo "   --zip-file fileb://$PROJECT_ROOT/lambda/fetch_daily_lambda.zip"
echo ""
echo "3. 環境変数の設定:"
echo "   以下の環境変数を設定してください:"
echo "   - ALPHA_VANTAGE_API_KEY: Alpha Vantage APIキー"
echo "   - STOCK_SYMBOLS: 取得する株式銘柄（カンマ区切り）"
echo "   - S3_BUCKET: データを保存するS3バケット名"
echo "   - MOCK_MODE: モックモード（true/false）"
echo "   - LOG_LEVEL: ログレベル（INFO/DEBUG/ERROR）"
echo ""
echo "4. Slack通知の設定:"
echo "   Slack通知を有効にするには、以下の環境変数を設定してください:"
echo "   - SLACK_ENABLED: Slack通知の有効化（true/false）"
echo "   - SLACK_WEBHOOK_URL: Slack Webhook URL（基本URL）"
echo "   - SLACK_WEBHOOK_URL_ERROR: エラー通知用Webhook URL（オプション）"
echo "   - SLACK_WEBHOOK_URL_WARNING: 警告通知用Webhook URL（オプション）"
echo "   - SLACK_WEBHOOK_URL_INFO: 情報通知用Webhook URL（オプション）"
echo ""
echo "   ログレベル別の通知設定:"
echo "   - SLACK_NOTIFY_INFO: INFO レベルの通知を有効化（true/false）"
echo "   - SLACK_NOTIFY_WARNING: WARNING レベルの通知を有効化（true/false）"
echo "   - SLACK_NOTIFY_ERROR: ERROR レベルの通知を有効化（true/false）"
echo ""
echo "5. タイムアウト設定:"
echo "   - Lambda関数のタイムアウトを300秒（5分）以上に設定してください"
echo "   - メモリサイズは256MB以上を推奨します"
echo ""
echo "デプロイが完了しました！"
