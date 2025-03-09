# AWS Lambdaを使った株価データ取得バッチの実装

このドキュメントでは、AWS Lambdaを使って`fetch_daily.py`を毎朝7時に実行するバッチ処理の実装方法について説明します。

## 前提条件

- AWSアカウントを持っていること
- AWS CLIがインストールされていること
- AWS CLIの認証情報が設定されていること

## 1. IAM権限の設定

Lambda関数には以下の権限が必要です：

1. **S3へのアクセス権限**：株価データをS3に保存するため
2. **CloudWatchへのアクセス権限**：ログを出力するため
3. **Lambda実行権限**：Lambda関数を実行するため

### IAMポリシーの作成

以下のIAMポリシーを作成します：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::s3-data-uploader-bucket",
        "arn:aws:s3:::s3-data-uploader-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### IAMロールの作成

1. AWSマネジメントコンソールにログインします
2. IAMサービスを選択します
3. 「ロール」を選択し、「ロールの作成」をクリックします
4. 「AWS サービス」を選択し、「Lambda」を選択します
5. 上記で作成したポリシーをアタッチします
6. ロール名を「FetchDailyLambdaRole」などとして作成します

## 2. Lambda関数のデプロイパッケージの作成

Lambda関数をデプロイするには、必要なファイルをパッケージ化する必要があります。

### デプロイパッケージの作成手順

1. 必要なファイルをコピーするディレクトリを作成します

```bash
mkdir -p lambda/package
```

2. 必要なファイルをコピーします

```bash
cp -r src lambda/package/
cp lambda/fetch_daily_lambda.py lambda/package/
```

3. 必要なライブラリをインストールします

```bash
pip install -r requirements.txt -t lambda/package/
```

4. デプロイパッケージを作成します

```bash
cd lambda/package
zip -r ../fetch_daily_lambda.zip .
cd ../..
```

## 3. Lambda関数の作成

### AWSマネジメントコンソールから作成する場合

1. AWSマネジメントコンソールにログインします
2. Lambda サービスを選択します
3. 「関数の作成」をクリックします
4. 「一から作成」を選択します
5. 関数名を「FetchDailyLambda」などとして入力します
6. ランタイムに「Python 3.9」を選択します
7. 「既存のロール」を選択し、上記で作成したロールを選択します
8. 「関数の作成」をクリックします
9. 「コード」タブで「アップロード元」を選択し、「.zip ファイル」を選択します
10. 上記で作成した`fetch_daily_lambda.zip`をアップロードします
11. 「保存」をクリックします
12. 「設定」タブで「一般設定」を選択し、「編集」をクリックします
13. タイムアウトを「5分」に設定します（必要に応じて調整）
14. メモリを「256 MB」に設定します（必要に応じて調整）
15. 「保存」をクリックします

### AWS CLIから作成する場合

```bash
aws lambda create-function \
  --function-name FetchDailyLambda \
  --runtime python3.9 \
  --role arn:aws:iam::<アカウントID>:role/FetchDailyLambdaRole \
  --handler fetch_daily_lambda.lambda_handler \
  --zip-file fileb://lambda/fetch_daily_lambda.zip \
  --timeout 300 \
  --memory-size 256
```

## 4. 環境変数の設定

Lambda関数に必要な環境変数を設定します。

### AWSマネジメントコンソールから設定する場合

1. Lambda関数の「設定」タブで「環境変数」を選択します
2. 「編集」をクリックします
3. 以下の環境変数を追加します：
   - `ALPHA_VANTAGE_API_KEY`: Alpha Vantage APIキー
   - `MOCK_MODE`: `False`（本番モード）
   - `SAVE_TO_S3`: `True`（S3に保存する）
   - `S3_BUCKET`: S3バケット名
   - `S3_PREFIX_PROD`: 本番用S3プレフィックス
   - `AWS_REGION`: AWSリージョン
4. 「保存」をクリックします

### AWS CLIから設定する場合

```bash
aws lambda update-function-configuration \
  --function-name FetchDailyLambda \
  --environment "Variables={ALPHA_VANTAGE_API_KEY=<APIキー>,MOCK_MODE=False,SAVE_TO_S3=True,S3_BUCKET=s3-data-uploader-bucket,S3_PREFIX_PROD=stock-data-prod,AWS_REGION=ap-northeast-1}"
```

## 5. EventBridgeを使ったスケジュール設定

Lambda関数を毎朝7時に実行するようにスケジュールを設定します。

### AWSマネジメントコンソールから設定する場合

1. Lambda関数の「設定」タブで「トリガー」を選択します
2. 「トリガーを追加」をクリックします
3. トリガーの設定で「EventBridge (CloudWatch Events)」を選択します
4. 「新規ルールの作成」を選択します
5. ルール名を「FetchDailyLambdaSchedule」などとして入力します
6. ルールタイプで「スケジュール式」を選択します
7. スケジュール式に `cron(0 22 * * ? *)` を入力します（UTC時間で22時 = 日本時間で朝7時）
8. 「追加」をクリックします

### AWS CLIから設定する場合

```bash
aws events put-rule \
  --name FetchDailyLambdaSchedule \
  --schedule-expression "cron(0 22 * * ? *)" \
  --state ENABLED

aws events put-targets \
  --rule FetchDailyLambdaSchedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:<リージョン>:<アカウントID>:function:FetchDailyLambda"

aws lambda add-permission \
  --function-name FetchDailyLambda \
  --statement-id FetchDailyLambdaSchedule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<リージョン>:<アカウントID>:rule/FetchDailyLambdaSchedule
```

## 6. Lambda関数のテスト実行

### AWSマネジメントコンソールからテスト実行する場合

1. Lambda関数の「テスト」タブを選択します
2. 「テストイベント」で「新しいテストイベント」を選択します
3. テストイベント名を「TestEvent」などとして入力します
4. テストイベントの内容はデフォルトのままでOKです
5. 「保存」をクリックします
6. 「テスト」をクリックします
7. 実行結果を確認します

### AWS CLIからテスト実行する場合

```bash
aws lambda invoke \
  --function-name FetchDailyLambda \
  --payload '{}' \
  output.json
```

## 7. CloudWatchでログを確認

Lambda関数の実行ログはCloudWatchで確認できます。

1. AWSマネジメントコンソールにログインします
2. CloudWatchサービスを選択します
3. 「ロググループ」を選択します
4. `/aws/lambda/FetchDailyLambda`を選択します
5. 最新のログストリームを選択します
6. ログを確認します

## 8. トラブルシューティング

### Lambda関数がタイムアウトする場合

- Lambda関数のタイムアウト設定を長くします（最大15分）
- メモリ割り当てを増やします（処理速度が向上します）

### S3へのアクセスエラーが発生する場合

- IAMロールのS3アクセス権限を確認します
- S3バケット名が正しいか確認します
- S3バケットのポリシーを確認します

### APIキーのエラーが発生する場合

- 環境変数に正しいAPIキーが設定されているか確認します
- APIキーの制限に達していないか確認します
