# Alpha Vantage Lambda関数

このディレクトリには、Alpha Vantage APIから株式データを取得し、S3に保存するLambda関数のコードとデプロイスクリプトが含まれています。

## 概要

Lambda関数は、Alpha Vantage APIから株式データを取得し、S3バケットに保存します。この関数は、CloudWatchイベントによって定期的にトリガーされるように設定することができます。

### ディレクトリ構造

```
lambda/
├── function/             # Lambda関数のコード
│   └── lambda_function.py  # Lambda関数のハンドラー
├── deploy.sh             # デプロイスクリプト
└── README.md             # このファイル
```

## デプロイ方法

### 前提条件

- AWS CLIがインストールされていること
- AWS認証情報が設定されていること
- Python 3.9以上がインストールされていること
- Lambda関数用のIAMロールが作成されていること

### IAMロールの作成

Lambda関数を実行するには、適切な権限を持つIAMロールが必要です。以下の手順でIAMロールを作成してください。

1. IAMコンソールで「ロール」を選択し、「ロールの作成」をクリックします。
2. 「AWS サービス」を選択し、「Lambda」を選択して「次へ」をクリックします。
3. アクセス許可ポリシーとして「AWSLambdaBasicExecutionRole」を選択します。
4. ロール名を入力（例: `lambda-alpha-vantage-role`）し、「ロールの作成」をクリックします。
5. 作成したロールを選択し、「インラインポリシーを追加」をクリックします。
6. JSONタブを選択し、`lambda/iam_policy.json`の内容をコピーして貼り付けます。
7. 以下の変数を実際の値に置き換えます：
   - `${S3_BUCKET}`: S3バケット名（例: `alpha-vantage-data`）
   - `${AWS_REGION}`: AWSリージョン（例: `ap-northeast-1`）
   - `${ACCOUNT_ID}`: AWSアカウントID
8. 「ポリシーの確認」をクリックし、ポリシー名を入力（例: `alpha-vantage-s3-access`）して「ポリシーの作成」をクリックします。

### デプロイ手順

1. デプロイスクリプトを実行して、Lambda関数とレイヤーのデプロイパッケージを作成します。

```bash
./lambda/deploy.sh
```

このスクリプトは以下の処理を行います：
- Lambda関数のコードをデプロイパッケージにコピー
- srcディレクトリのコードをデプロイパッケージにコピー
- デプロイパッケージをZIPファイルに圧縮
- 依存ライブラリをレイヤーパッケージにインストール
- レイヤーパッケージをZIPファイルに圧縮
- プロジェクトの.envファイルから環境変数を読み込み

2. AWS Management ConsoleまたはAWS CLIを使用して、Lambda関数とレイヤーをデプロイします。

スクリプト実行後、AWS CLIを使用したデプロイコマンドが表示されます。これらのコマンドを使用して、Lambda関数とレイヤーをデプロイすることができます。

### 定期実行の設定

Lambda関数を定期的に実行するには、CloudWatchイベントルールを設定します。

#### AWS Management Consoleを使用する場合

1. CloudWatchコンソールで「ルール」を選択し、「ルールの作成」をクリックします。
2. 「イベントソース」で「スケジュール」を選択します。
3. 「固定レート」を選択し、実行間隔を設定します（例: 1日）。
   または、「Cron式」を選択し、特定の時間に実行するように設定します（例: `0 0 * * ? *` で毎日午前0時に実行）。
4. 「ターゲット」で「Lambda関数」を選択し、作成したLambda関数を選択します。
5. 「ルールの詳細を設定」をクリックし、ルール名と説明を入力して「ルールの作成」をクリックします。

#### AWS CLIを使用する場合

```bash
# CloudWatchイベントルールを作成（毎日午前9時に実行）
aws events put-rule \
  --name alpha-vantage-daily-fetch-rule \
  --schedule-expression "cron(0 9 * * ? *)" \
  --state ENABLED

# Lambda関数をターゲットとして設定
aws events put-targets \
  --rule alpha-vantage-daily-fetch-rule \
  --targets "Id"="1","Arn"="arn:aws:lambda:<リージョン>:<アカウントID>:function:alpha-vantage-daily-fetch"

# Lambda関数にCloudWatchイベントからの呼び出し許可を追加
aws lambda add-permission \
  --function-name alpha-vantage-daily-fetch \
  --statement-id alpha-vantage-daily-fetch-rule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<リージョン>:<アカウントID>:rule/alpha-vantage-daily-fetch-rule
```

## 環境変数

Lambda関数は以下の環境変数を使用します：

- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage APIキー
- `S3_BUCKET`: 株式データを保存するS3バケット名
- `AWS_REGION`: AWSリージョン（デフォルト: ap-northeast-1）
- `STOCK_SYMBOLS`: 取得する株式シンボル（カンマ区切り）
- `MOCK_MODE`: モックモードを有効にするかどうか（true/false）
- `DEBUG_MODE`: デバッグモードを有効にするかどうか（true/false）
- `SLACK_ENABLED`: Slack通知を有効にするかどうか（true/false）
- `SLACK_WEBHOOK_URL`: Slack Webhook URL

### 環境変数の設定方法

プロジェクトのルートディレクトリに`.env`ファイルを作成し、必要な環境変数を設定します。デプロイスクリプトは、このファイルから環境変数を読み込み、Lambda関数の環境変数として設定します。

```
ALPHA_VANTAGE_API_KEY=your_api_key
S3_BUCKET=your_bucket_name
AWS_REGION=ap-northeast-1
STOCK_SYMBOLS=NVDA,AAPL,MSFT
MOCK_MODE=false
DEBUG_MODE=false
SLACK_ENABLED=false
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

## トラブルシューティング

### Lambda関数のデプロイに失敗する場合

- AWS認証情報が正しく設定されているか確認してください
- IAMロールに必要な権限が付与されているか確認してください
- デプロイパッケージのサイズが50MB以下であることを確認してください

### Lambda関数の実行に失敗する場合

- 環境変数が正しく設定されているか確認してください
- IAMロールにS3バケットへのアクセス権限が付与されているか確認してください
- CloudWatchログを確認して、エラーメッセージを確認してください

### Lambda関数のタイムアウトが発生する場合

- Lambda関数のタイムアウト設定を増やしてください（デフォルト: 3秒）
- メモリ割り当てを増やしてください（デフォルト: 128MB）

## 注意事項

- Lambda関数は、srcディレクトリのコードを使用します。srcディレクトリのコードを変更した場合は、Lambda関数を再デプロイする必要があります。
- Lambda関数のタイムアウトは、CloudWatchイベントのタイムアウトよりも短く設定してください。
- Lambda関数のメモリ割り当ては、処理するデータ量に応じて調整してください。
