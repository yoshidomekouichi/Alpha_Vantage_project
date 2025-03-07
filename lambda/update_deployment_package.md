# Lambda関数のデプロイパッケージを更新する手順

このドキュメントでは、Lambda関数のデプロイパッケージ（`fetch_daily_lambda.zip`）を更新する手順を説明します。

## デプロイパッケージの更新手順

1. ソースコードを変更した場合は、デプロイパッケージを再作成する必要があります。
2. 以下のコマンドを実行して、デプロイパッケージを再作成します：

```bash
# プロジェクトのルートディレクトリで実行
./lambda/create_deployment_package.sh
```

3. このコマンドにより、`lambda/fetch_daily_lambda.zip`ファイルが更新されます。
4. 更新されたデプロイパッケージをAWS管理コンソールからLambda関数にアップロードします：
   - Lambda関数の「コード」タブで「アップロード元」を選択し、「.zip ファイル」を選択します
   - 更新された`lambda/fetch_daily_lambda.zip`をアップロードします
   - 「保存」をクリックします

## 環境変数の設定

Lambda関数の環境変数に以下の設定を追加してください：

```
SLACK_ENABLED=true
SLACK_WEBHOOK_URL_ERROR=https://hooks.slack.com/services/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
SLACK_WEBHOOK_URL_WARNING=https://hooks.slack.com/services/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
SLACK_WEBHOOK_URL_INFO=https://hooks.slack.com/services/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
```

これらの環境変数は、Lambda関数がSlackに通知を送信するために必要です。

## デプロイパッケージの内容を確認する方法

デプロイパッケージの内容を確認するには、以下のコマンドを実行します：

```bash
# zipファイルの内容を一覧表示
unzip -l lambda/fetch_daily_lambda.zip
```

## デプロイパッケージのサイズを最適化する方法

デプロイパッケージのサイズが大きすぎる場合は、以下の方法でサイズを最適化できます：

1. 不要なライブラリを削除する
2. 必要なライブラリのみをインストールする
3. ソースコードから不要なファイル（テストファイルなど）を削除する

`requirements_lambda.txt`ファイルを編集して、必要なライブラリのみを指定することで、デプロイパッケージのサイズを削減できます。

## 更新後の動作確認

デプロイパッケージを更新した後は、以下の手順で動作確認を行ってください：

1. Lambda関数のテスト機能を使用して、関数を実行します。
2. CloudWatchログを確認して、関数が正常に実行されたことを確認します。
3. Slackの各チャンネルに通知が送信されたことを確認します：
   - #system-errors：エラー通知
   - #data-warnings：警告通知
   - #daily-updates：成功通知
