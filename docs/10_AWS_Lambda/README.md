# AWS Lambdaモジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのAWS Lambda実装について説明します。

## 1. AWS Lambdaの概要

AWS Lambdaは、サーバーレスコンピューティングサービスで、サーバーのプロビジョニングや管理なしにコードを実行できます。Alpha Vantage株価データパイプラインでは、AWS Lambdaを使用して、日次株価データの取得と保存を自動化しています。主な機能は以下の通りです：

- サーバーレス実行環境
- スケジュールに基づく自動実行
- イベント駆動型の実行
- 柔軟なスケーリング
- 低コストな運用

## 2. 主要なファイル

- `lambda/fetch_daily_lambda.py`: Lambda関数のハンドラー
- `lambda/create_deployment_package.sh`: デプロイパッケージ作成スクリプト
- `lambda/update_deployment_package.md`: デプロイパッケージ更新手順
- `lambda/lambda_policy.json`: Lambda実行ロールのポリシー
- `lambda/test_event.json`: Lambda関数のテストイベント
- `lambda/schedule_settings.md`: スケジュール設定の手順
- `lambda/monitoring_troubleshooting.md`: モニタリングとトラブルシューティングの手順
- `lambda/README.md`: Lambda実装の概要と手順
- `lambda/README_ja.md`: Lambda実装の概要と手順（日本語版）

## 3. Lambda関数ハンドラー（`fetch_daily_lambda.py`）の詳細

### 3.1 ハンドラーの構造

```python
import os
import sys
import json
import boto3
import logging
from datetime import datetime

# Lambda関数のログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数の設定
os.environ['MOCK_MODE'] = 'False'  # 本番モード
os.environ['SAVE_TO_S3'] = 'True'  # S3に保存する
os.environ['SLACK_ENABLED'] = 'True'  # Slack通知を有効化

def lambda_handler(event, context):
    """
    Lambda関数のハンドラー
    
    引数:
        event: Lambda関数のイベント
        context: Lambda関数のコンテキスト
        
    戻り値:
        Lambda関数の実行結果
    """
    logger.info(f"Lambda function started at {datetime.now().isoformat()}")
    logger.info(f"Event: {json.dumps(event)}")
    
    # Slack Webhook URLsを環境変数から取得
    slack_webhook_url_error = os.environ.get('SLACK_WEBHOOK_URL_ERROR')
    slack_webhook_url_warning = os.environ.get('SLACK_WEBHOOK_URL_WARNING')
    slack_webhook_url_info = os.environ.get('SLACK_WEBHOOK_URL_INFO')
    
    # 環境変数にSlack Webhook URLsが設定されていることを確認
    if not (slack_webhook_url_error and slack_webhook_url_warning and slack_webhook_url_info):
        logger.warning("Slack Webhook URLs are not properly configured in environment variables")
    else:
        logger.info("Slack Webhook URLs are configured")
    
    try:
        # Lambda関数のパッケージをインポートパスに追加
        sys.path.append('/var/task')
        
        # fetch_daily.pyをインポート
        from fetch_daily import main
        
        # fetch_daily.pyのmain関数を実行
        result = main()
        
        # 実行結果をログに出力
        logger.info(f"fetch_daily.py execution completed with result: {result}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'fetch_daily.py execution completed successfully',
                'result': result
            })
        }
    except Exception as e:
        logger.error(f"Error executing fetch_daily.py: {str(e)}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(error_traceback)
        
        # エラー情報をより詳細に含める
        error_details = {
            'error_message': str(e),
            'error_type': type(e).__name__,
            'traceback': error_traceback,
            'lambda_function_name': context.function_name,
            'lambda_function_version': context.function_version,
            'lambda_request_id': context.aws_request_id,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error executing fetch_daily.py',
                'error': str(e),
                'error_details': error_details
            })
        }
```

Lambda関数ハンドラーは、以下の主要な部分から構成されています：

1. **インポートと初期設定**: 必要なモジュールのインポートとロギングの設定
2. **環境変数の設定**: Lambda環境での環境変数の設定
3. **ハンドラー関数**: Lambda関数のエントリーポイント
4. **メイン処理**: `fetch_daily.py`のインポートと実行
5. **エラーハンドリング**: 例外のキャッチと詳細なエラー情報の返却

### 3.2 環境変数の設定

```python
# 環境変数の設定
os.environ['MOCK_MODE'] = 'False'  # 本番モード
os.environ['SAVE_TO_S3'] = 'True'  # S3に保存する
os.environ['SLACK_ENABLED'] = 'True'  # Slack通知を有効化
```

環境変数の設定部分では、Lambda関数内で実行時の動作を制御するための環境変数を設定しています。各行の処理内容は以下の通りです：

1. `os.environ['MOCK_MODE'] = 'False'`: モックモードを無効に設定します。本番環境では実際のAPIコールを行うためです。
2. `os.environ['SAVE_TO_S3'] = 'True'`: S3への保存機能を有効に設定します。取得したデータをS3バケットに保存します。
3. `os.environ['SLACK_ENABLED'] = 'True'`: Slack通知機能を有効に設定します。処理結果をSlackに通知します。

これらの環境変数は、`fetch_daily.py`スクリプトの動作を制御するために使用されます。Lambda関数内で直接設定することで、AWS Lambdaコンソールでの環境変数設定に加えて、追加の制御が可能になります。

### 3.3 Slack Webhook URLsの取得

```python
# Slack Webhook URLsを環境変数から取得
slack_webhook_url_error = os.environ.get('SLACK_WEBHOOK_URL_ERROR')
slack_webhook_url_warning = os.environ.get('SLACK_WEBHOOK_URL_WARNING')
slack_webhook_url_info = os.environ.get('SLACK_WEBHOOK_URL_INFO')

# 環境変数にSlack Webhook URLsが設定されていることを確認
if not (slack_webhook_url_error and slack_webhook_url_warning and slack_webhook_url_info):
    logger.warning("Slack Webhook URLs are not properly configured in environment variables")
else:
    logger.info("Slack Webhook URLs are configured")
```

Slack Webhook URLsの取得部分では、通知送信先の設定を確認しています。各行の処理内容は以下の通りです：

1. `slack_webhook_url_error = os.environ.get('SLACK_WEBHOOK_URL_ERROR')`: エラー通知用のSlack Webhook URLを環境変数から取得します。
2. `slack_webhook_url_warning = os.environ.get('SLACK_WEBHOOK_URL_WARNING')`: 警告通知用のSlack Webhook URLを環境変数から取得します。
3. `slack_webhook_url_info = os.environ.get('SLACK_WEBHOOK_URL_INFO')`: 情報通知用のSlack Webhook URLを環境変数から取得します。
4. `if not (slack_webhook_url_error and slack_webhook_url_warning and slack_webhook_url_info):`: すべてのWebhook URLが設定されているかをチェックします。
5. `logger.warning("Slack Webhook URLs are not properly configured in environment variables")`: URLが設定されていない場合、警告メッセージをログに記録します。
6. `else:`: すべてのURLが設定されている場合の処理です。
7. `logger.info("Slack Webhook URLs are configured")`: 設定が完了していることをログに記録します。

これにより、通知機能が正しく設定されているかを実行時に確認し、問題がある場合はログに警告を残します。

### 3.4 メイン処理

```python
try:
    # Lambda関数のパッケージをインポートパスに追加
    sys.path.append('/var/task')
    
    # fetch_daily.pyをインポート
    from fetch_daily import main
    
    # fetch_daily.pyのmain関数を実行
    result = main()
    
    # 実行結果をログに出力
    logger.info(f"fetch_daily.py execution completed with result: {result}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'fetch_daily.py execution completed successfully',
            'result': result
        })
    }
```

メイン処理部分では、実際のデータ取得処理を実行します。各行の処理内容は以下の通りです：

1. `try:`: 例外処理のためのtryブロックを開始します。
2. `sys.path.append('/var/task')`: Lambda関数のデプロイパッケージがあるディレクトリをPythonのインポートパスに追加します。
3. `from fetch_daily import main`: メインの処理ロジックを含む`fetch_daily.py`モジュールから`main`関数をインポートします。
4. `result = main()`: インポートした`main`関数を実行し、結果を`result`変数に格納します。
5. `logger.info(f"fetch_daily.py execution completed with result: {result}")`: 実行結果をINFOレベルでログに記録します。
6. `return {...}`: Lambda関数のレスポンスを返します。
7. `'statusCode': 200`: HTTPステータスコード200（成功）を設定します。
8. `'body': json.dumps({...})`: レスポンスボディをJSON形式で設定します。
9. `'message': 'fetch_daily.py execution completed successfully'`: 成功メッセージを含めます。
10. `'result': result`: 実行結果を含めます。

この部分は、Lambda関数の主要な処理ロジックを実行し、その結果をフォーマットして返す役割を担っています。

### 3.5 エラーハンドリング

```python
except Exception as e:
    logger.error(f"Error executing fetch_daily.py: {str(e)}")
    import traceback
    error_traceback = traceback.format_exc()
    logger.error(error_traceback)
    
    # エラー情報をより詳細に含める
    error_details = {
        'error_message': str(e),
        'error_type': type(e).__name__,
        'traceback': error_traceback,
        'lambda_function_name': context.function_name,
        'lambda_function_version': context.function_version,
        'lambda_request_id': context.aws_request_id,
        'timestamp': datetime.now().isoformat()
    }
    
    return {
        'statusCode': 500,
        'body': json.dumps({
            'message': 'Error executing fetch_daily.py',
            'error': str(e),
            'error_details': error_details
        })
    }
```

エラーハンドリング部分では、実行中に発生した例外を捕捉して適切に処理します。各行の処理内容は以下の通りです：

1. `except Exception as e:`: あらゆる種類の例外をキャッチします。
2. `logger.error(f"Error executing fetch_daily.py: {str(e)}")`: エラーメッセージをERRORレベルでログに記録します。
3. `import traceback`: スタックトレースを取得するためのモジュールをインポートします。
4. `error_traceback = traceback.format_exc()`: 例外のスタックトレースを文字列形式で取得します。
5. `logger.error(error_traceback)`: スタックトレースをERRORレベルでログに記録します。
6. `error_details = {...}`: 詳細なエラー情報を含む辞書を作成します。
7. `'error_message': str(e)`: エラーメッセージを含めます。
8. `'error_type': type(e).__name__`: 例外の型名を含めます。
9. `'traceback': error_traceback`: スタックトレースを含めます。
10. `'lambda_function_name': context.function_name`: Lambda関数名を含めます。
11. `'lambda_function_version': context.function_version`: Lambda関数のバージョンを含めます。
12. `'lambda_request_id': context.aws_request_id`: AWS リクエストIDを含めます。
13. `'timestamp': datetime.now().isoformat()`: エラー発生時のタイムスタンプを含めます。
14. `return {...}`: エラーレスポンスを返します。
15. `'statusCode': 500`: HTTPステータスコード500（サーバーエラー）を設定します。
16. `'body': json.dumps({...})`: レスポンスボディをJSON形式で設定します。
17. `'message': 'Error executing fetch_daily.py'`: エラーメッセージを含めます。
18. `'error': str(e)`: 簡潔なエラーメッセージを含めます。
19. `'error_details': error_details`: 詳細なエラー情報を含めます。

この包括的なエラーハンドリングにより、問題が発生した場合でも詳細な診断情報が提供され、トラブルシューティングが容易になります。

## 4. デプロイパッケージの作成

Lambda関数をデプロイするには、デプロイパッケージを作成する必要があります。デプロイパッケージは、Lambda関数のコードと依存ライブラリを含むZIPファイルです。

### 4.1 デプロイパッケージ作成スクリプト（`create_deployment_package.sh`）

```bash
#!/bin/bash

# デプロイパッケージ作成スクリプト
# このスクリプトは、Lambda関数のデプロイパッケージを作成します。

# エラー時に終了
set -e

# 作業ディレクトリの作成
echo "Creating package directory..."
mkdir -p lambda/package

# 依存ライブラリのインストール
echo "Installing dependencies..."
pip install -r lambda/requirements_lambda.txt -t lambda/package/

# ソースコードのコピー
echo "Copying source code..."
cp -r src/* lambda/package/

# Lambda関数ハンドラーのコピー
echo "Copying Lambda handler..."
cp lambda/fetch_daily_lambda.py lambda/package/

# ZIPファイルの作成
echo "Creating ZIP file..."
cd lambda/package
zip -r ../fetch_daily_lambda.zip .
cd ../..

echo "Deployment package created: lambda/fetch_daily_lambda.zip"
echo "Package size: $(du -h lambda/fetch_daily_lambda.zip | cut -f1)"
```

このスクリプトは、以下の手順でデプロイパッケージを作成します：

1. パッケージディレクトリの作成
2. 依存ライブラリのインストール
3. ソースコードのコピー
4. Lambda関数ハンドラーのコピー
5. ZIPファイルの作成

### 4.2 依存ライブラリ（`requirements_lambda.txt`）

```
boto3==1.26.135
requests==2.31.0
pandas==2.0.1
python-dotenv==1.0.0
```

Lambda関数が依存するライブラリのリストです。これらのライブラリは、デプロイパッケージに含まれます。

## 5. Lambda関数のデプロイ

### 5.1 AWS Management Consoleを使用したデプロイ

1. AWS Management Consoleにログイン
2. Lambda サービスに移動
3. 「関数の作成」をクリック
4. 「一から作成」を選択
5. 関数名を入力（例：`fetch_daily_lambda`）
6. ランタイムとして「Python 3.9」を選択
7. 「関数の作成」をクリック
8. 「コード」タブで「アップロード元」を「.zipファイル」に変更
9. 作成したZIPファイル（`fetch_daily_lambda.zip`）をアップロード
10. 「保存」をクリック

### 5.2 AWS CLIを使用したデプロイ

```bash
# Lambda関数の作成
aws lambda create-function \
  --function-name fetch_daily_lambda \
  --runtime python3.9 \
  --role arn:aws:iam::123456789012:role/lambda-execution-role \
  --handler fetch_daily_lambda.lambda_handler \
  --zip-file fileb://lambda/fetch_daily_lambda.zip \
  --timeout 300 \
  --memory-size 512

# 既存のLambda関数の更新
aws lambda update-function-code \
  --function-name fetch_daily_lambda \
  --zip-file fileb://lambda/fetch_daily_lambda.zip
```

## 6. Lambda関数の設定

### 6.1 環境変数の設定

Lambda関数の環境変数を設定することで、関数の動作をカスタマイズできます。以下の環境変数を設定します：

- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage APIキー
- `S3_BUCKET`: S3バケット名
- `AWS_REGION`: AWSリージョン
- `STOCK_SYMBOLS`: 取得する株式銘柄（カンマ区切り）
- `SLACK_WEBHOOK_URL_ERROR`: エラー通知用Slack Webhook URL
- `SLACK_WEBHOOK_URL_WARNING`: 警告通知用Slack Webhook URL
- `SLACK_WEBHOOK_URL_INFO`: 情報通知用Slack Webhook URL

### 6.2 タイムアウトとメモリの設定

Lambda関数のタイムアウトとメモリを設定することで、関数の実行時間とリソース使用量を制御できます。

- タイムアウト: 300秒（5分）
- メモリ: 512MB

### 6.3 実行ロールの設定

Lambda関数の実行ロールを設定することで、関数がアクセスできるAWSリソースを制御できます。以下のポリシーを持つロールを作成します：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

## 7. Lambda関数のスケジュール設定

### 7.1 EventBridge（CloudWatch Events）を使用したスケジュール設定

1. AWS Management Consoleにログイン
2. EventBridge サービスに移動
3. 「ルールの作成」をクリック
4. ルール名を入力（例：`fetch_daily_schedule`）
5. 「スケジュール」を選択
6. 「固定レート」または「Cron式」を選択
   - 固定レート: 1日ごと
   - Cron式: `0 1 * * ? *`（毎日午前1時に実行）
7. 「ターゲットの追加」をクリック
8. 「Lambda関数」を選択
9. 作成したLambda関数を選択
10. 「ルールの作成」をクリック

### 7.2 AWS CLIを使用したスケジュール設定

```bash
# EventBridgeルールの作成
aws events put-rule \
  --name fetch_daily_schedule \
  --schedule-expression "cron(0 1 * * ? *)" \
  --state ENABLED

# Lambda関数をターゲットとして追加
aws events put-targets \
  --rule fetch_daily_schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:123456789012:function:fetch_daily_lambda"

# Lambda関数にEventBridgeからの呼び出し許可を追加
aws lambda add-permission \
  --function-name fetch_daily_lambda \
  --statement-id fetch_daily_schedule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:123456789012:rule/fetch_daily_schedule
```

## 8. Lambda関数のテスト

### 8.1 AWS Management Consoleを使用したテスト

1. AWS Management Consoleにログイン
2. Lambda サービスに移動
3. 作成したLambda関数を選択
4. 「テスト」タブをクリック
5. テストイベント名を入力（例：`test_event`）
6. テストイベントJSONを入力（空のJSONオブジェクト `{}` でも可）
7. 「テストの実行」をクリック
8. 実行結果とログを確認

### 8.2 AWS CLIを使用したテスト

```bash
# Lambda関数の呼び出し
aws lambda invoke \
  --function-name fetch_daily_lambda \
  --payload '{}' \
  output.json

# 実行結果の確認
cat output.json
```

### 8.3 テストイベント（`test_event.json`）

```json
{
  "source": "aws.events",
  "time": "2023-01-01T01:00:00Z",
  "detail-type": "Scheduled Event",
  "resources": [
    "arn:aws:events:us-east-1:123456789012:rule/fetch_daily_schedule"
  ],
  "detail": {}
}
```

## 9. Lambda関数のモニタリングとトラブルシューティング

### 9.1 CloudWatch Logsを使用したログの確認

1. AWS Management Consoleにログイン
2. CloudWatch サービスに移動
3. 「ロググループ」をクリック
4. `/aws/lambda/fetch_daily_lambda` ロググループを選択
5. 最新のログストリームを選択
6. ログを確認

### 9.2 CloudWatch Metricsを使用したメトリクスの確認

1. AWS Management Consoleにログイン
2. CloudWatch サービスに移動
3. 「メトリクス」をクリック
4. 「Lambda」名前空間を選択
5. 「関数名」ディメンションを選択
6. 作成したLambda関数のメトリクスを確認
   - Invocations: 呼び出し回数
   - Errors: エラー回数
   - Duration: 実行時間
   - Throttles: スロットル回数
   - ConcurrentExecutions: 同時実行数

### 9.3 一般的なエラーと解決策

1. **タイムアウトエラー**:
   - 症状: 関数の実行時間がタイムアウト設定を超えた
   - 解決策: タイムアウト設定を増やす、または処理を最適化する

2. **メモリ不足エラー**:
   - 症状: 関数の実行中にメモリ不足が発生した
   - 解決策: メモリ設定を増やす、または処理を最適化する

3. **権限エラー**:
   - 症状: 関数がAWSリソース（S3など）にアクセスできない
   - 解決策: 実行ロールに適切な権限を追加する

4. **インポートエラー**:
   - 症状: 関数が必要なモジュールをインポートできない
   - 解決策: デプロイパッケージに必要なライブラリを含める

5. **API制限エラー**:
   - 症状: Alpha Vantage APIの制限に達した
   - 解決策: API呼び出しの頻度を下げる、または有料プランにアップグレードする

## 10. Lambda関数の利点

AWS Lambdaを使用することで、以下のような利点があります：

1. **サーバーレス**: サーバーのプロビジョニングや管理が不要
2. **スケーラビリティ**: 自動的にスケールアップ/ダウン
3. **コスト効率**: 使用した分だけ支払い
4. **高可用性**: AWSによる高可用性の保証
5. **イベント駆動**: イベントに基づいて自動的に実行
6. **統合**: 他のAWSサービスとの簡単な統合

## 11. 設計のポイント

1. **モジュール化**: Lambda関数のハンドラーと実際の処理ロジックを分離しています。

2. **エラーハンドリング**: 詳細なエラー情報を含むレスポンスを返すことで、トラブルシューティングを容易にしています。

3. **環境変数**: 環境変数を使用して、関数の動作をカスタマイズしています。

4. **ロギング**: 詳細なログを出力することで、関数の実行状況を追跡できます。

5. **タイムアウトとメモリ**: 適切なタイムアウトとメモリ設定により、関数の実行時間とリソース使用量を制御しています。

6. **スケジュール**: EventBridgeを使用して、関数を定期的に実行するスケジュールを設定しています。

## 12. 練習問題

1. Lambda関数を拡張して、特定の銘柄のみを処理するパラメータを追加してみましょう。

2. Lambda関数を拡張して、処理結果をSNSトピックに発行するようにしてみましょう。

3. Lambda関数を拡張して、CloudWatch Metricsにカスタムメトリクスを発行するようにしてみましょう。

4. Lambda関数を拡張して、S3バケットにオブジェクトが追加されたときに実行されるようにしてみましょう。

## 13. 参考資料

- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html): AWS Lambdaの公式ドキュメント
- [AWS Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html): AWS Lambda Python ランタイムのドキュメント
- [AWS EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html): AWS EventBridgeの公式ドキュメント
- [AWS CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html): AWS CloudWatchの公式ドキュメント
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html): AWS CLIの公式ドキュメント
