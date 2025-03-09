# 最小構成のAWS Lambda関数

このディレクトリには、最小構成のAWS Lambda関数とそのデプロイスクリプトが含まれています。

## ディレクトリ構造

```
test_lambda/
├── README.md           # このファイル
├── deploy.sh           # デプロイパッケージ作成スクリプト
└── function/
    └── lambda_function.py  # Lambda関数のコード
```

## Lambda関数の概要

`lambda_function.py`は、以下の機能を持つ最小構成のLambda関数です：

- 環境変数の読み取りと表示
- イベントとコンテキスト情報のログ出力
- 実行時間の計測
- JSONレスポンスの返却

この関数は、Lambda環境で正常に動作することを確認するための最小限の実装です。

## デプロイ方法

### 1. デプロイパッケージの作成

以下のコマンドを実行して、デプロイパッケージ（ZIP）を作成します：

```bash
./deploy.sh
```

このスクリプトは、Lambda関数のコードをZIPファイルにパッケージ化し、`function.zip`として保存します。

### 2. AWS CLIを使用したデプロイ

#### 新規Lambda関数の作成

```bash
aws lambda create-function \
  --function-name test-lambda-minimal \
  --runtime python3.9 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::<アカウントID>:role/lambda-test-role \
  --zip-file fileb://test_lambda/function.zip \
  --environment '{"Variables":{"AWS_REGION":"ap-northeast-1","S3_BUCKET":"your-bucket-name","ENVIRONMENT":"test"}}'
```

#### 既存Lambda関数の更新

```bash
aws lambda update-function-code \
  --function-name test-lambda-minimal \
  --zip-file fileb://test_lambda/function.zip
```

### 3. Lambda関数のテスト実行

```bash
aws lambda invoke \
  --function-name test-lambda-minimal \
  --payload '{}' \
  response.json

# 結果の確認
cat response.json
```

## 環境変数

Lambda関数は以下の環境変数を使用します：

- `AWS_REGION`: AWS リージョン（例: ap-northeast-1）
- `S3_BUCKET`: S3バケット名
- `ENVIRONMENT`: 環境（test/prod）
- `DEBUG_MODE`: デバッグモード（true/false）

これらの環境変数は、プロジェクトルートの`.env`ファイルから自動的に読み込まれます。

## ローカルでのテスト実行

Lambda関数はローカルでも実行できます：

```bash
cd test_lambda/function
python lambda_function.py
```

これにより、Lambda関数がローカル環境で実行され、結果がコンソールに表示されます。
