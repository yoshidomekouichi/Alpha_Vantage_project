#!/bin/bash

# Lambda関数のデプロイパッケージを作成するスクリプト（最適化版）

# エラーが発生したら終了
set -e

# 現在のディレクトリを取得
CURRENT_DIR=$(pwd)

# プロジェクトのルートディレクトリを取得
PROJECT_ROOT=$(dirname $(dirname $0))

# パッケージディレクトリを確認
PACKAGE_DIR="$PROJECT_ROOT/lambda/package"
if [ -d "$PACKAGE_DIR" ]; then
    echo "既存のパッケージディレクトリを使用します..."
else
    echo "パッケージディレクトリを作成しています..."
    mkdir -p $PACKAGE_DIR
fi

# 必要なファイルをコピー
echo "必要なファイルをコピーしています..."

# 注意: fetch_daily.pyとfetch_daily_lambda.pyは既に修正済みのものを使用するため、
# ここではコピーしません

# 必要なモジュールをコピー（既存のファイルを上書き）
echo "モジュールをコピーしています..."
cp -rf $PROJECT_ROOT/src/utils $PACKAGE_DIR/
cp -rf $PROJECT_ROOT/src/api $PACKAGE_DIR/
cp -rf $PROJECT_ROOT/src/core $PACKAGE_DIR/
cp -rf $PROJECT_ROOT/src/notifications $PACKAGE_DIR/
cp -f $PROJECT_ROOT/src/config.py $PACKAGE_DIR/

# 必要なライブラリをインストール（既にインストールされている場合はスキップ）
echo "必要なライブラリを確認しています..."
if [ ! -d "$PACKAGE_DIR/pandas" ] || [ ! -d "$PACKAGE_DIR/numpy" ]; then
    echo "基本ライブラリをインストールしています..."
    pip install -r $PROJECT_ROOT/lambda/requirements_lambda.txt -t $PACKAGE_DIR --no-deps
else
    echo "基本ライブラリは既にインストールされています。スキップします。"
fi

# デプロイパッケージを作成
echo "デプロイパッケージを作成しています..."
cd $PACKAGE_DIR
zip -r ../fetch_daily_lambda.zip .
cd $CURRENT_DIR

echo "デプロイパッケージが作成されました: $PROJECT_ROOT/lambda/fetch_daily_lambda.zip"
