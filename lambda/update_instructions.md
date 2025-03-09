# Lambda関数の更新手順

環境変数の問題を解決するために、以下の変更を行いました：

1. `AWS_REGION`環境変数が予約語であるため、`CUSTOM_AWS_REGION`に変更しました
2. 以下のファイルを修正しました：
   - `src/config.py`
   - `src/core/config.py`
   - `lambda/package/config.py`
3. デプロイパッケージを再作成しました

## Lambda関数の更新手順

1. AWS管理コンソールにログインします
2. Lambda サービスを選択します
3. 「FetchDailyLambda」関数を選択します
4. 「コード」タブで「アップロード元」を選択し、「.zip ファイル」を選択します
5. 更新された`lambda/fetch_daily_lambda.zip`をアップロードします（ファイル名は元のデプロイパッケージと同じです）
6. 「保存」をクリックします

注意：デプロイパッケージのファイル名は変わっていません。create_deployment_package.shスクリプトを実行すると、同じ名前のファイル（lambda/fetch_daily_lambda.zip）が上書きされます。

## 環境変数の確認

1. 「設定」タブで「環境変数」を選択します
2. 以下の環境変数が設定されていることを確認します：
   - `ALPHA_VANTAGE_API_KEY`: Alpha Vantage APIキー
   - `MOCK_MODE`: `False`（本番モード）
   - `SAVE_TO_S3`: `True`（S3に保存する）
   - `S3_BUCKET`: `s3-data-uploader-bucket`
   - `S3_PREFIX_PROD`: `stock-data-prod`
   - `CUSTOM_AWS_REGION`: `ap-northeast-1`（AWS_REGIONの代わりに使用）

## テスト実行

1. Lambda関数の「テスト」タブを選択します
2. 「テスト」をクリックします
3. 実行結果を確認します
4. CloudWatchログで詳細を確認します

## トラブルシューティング

もし問題が発生した場合は、以下を確認してください：

1. 環境変数が正しく設定されているか
2. デプロイパッケージが正しくアップロードされているか
3. CloudWatchログでエラーメッセージを確認する
