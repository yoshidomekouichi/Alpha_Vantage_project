# AWS Lambdaを使った株価データ取得バッチの実装

このドキュメントでは、AWS Lambdaを使って`fetch_daily.py`を毎朝7時に実行するバッチ処理の実装方法について説明します。

## 目次

1. [AWS管理コンソールからLambda関数を作成する手順](aws_console_instructions.md)
2. [Lambda関数のスケジュール設定](schedule_settings.md)
3. [Lambda関数のデプロイパッケージを更新する手順](update_deployment_package.md)
4. [Lambda関数のモニタリングとトラブルシューティング](monitoring_troubleshooting.md)

## 概要

このプロジェクトでは、AWS Lambdaを使って`fetch_daily.py`スクリプトを毎朝7時に自動実行するバッチ処理を実装します。これにより、Alpha Vantage APIから最新の株価データを取得し、AWS S3に保存する処理を自動化します。

## 実装の流れ

1. Lambda関数用のデプロイパッケージを作成します
2. AWS管理コンソールからLambda関数を作成します
3. Lambda関数に必要な環境変数を設定します
4. Lambda関数のIAMロールにS3アクセス権限を追加します
5. EventBridgeを使って毎朝7時に実行するようにスケジュールを設定します
6. テスト実行して動作確認します

## 前提条件

- AWSアカウントを持っていること
- AWS管理コンソールにアクセスできること
- Lambda関数を作成するための権限があること

## ファイル構成

- `fetch_daily_lambda.py`: Lambda関数のハンドラー
- `fetch_daily_lambda.zip`: Lambda関数のデプロイパッケージ
- `test_event.json`: Lambda関数のテスト用イベント
- `create_deployment_package.sh`: デプロイパッケージを作成するスクリプト
- `requirements_lambda.txt`: Lambda関数に必要なライブラリのリスト

## 詳細な手順

詳細な手順については、各ドキュメントを参照してください。

1. [AWS管理コンソールからLambda関数を作成する手順](aws_console_instructions.md)では、AWS管理コンソールを使ってLambda関数を作成する方法を説明しています。
2. [Lambda関数のスケジュール設定](schedule_settings.md)では、EventBridgeを使ってLambda関数を毎朝7時に実行するスケジュールを設定する方法を説明しています。
3. [Lambda関数のデプロイパッケージを更新する手順](update_deployment_package.md)では、Lambda関数のデプロイパッケージを更新する方法を説明しています。
4. [Lambda関数のモニタリングとトラブルシューティング](monitoring_troubleshooting.md)では、Lambda関数のモニタリング方法とトラブルシューティングについて説明しています。
