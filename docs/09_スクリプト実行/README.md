# スクリプト実行モジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのスクリプト実行モジュールについて説明します。

## 1. スクリプト実行モジュールの概要

スクリプト実行モジュールは、Alpha Vantage APIから株価データを取得し、処理して、AWS S3に保存するためのメインスクリプトを提供します。主な機能は以下の通りです：

- 日次株価データの取得と保存（`fetch_daily.py`）
- 過去の株価データの一括取得と保存（`fetch_bulk.py`）
- 各コンポーネント（API、データ処理、ストレージなど）の連携
- エラーハンドリングと結果の集計
- 実行結果の通知

## 2. 主要なファイル

- `src/fetch_daily.py`: 日次株価データ取得スクリプト
- `src/fetch_bulk.py`: 過去の株価データ一括取得スクリプト
- `src/scripts/fetch_daily.py`: 日次データ取得スクリプト（代替実装）
- `src/scripts/fetch_bulk.py`: 過去データ取得スクリプト（代替実装）

## 3. 日次データ取得スクリプト（`fetch_daily.py`）の詳細

### 3.1 スクリプトの構造

```python
#!/usr/bin/env python3
"""
Daily Stock Data Fetcher

This script fetches the latest daily stock data from Alpha Vantage API
and stores it in AWS S3. It is designed to be run as a daily batch job.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import traceback

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config
from src.utils.api_client import AlphaVantageClient
from src.utils.data_processing import StockDataProcessor
from src.utils.storage import S3Storage
from src.utils.atomic_s3 import AtomicS3
from src.utils.logging_utils import LoggerManager, log_execution_time
from src.utils.alerts import AlertManager

def setup_components(config):
    """コンポーネントを設定します。"""
    # ...（コンポーネントの初期化コード）

@log_execution_time(logging.getLogger(__name__))
def process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger):
    """単一の株式銘柄を処理します。"""
    # ...（銘柄処理コード）

def main():
    """メイン関数。"""
    # ...（メインロジック）

if __name__ == "__main__":
    # インポートの循環を避けるためにここでloggingをインポート
    import logging
    
    try:
        sys.exit(main())
    except Exception as e:
        # 予期しない例外をキャッチ
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)
```

スクリプトは、以下の主要な部分から構成されています：

1. **インポートと初期設定**: 必要なモジュールのインポートとプロジェクトルートのパス設定
2. **コンポーネント設定関数**: 各コンポーネント（ロガー、APIクライアント、データプロセッサなど）の初期化
3. **銘柄処理関数**: 単一の株式銘柄のデータ取得と処理
4. **メイン関数**: スクリプトのメインロジック
5. **エントリーポイント**: スクリプト実行時のエラーハンドリング

### 3.2 コンポーネントの設定

```python
def setup_components(config):
    """
    指定された設定でコンポーネントを設定します。
    
    引数:
        config: 設定オブジェクト
        
    戻り値:
        (logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager)のタプル
    """
    # ロガーの設定
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger_manager = LoggerManager(
        "fetch_daily",
        log_dir=config.log_dir,
        console_level=log_level,
        file_level=logging.DEBUG,
        is_mock=config.mock_mode
    )
    logger = logger_manager.get_logger()
    
    # デバッグモードが設定されている場合は有効化
    if config.debug_mode:
        logger_manager.set_debug_mode(True)
    
    # 環境タイプをログに記録
    env_type = "Mock" if config.mock_mode else "Production"
    logger.info(f"🔧 Running in {env_type} environment")
    
    # APIクライアントの設定
    api_client = AlphaVantageClient(config.api_key, config.api_base_url)
    api_client.set_logger(logger)
    
    # データプロセッサの設定
    data_processor = StockDataProcessor()
    data_processor.set_logger(logger)
    
    # S3ストレージの設定
    s3_storage = S3Storage(config.s3_bucket, config.s3_region)
    s3_storage.set_logger(logger)
    
    # アトミックS3更新の設定
    atomic_s3 = AtomicS3(s3_storage)
    atomic_s3.set_logger(logger)
    
    # アラートマネージャーの設定
    alert_manager = AlertManager(config.email_config, config.slack_webhook_url)
    alert_manager.set_logger(logger)
    
    return logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager
```

コンポーネント設定関数は、各コンポーネントを初期化し、連携させます。各行の処理内容は以下の通りです：

1. `log_level = getattr(logging, config.log_level.upper(), logging.INFO)`: 設定から指定されたログレベルを取得します。指定されていない場合はINFOレベルをデフォルトとします。
2. `logger_manager = LoggerManager(...)`: ロガーマネージャーを初期化します。
3. `"fetch_daily"`: ロガー名を指定します。
4. `log_dir=config.log_dir`: ログファイルの保存先ディレクトリを指定します。
5. `console_level=log_level`: コンソール出力のログレベルを設定します。
6. `file_level=logging.DEBUG`: ファイル出力のログレベルをDEBUGに設定します（詳細なログをファイルに記録）。
7. `is_mock=config.mock_mode`: モックモードの設定を渡します。
8. `logger = logger_manager.get_logger()`: 設定されたロガーインスタンスを取得します。
9. `if config.debug_mode:`: デバッグモードが有効かどうかをチェックします。
10. `logger_manager.set_debug_mode(True)`: デバッグモードを有効にします（コンソールのログレベルをDEBUGに設定）。
11. `env_type = "Mock" if config.mock_mode else "Production"`: 環境タイプの文字列を作成します。
12. `logger.info(f"🔧 Running in {env_type} environment")`: 環境タイプをログに記録します。
13. `api_client = AlphaVantageClient(config.api_key, config.api_base_url)`: APIクライアントを初期化します。
14. `api_client.set_logger(logger)`: APIクライアントにロガーを設定します。
15. `data_processor = StockDataProcessor()`: データプロセッサを初期化します。
16. `data_processor.set_logger(logger)`: データプロセッサにロガーを設定します。
17. `s3_storage = S3Storage(config.s3_bucket, config.s3_region)`: S3ストレージを初期化します。
18. `s3_storage.set_logger(logger)`: S3ストレージにロガーを設定します。
19. `atomic_s3 = AtomicS3(s3_storage)`: アトミックS3更新を初期化します。
20. `atomic_s3.set_logger(logger)`: アトミックS3更新にロガーを設定します。
21. `alert_manager = AlertManager(config.email_config, config.slack_webhook_url)`: アラートマネージャーを初期化します。
22. `alert_manager.set_logger(logger)`: アラートマネージャーにロガーを設定します。
23. `return logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager`: 初期化されたすべてのコンポーネントをタプルとして返します。

### 3.3 銘柄処理

```python
@log_execution_time(logging.getLogger(__name__))
def process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger):
    """
    単一の株式銘柄を処理します。
    
    引数:
        symbol: 処理する株式銘柄
        config: 設定オブジェクト
        api_client: Alpha Vantage APIクライアント
        data_processor: データプロセッサ
        atomic_s3: アトミックS3更新
        logger: ロガー
        
    戻り値:
        成功を示すブール値
    """
    logger.info(f"🔍 Processing symbol: {symbol}")
    
    # APIからデータを取得
    stock_data = api_client.fetch_daily_stock_data(symbol)
    
    if not stock_data:
        logger.error(f"❌ Failed to fetch data for {symbol}")
        return False
    
    # データの検証と変換
    is_valid, df = data_processor.validate_and_transform(stock_data)
    
    if not is_valid or df is None:
        logger.error(f"❌ Data validation failed for {symbol}")
        return False
    
    # 最新データポイントの抽出
    latest_df = data_processor.extract_latest_data(df)
    latest_date = latest_df.index[0].strftime('%Y-%m-%d')
    
    # JSONに変換
    json_data = data_processor.convert_to_json(df)
    latest_json_data = data_processor.convert_to_json(latest_df)
    
    # メタデータの追加
    json_data['symbol'] = symbol
    json_data['last_updated'] = datetime.now().isoformat()
    latest_json_data['symbol'] = symbol
    latest_json_data['last_updated'] = datetime.now().isoformat()
    
    # S3に保存
    full_key = config.get_s3_key(symbol)
    latest_key = config.get_s3_key(symbol, is_latest=True)
    daily_key = config.get_s3_key(symbol, date=latest_date)
    
    # 最新データをアトミックに保存
    if not atomic_s3.atomic_json_update(latest_key, latest_json_data):
        logger.error(f"❌ Failed to save latest data for {symbol}")
        return False
    
    # 日次データをアトミックに保存
    if not atomic_s3.atomic_json_update(daily_key, latest_json_data):
        logger.warning(f"⚠️ Failed to save daily data for {symbol}, but latest data was saved")
    
    # 全データをアトミックに更新
    if not atomic_s3.atomic_json_update(full_key, json_data):
        logger.warning(f"⚠️ Failed to update full data for {symbol}, but latest data was saved")
    
    # メタデータの更新
    metadata = {
        'symbol': symbol,
        'last_updated': datetime.now().isoformat(),
        'latest_date': latest_date,
        'data_points': len(df),
        'date_range': {
            'start': df.index[-1].strftime('%Y-%m-%d'),
            'end': latest_date
        }
    }
    
    metadata_key = config.get_metadata_key(symbol)
    if not atomic_s3.atomic_json_update(metadata_key, metadata):
        logger.warning(f"⚠️ Failed to update metadata for {symbol}")
    
    logger.info(f"✅ Successfully processed {symbol} for date {latest_date}")
    return True
```

銘柄処理関数は、単一の株式銘柄のデータを取得、処理、保存します。各行の処理内容は以下の通りです：

1. `@log_execution_time(logging.getLogger(__name__))`: 関数の実行時間をログに記録するデコレータを適用します。
2. `logger.info(f"🔍 Processing symbol: {symbol}")`: 処理開始をログに記録します。
3. `stock_data = api_client.fetch_daily_stock_data(symbol)`: APIから株価データを取得します。
4. `if not stock_data:`: データ取得に失敗した場合の処理です。
5. `logger.error(f"❌ Failed to fetch data for {symbol}")`: エラーをログに記録します。
6. `return False`: 失敗を示すFalseを返します。
7. `is_valid, df = data_processor.validate_and_transform(stock_data)`: 取得したデータを検証し、DataFrameに変換します。
8. `if not is_valid or df is None:`: データ検証に失敗した場合の処理です。
9. `logger.error(f"❌ Data validation failed for {symbol}")`: エラーをログに記録します。
10. `return False`: 失敗を示すFalseを返します。
11. `latest_df = data_processor.extract_latest_data(df)`: 最新の株価データを抽出します。
12. `latest_date = latest_df.index[0].strftime('%Y-%m-%d')`: 最新データの日付を文字列形式で取得します。
13. `json_data = data_processor.convert_to_json(df)`: 全データをJSON形式に変換します。
14. `latest_json_data = data_processor.convert_to_json(latest_df)`: 最新データをJSON形式に変換します。
15. `json_data['symbol'] = symbol`: 全データにシンボル情報を追加します。
16. `json_data['last_updated'] = datetime.now().isoformat()`: 全データに更新日時を追加します。
17. `latest_json_data['symbol'] = symbol`: 最新データにシンボル情報を追加します。
18. `latest_json_data['last_updated'] = datetime.now().isoformat()`: 最新データに更新日時を追加します。
19. `full_key = config.get_s3_key(symbol)`: 全データ用のS3キーを取得します。
20. `latest_key = config.get_s3_key(symbol, is_latest=True)`: 最新データ用のS3キーを取得します。
21. `daily_key = config.get_s3_key(symbol, date=latest_date)`: 日次データ用のS3キーを取得します。
22. `if not atomic_s3.atomic_json_update(latest_key, latest_json_data):`: 最新データの保存に失敗した場合の処理です。
23. `logger.error(f"❌ Failed to save latest data for {symbol}")`: エラーをログに記録します。
24. `return False`: 失敗を示すFalseを返します。
25. `if not atomic_s3.atomic_json_update(daily_key, latest_json_data):`: 日次データの保存に失敗した場合の処理です。
26. `logger.warning(f"⚠️ Failed to save daily data for {symbol}, but latest data was saved")`: 警告をログに記録します。
27. `if not atomic_s3.atomic_json_update(full_key, json_data):`: 全データの保存に失敗した場合の処理です。
28. `logger.warning(f"⚠️ Failed to update full data for {symbol}, but latest data was saved")`: 警告をログに記録します。
29. `metadata = {...}`: メタデータ辞書を作成します。
30. `'symbol': symbol`: シンボル情報を設定します。
31. `'last_updated': datetime.now().isoformat()`: 更新日時を設定します。
32. `'latest_date': latest_date`: 最新データの日付を設定します。
33. `'data_points': len(df)`: データポイント数を設定します。
34. `'date_range': {...}`: 日付範囲を設定します。
35. `'start': df.index[-1].strftime('%Y-%m-%d')`: 開始日を設定します。
36. `'end': latest_date`: 終了日を設定します。
37. `metadata_key = config.get_metadata_key(symbol)`: メタデータ用のS3キーを取得します。
38. `if not atomic_s3.atomic_json_update(metadata_key, metadata):`: メタデータの保存に失敗した場合の処理です。
39. `logger.warning(f"⚠️ Failed to update metadata for {symbol}")`: 警告をログに記録します。
40. `logger.info(f"✅ Successfully processed {symbol} for date {latest_date}")`: 処理成功をログに記録します。
41. `return True`: 成功を示すTrueを返します。

### 3.4 メイン関数

```python
def main():
    """メイン関数。"""
    start_time = time.time()
    
    # 設定の読み込み
    config = Config()
    
    # テスト用にモックモードを強制
    config.mock_mode = True
    config.debug_mode = True
    
    # コンポーネントの設定
    logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager = setup_components(config)
    
    # 実行開始をログに記録
    logger.info("=" * 80)
    logger.info(f"🚀 Starting daily stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"📋 Configuration: {config}")
    logger.info(f"🔍 Environment STOCK_SYMBOLS: {os.getenv('STOCK_SYMBOLS')}")
    logger.info(f"🔍 Config stock_symbols: {config.stock_symbols}")
    logger.info("=" * 80)
    
    # 各銘柄を処理
    results = {}
    success_count = 0
    failure_count = 0
    
    for symbol in config.stock_symbols:
        try:
            success = process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger)
            results[symbol] = "SUCCESS" if success else "FAILURE"
            
            if success:
                success_count += 1
            else:
                failure_count += 1
                
        except Exception as e:
            logger.exception(f"❌ Unexpected error processing {symbol}: {e}")
            results[symbol] = f"ERROR: {str(e)}"
            failure_count += 1
    
    # 実行時間の計算
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 実行サマリーをログに記録
    logger.info("=" * 80)
    logger.info(f"📊 Execution summary:")
    logger.info(f"⏱ Total execution time: {execution_time:.2f} seconds")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failure_count}")
    logger.info(f"📋 Results by symbol: {json.dumps(results, indent=2)}")
    logger.info("=" * 80)
    
    # 設定されている場合はアラートを送信
    if config.email_enabled or config.slack_enabled:
        if failure_count > 0:
            # 警告またはエラーアラートを送信
            alert_message = f"Daily stock data fetch completed with {failure_count} failures"
            alert_details = f"""
Execution time: {execution_time:.2f} seconds
Successful: {success_count}
Failed: {failure_count}

Results by symbol:
{json.dumps(results, indent=2)}
"""
            alert_manager.send_warning_alert(
                alert_message,
                alert_details,
                source="fetch_daily.py"
            )

### 3.4 メイン関数

```python
def main():
    """メイン関数。"""
    start_time = time.time()
    
    # 設定の読み込み
    config = Config()
    
    # テスト用にモックモードを強制
    config.mock_mode = True
    config.debug_mode = True
    
    # コンポーネントの設定
    logger, api_client, data_processor, s3_storage, atomic_s3, alert_manager = setup_components(config)
    
    # 実行開始をログに記録
    logger.info("=" * 80)
    logger.info(f"🚀 Starting daily stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"📋 Configuration: {config}")
    logger.info(f"🔍 Environment STOCK_SYMBOLS: {os.getenv('STOCK_SYMBOLS')}")
    logger.info(f"🔍 Config stock_symbols: {config.stock_symbols}")
    logger.info("=" * 80)
    
    # 各銘柄を処理
    results = {}
    success_count = 0
    failure_count = 0
    
    for symbol in config.stock_symbols:
        try:
            success = process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger)
            results[symbol] = "SUCCESS" if success else "FAILURE"
            
            if success:
                success_count += 1
            else:
                failure_count += 1
                
        except Exception as e:
            logger.exception(f"❌ Unexpected error processing {symbol}: {e}")
            results[symbol] = f"ERROR: {str(e)}"
            failure_count += 1
    
    # 実行時間の計算
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 実行サマリーをログに記録
    logger.info("=" * 80)
    logger.info(f"📊 Execution summary:")
    logger.info(f"⏱ Total execution time: {execution_time:.2f} seconds")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failure_count}")
    logger.info(f"📋 Results by symbol: {json.dumps(results, indent=2)}")
    logger.info("=" * 80)
    
    # 設定されている場合はアラートを送信
    if config.email_enabled or config.slack_enabled:
        if failure_count > 0:
            # 警告またはエラーアラートを送信
            alert_message = f"Daily stock data fetch completed with {failure_count} failures"
            alert_details = f"""
Execution time: {execution_time:.2f} seconds
Successful: {success_count}
Failed: {failure_count}

Results by symbol:
{json.dumps(results, indent=2)}
"""
            alert_manager.send_warning_alert(
                alert_message,
                alert_details,
                source="fetch_daily.py"
            )
        else:
            # 成功アラートを送信
            alert_message = f"Daily stock data fetch completed successfully"
            alert_details = f"""
Execution time: {execution_time:.2f} seconds
Processed symbols: {', '.join(config.stock_symbols)}
"""
            alert_manager.send_success_alert(
                alert_message,
                alert_details,
                source="fetch_daily.py"
            )
    
    # 終了コードを返す
    return 0 if failure_count == 0 else 1
```

メイン関数は、スクリプトの主要なロジックを実装しています。以下の手順で処理が行われます：

1. **設定読み込み**: 設定オブジェクトの作成
2. **コンポーネント設定**: 各コンポーネントの初期化
3. **実行開始ログ**: 実行開始情報のログ記録
4. **銘柄処理**: 各銘柄の処理と結果の追跡
5. **実行サマリー**: 実行結果のサマリーをログに記録
6. **通知送信**: 実行結果に基づいて通知を送信
7. **終了コード返却**: 成功/失敗に基づいて終了コードを返却

## 4. 過去データ一括取得スクリプト（`fetch_bulk.py`）の詳細

`fetch_bulk.py`スクリプトは、`fetch_daily.py`と同様の構造を持ちますが、過去の株価データを一括で取得するために設計されています。主な違いは以下の通りです：

1. **データ取得**: `outputsize="full"`パラメータを使用して、最大20年分のデータを取得します。
2. **個別日次データの保存**: オプションで、各日付の個別データファイルを保存できます。
3. **API制限の考慮**: API制限を回避するために、リクエスト間に遅延を挿入します。

```python
# APIからの完全な過去データの取得
logger.info(f"📥 Fetching full historical data for {symbol}")
stock_data = api_client.fetch_daily_stock_data(symbol, outputsize="full")

# 個別の日次データを保存（オプション）
save_individual = os.getenv('SAVE_INDIVIDUAL_DAYS', 'False').lower() == 'true'

if save_individual:
    for date, row in df.iterrows():
        date_str = date.strftime('%Y-%m-%d')
        daily_df = df.loc[[date]]
        daily_json = data_processor.convert_to_json(daily_df)
        daily_json['symbol'] = symbol
        daily_json['last_updated'] = datetime.now().isoformat()
        
        daily_key = config.get_s3_key(symbol, date=date_str)
        if not atomic_s3.atomic_json_update(daily_key, daily_json):
            logger.warning(f"⚠️ Failed to save daily data for {symbol} on {date_str}")

# API制限を回避するための遅延
if symbol != config.stock_symbols[0]:
    delay = 15  # APIコール間に15秒の遅延
    logger.info(f"⏱ Waiting {delay} seconds before processing next symbol to avoid API rate limits")
    time.sleep(delay)
```

## 5. スクリプトの実行方法

### 5.1 日次データ取得

```bash
# 基本的な実行
python src/fetch_daily.py

# 環境変数を設定して実行
STOCK_SYMBOLS=AAPL,MSFT,GOOGL DEBUG_MODE=true python src/fetch_daily.py

# モックモードで実行（APIコールなし）
MOCK_MODE=true python src/fetch_daily.py
```

### 5.2 過去データ一括取得

```bash
# 基本的な実行
python src/fetch_bulk.py

# 個別の日次データファイルも保存
SAVE_INDIVIDUAL_DAYS=true python src/fetch_bulk.py

# 特定の銘柄のみ処理
STOCK_SYMBOLS=NVDA,AMD python src/fetch_bulk.py
```

## 6. スクリプトの実行フロー

### 6.1 日次データ取得の実行フロー

```
1. 設定の読み込み
   ↓
2. コンポーネントの初期化（ロガー、APIクライアント、データプロセッサ、S3ストレージなど）
   ↓
3. 各銘柄の処理
   |
   ├─ 3.1. APIからデータ取得
   |   ↓
   ├─ 3.2. データの検証と変換
   |   ↓
   ├─ 3.3. 最新データの抽出
   |   ↓
   ├─ 3.4. JSONへの変換
   |   ↓
   └─ 3.5. S3への保存（最新、日次、全データ、メタデータ）
   ↓
4. 実行結果の集計
   ↓
5. 通知の送信（成功または警告/エラー）
   ↓
6. 終了コードの返却
```

### 6.2 過去データ一括取得の実行フロー

```
1. 設定の読み込み
   ↓
2. コンポーネントの初期化
   ↓
3. 各銘柄の処理
   |
   ├─ 3.1. APIから完全な過去データを取得（outputsize="full"）
   |   ↓
   ├─ 3.2. データの検証と変換
   |   ↓
   ├─ 3.3. 最新データの抽出
   |   ↓
   ├─ 3.4. JSONへの変換
   |   ↓
   ├─ 3.5. S3への保存（最新、全データ、メタデータ）
   |   ↓
   ├─ 3.6. （オプション）個別の日次データファイルの保存
   |   ↓
   └─ 3.7. API制限を回避するための遅延
   ↓
4. 実行結果の集計
   ↓
5. 通知の送信
   ↓
6. 終了コードの返却
```

## 7. エラーハンドリング

スクリプトは、以下のレベルでエラーハンドリングを実装しています：

1. **銘柄レベル**: 各銘柄の処理中にエラーが発生した場合、そのエラーはログに記録され、次の銘柄の処理に進みます。

```python
for symbol in config.stock_symbols:
    try:
        success = process_symbol(symbol, config, api_client, data_processor, atomic_s3, logger)
        # ...
    except Exception as e:
        logger.exception(f"❌ Unexpected error processing {symbol}: {e}")
        results[symbol] = f"ERROR: {str(e)}"
        failure_count += 1
```

2. **スクリプトレベル**: スクリプト全体で予期しない例外が発生した場合、その例外はキャッチされ、スタックトレースがログに記録されます。

```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)
```

3. **コンポーネントレベル**: 各コンポーネント（APIクライアント、データプロセッサなど）は、内部でエラーハンドリングを実装しています。

## 8. 通知

スクリプトは、実行結果に基づいて通知を送信します：

1. **成功通知**: すべての銘柄が正常に処理された場合、成功通知が送信されます。

```python
alert_manager.send_success_alert(
    message="Daily stock data fetch completed successfully",
    details=f"""
Execution time: {execution_time:.2f} seconds
Processed symbols: {', '.join(config.stock_symbols)}
""",
    source="fetch_daily.py"
)
```

2. **警告通知**: 一部の銘柄の処理に失敗した場合、警告通知が送信されます。

```python
alert_manager.send_warning_alert(
    warning_message=f"Daily stock data fetch completed with {failure_count} failures",
    warning_details=f"""
Execution time: {execution_time:.2f} seconds
Successful: {success_count}
Failed: {failure_count}

Results by symbol:
{json.dumps(results, indent=2)}
""",
    source="fetch_daily.py"
)
```

## 9. モックモードとデバッグモード

スクリプトは、以下の2つの特別なモードをサポートしています：

1. **モックモード**: APIコールを行わずに、モックデータを使用してスクリプトをテストできます。

```python
# 環境変数で設定
MOCK_MODE=true python src/fetch_daily.py

# またはコード内で設定
config.mock_mode = True
```

2. **デバッグモード**: より詳細なログ出力を有効にします。

```python
# 環境変数で設定
DEBUG_MODE=true python src/fetch_daily.py

# またはコード内で設定
config.debug_mode = True
```

## 10. 設計のポイント

1. **モジュール化**: 各機能（設定、API、データ処理、ストレージなど）が独立したモジュールに分割されています。

2. **エラーハンドリング**: 複数のレベルでエラーハンドリングが実装されています。

3. **ロギング**: 詳細なログ出力により、スクリプトの実行状況を追跡できます。

4. **通知**: メールやSlackによる通知機能により、実行結果を即座に確認できます。

5. **テスト容易性**: モックモードにより、実際のAPIコールを行わずにスクリプトをテストできます。

6. **設定の柔軟性**: 環境変数や設定ファイルにより、スクリプトの動作をカスタマイズできます。

7. **アトミック更新**: S3へのデータ保存にアトミック更新を使用することで、データの整合性を確保しています。

## 11. 練習問題

1. `fetch_daily.py`スクリプトを拡張して、特定の銘柄のみを処理するコマンドライン引数を追加してみましょう。

2. `fetch_bulk.py`スクリプトを拡張して、特定の日付範囲のデータのみを取得するオプションを追加してみましょう。

3. 両スクリプトに、処理の進捗状況を表示するプログレスバーを追加してみましょう。

4. エラーが発生した銘柄のみを再処理するスクリプトを作成してみましょう。

## 12. 参考資料

- [Python argparse](https://docs.python.org/3/library/argparse.html): コマンドライン引数の解析
- [Python logging](https://docs.python.org/3/library/logging.html): ロギング
- [Python datetime](https://docs.python.org/3/library/datetime.html): 日付と時間の操作
- [Python traceback](https://docs.python.org/3/library/traceback.html): 例外のスタックトレース
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/): Alpha Vantage APIのドキュメント
