#!/bin/bash

# Lambda関数のデプロイパッケージを作成するスクリプト

# エラーが発生したら終了
set -e

# 現在のディレクトリを取得
CURRENT_DIR=$(pwd)

# プロジェクトのルートディレクトリを取得
PROJECT_ROOT=$(dirname $(dirname $0))

# パッケージディレクトリを作成
echo "パッケージディレクトリを作成しています..."
mkdir -p $PROJECT_ROOT/lambda/package

# 必要なファイルをコピー
echo "必要なファイルをコピーしています..."

# fetch_daily.pyをコピー
cp $PROJECT_ROOT/src/fetch_daily.py $PROJECT_ROOT/lambda/package/

# 必要なモジュールをコピー
cp -r $PROJECT_ROOT/src/utils $PROJECT_ROOT/lambda/package/
cp -r $PROJECT_ROOT/src/api $PROJECT_ROOT/lambda/package/
cp -r $PROJECT_ROOT/src/core $PROJECT_ROOT/lambda/package/
cp -r $PROJECT_ROOT/src/notifications $PROJECT_ROOT/lambda/package/
cp $PROJECT_ROOT/src/config.py $PROJECT_ROOT/lambda/package/

# Lambda関数のハンドラーをコピー
cp $PROJECT_ROOT/lambda/fetch_daily_lambda.py $PROJECT_ROOT/lambda/package/

# 必要なライブラリをインストール
echo "必要なライブラリをインストールしています..."
pip install -r $PROJECT_ROOT/lambda/requirements_lambda.txt -t $PROJECT_ROOT/lambda/package/

# デプロイパッケージを作成
echo "デプロイパッケージを作成しています..."
cd $PROJECT_ROOT/lambda/package
zip -r ../fetch_daily_lambda.zip .
cd $CURRENT_DIR

echo "デプロイパッケージが作成されました: $PROJECT_ROOT/lambda/fetch_daily_lambda.zip"
