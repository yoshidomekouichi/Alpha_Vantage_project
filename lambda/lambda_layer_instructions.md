# Lambda Layerを使用してnumpyの問題を解決する手順

このドキュメントでは、AWS Lambda Layerを使用してnumpyのソースディレクトリからのインポート問題を解決する方法を説明します。

## 問題の概要

Lambda関数の実行時に以下のエラーが発生しています：

```
[ERROR] Runtime.ImportModuleError: Unable to import module 'fetch_daily_lambda': Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory; please exit the numpy source tree, and relaunch
        your python interpreter from there.
```

これは、numpyがソースディレクトリからインポートされようとしていることが原因です。この問題を解決するために、Lambda Layerを使用してnumpyとpandasを関数コードから分離します。

## Lambda Layerとは

Lambda Layerは、ライブラリ、カスタムランタイム、またはその他の依存関係を含むZIPアーカイブです。Layerを使用すると、デプロイパッケージのサイズを小さく保ちながら、Lambda関数で追加のコードやコンテンツを使用できます。

## 解決手順

### 1. Lambda Layerを作成する

作成したスクリプト `create_lambda_layer.sh` を実行して、numpyとpandasを含むLambda Layerを作成します：

```bash
cd /Users/koichi/Desktop/local_document/Alpha_Vantage_project
./lambda/create_lambda_layer.sh
```

このスクリプトは以下の処理を行います：

1. numpyとpandasを含むLambda Layer用のZIPファイル（`numpy_pandas_layer.zip`）を作成
2. numpyとpandasを除いたLambda関数用のデプロイパッケージ（`fetch_daily_lambda_without_numpy.zip`）を作成

### 2. AWS管理コンソールでLambda Layerを作成する

1. AWS管理コンソールにログインします
2. Lambda サービスを選択します
3. 左側のナビゲーションペインで「Layers」を選択します
4. 「Create layer」ボタンをクリックします
5. 以下の情報を入力します：
   - Name: `numpy-pandas-layer`
   - Description: `Layer containing numpy and pandas libraries`
   - Upload a .zip file: `lambda/numpy_pandas_layer.zip`をアップロード
   - Compatible runtimes: `Python 3.9`（または使用しているPythonバージョン）を選択
6. 「Create」ボタンをクリックします

### 3. Lambda関数にLayerをアタッチする

1. Lambda サービスで「Functions」を選択します
2. 「FetchDailyLambda」関数を選択します
3. 「Code」タブを選択します
4. 「Layers」セクションまでスクロールします
5. 「Add a layer」ボタンをクリックします
6. 「Custom layers」を選択します
7. 作成したLayer（`numpy-pandas-layer`）とバージョン（通常は1）を選択します
8. 「Add」ボタンをクリックします

### 4. Lambda関数のコードを更新する

1. Lambda サービスで「Functions」を選択します
2. 「FetchDailyLambda」関数を選択します
3. 「Code」タブを選択します
4. 「Upload from」を選択し、「.zip file」を選択します
5. 作成した`fetch_daily_lambda_without_numpy.zip`をアップロードします
6. 「Save」ボタンをクリックします

### 5. Lambda関数をテストする

1. Lambda サービスで「Functions」を選択します
2. 「FetchDailyLambda」関数を選択します
3. 「Test」タブを選択します
4. テストイベントを設定していない場合は、新しいテストイベントを作成します
5. 「Test」ボタンをクリックします
6. 実行結果を確認します

## トラブルシューティング

### Layer内のライブラリが見つからない場合

Lambda関数がLayer内のライブラリを見つけられない場合は、以下を確認してください：

1. Layerが正しくアタッチされているか
2. Layerのディレクトリ構造が正しいか（`python`ディレクトリ内にライブラリがあるか）
3. Lambda関数のランタイムとLayerの互換性があるか

### その他の依存関係の問題

numpyとpandasの依存関係に問題がある場合は、以下を試してください：

1. 特定のバージョンのnumpyとpandasを使用する（例：`numpy==1.26.4`, `pandas==2.2.3`）
2. 依存関係の競合を避けるために、他のライブラリとの互換性を確認する

## 参考情報

- [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Using Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/invocation-layers.html)
- [Best Practices for Working with AWS Lambda Layers](https://aws.amazon.com/blogs/compute/best-practices-for-using-lambda-layers-in-serverless-applications/)
