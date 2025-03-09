#!/bin/bash

# Lambda Layerを作成するスクリプト
# numpyとpandasを含むレイヤーを作成します

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

# レイヤーディレクトリを確認
LAYER_DIR="$PROJECT_ROOT/lambda/layer"
echo "レイヤーディレクトリ: $LAYER_DIR"

# Pythonディレクトリを確認（Lambda Layerの構造に合わせる）
PYTHON_DIR="$LAYER_DIR/python"
echo "Pythonディレクトリ: $PYTHON_DIR"

# 既存のレイヤーディレクトリをクリーンアップ
show_status "レイヤーディレクトリをクリーンアップしています..."
if [ -d "$LAYER_DIR" ]; then
    echo "既存のレイヤーディレクトリを削除しています..."
    rm -rf $LAYER_DIR || handle_error "レイヤーディレクトリの削除に失敗しました"
fi

# 新しいレイヤーディレクトリを作成
echo "新しいレイヤーディレクトリを作成しています..."
mkdir -p $PYTHON_DIR || handle_error "Pythonディレクトリの作成に失敗しました"

# 仮想環境を作成してライブラリをインストール
show_status "ライブラリをインストールしています..."

# 仮想環境のディレクトリ
VENV_DIR="$PROJECT_ROOT/lambda/layer_venv"

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

# numpyとpandasをインストール
show_status "numpyとpandasをインストールしています..."
echo "numpyをインストールしています..."
pip install numpy==1.26.4 -t $PYTHON_DIR || handle_error "numpyのインストールに失敗しました"

echo "pandasをインストールしています..."
pip install pandas==2.2.3 -t $PYTHON_DIR || handle_error "pandasのインストールに失敗しました"

# 不要なファイルを削除してサイズを小さくする
show_status "不要なファイルを削除しています..."

# __pycache__ディレクトリと.pycファイルを削除
echo "キャッシュファイルを削除しています..."
find $PYTHON_DIR -name "*.pyc" -delete
find $PYTHON_DIR -name "__pycache__" -type d -exec rm -rf {} +

# テストファイルとドキュメントを削除
echo "テストファイルとドキュメントを削除しています..."
find $PYTHON_DIR -name "tests" -type d -exec rm -rf {} +
find $PYTHON_DIR -name "testing" -type d -exec rm -rf {} +
find $PYTHON_DIR -name "docs" -type d -exec rm -rf {} +

# 仮想環境を非アクティブ化
deactivate

# レイヤーのzipファイルを作成
show_status "Lambda Layerのzipファイルを作成しています..."
cd $LAYER_DIR || handle_error "レイヤーディレクトリへの移動に失敗しました"
echo "現在のディレクトリ: $(pwd)"

# zipファイルを作成
echo "zipファイルを作成しています..."
zip -r ../numpy_pandas_layer.zip . || handle_error "zipファイルの作成に失敗しました"

# 元のディレクトリに戻る
cd $CURRENT_DIR || handle_error "元のディレクトリへの移動に失敗しました"

show_status "Lambda Layerが作成されました: $PROJECT_ROOT/lambda/numpy_pandas_layer.zip"
echo "レイヤーサイズ: $(du -h $PROJECT_ROOT/lambda/numpy_pandas_layer.zip | cut -f1)"

# Lambda関数のデプロイパッケージを作成（numpyとpandasを除く）
show_status "Lambda関数のデプロイパッケージを作成しています..."

# パッケージディレクトリを確認
PACKAGE_DIR="$PROJECT_ROOT/lambda/package"
echo "パッケージディレクトリ: $PACKAGE_DIR"

# 既存のパッケージディレクトリをクリーンアップ
if [ -d "$PACKAGE_DIR" ]; then
    echo "既存のパッケージディレクトリを削除しています..."
    rm -rf $PACKAGE_DIR || handle_error "パッケージディレクトリの削除に失敗しました"
fi

# 新しいパッケージディレクトリを作成
echo "新しいパッケージディレクトリを作成しています..."
mkdir -p $PACKAGE_DIR || handle_error "パッケージディレクトリの作成に失敗しました"

# 必要なファイルをコピー
echo "必要なファイルをコピーしています..."

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

# 仮想環境を作成してライブラリをインストール（numpyとpandasを除く）
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
pip install -r $PROJECT_ROOT/lambda/temp_requirements.txt -t $PACKAGE_DIR || handle_error "基本ライブラリのインストールに失敗しました"

# 一時ファイルを削除
rm -f $PROJECT_ROOT/lambda/temp_requirements.txt

# 仮想環境を非アクティブ化
deactivate

# Lambda環境フラグを設定
echo "Lambda環境フラグを設定しています..."
echo "AWS_LAMBDA_EXECUTION=true" > $PACKAGE_DIR/.env

# デプロイパッケージを作成
cd $PACKAGE_DIR || handle_error "パッケージディレクトリへの移動に失敗しました"
echo "現在のディレクトリ: $(pwd)"

# zipファイルを作成
echo "zipファイルを作成しています..."
zip -r ../fetch_daily_lambda_without_numpy.zip . || handle_error "zipファイルの作成に失敗しました"

# 元のディレクトリに戻る
cd $CURRENT_DIR || handle_error "元のディレクトリへの移動に失敗しました"

show_status "デプロイパッケージが作成されました: $PROJECT_ROOT/lambda/fetch_daily_lambda_without_numpy.zip"
echo "パッケージサイズ: $(du -h $PROJECT_ROOT/lambda/fetch_daily_lambda_without_numpy.zip | cut -f1)"

show_status "Lambda Layerとデプロイパッケージの作成が完了しました"
echo "次のステップ:"
echo "1. AWS管理コンソールでLambda Layerを作成し、numpy_pandas_layer.zipをアップロードします"
echo "2. Lambda関数にLayerをアタッチします"
echo "3. Lambda関数のコードを更新し、fetch_daily_lambda_without_numpy.zipをアップロードします"
