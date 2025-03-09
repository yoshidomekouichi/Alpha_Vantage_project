# APIクライアントモジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのAPIクライアントモジュールについて説明します。

## 1. APIクライアントの概要

APIクライアントモジュールは、Alpha Vantage APIとの通信を担当し、株価データを取得します。主な機能は以下の通りです：

- Alpha Vantage APIへのリクエスト送信
- レスポンスの検証と解析
- エラーハンドリングとリトライ
- モックモードでのテストデータ生成

## 2. 主要なファイル

- `src/api/alpha_vantage/client.py`: Alpha Vantage APIクライアントの実装
- `src/utils/api_client.py`: 汎用APIクライアントユーティリティ（このプロジェクトでは使用されていない可能性があります）

## 3. `AlphaVantageClient`クラスの詳細

### 3.1 初期化

```python
def __init__(self, api_key: str, base_url: str = 'https://www.alphavantage.co/query'):
    """
    Alpha Vantage APIクライアントを初期化します。
    
    引数:
        api_key: Alpha Vantage APIキー
        base_url: Alpha Vantage APIのベースURL
    """
    self.api_key = api_key
    self.base_url = base_url
    self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
```

初期化時に、APIキーとベースURLを設定します。また、環境変数からモックモードの設定を読み込みます。

### 3.2 日次株価データの取得

```python
def fetch_daily_stock_data(self, symbol: str, outputsize: str = 'compact') -> Optional[Dict[str, Any]]:
    """
    指定された銘柄の日次株価データを取得します。
    
    引数:
        symbol: 株式銘柄（例：'NVDA'）
        outputsize: 'compact'は最新の100データポイント、'full'は最大20年分のデータ
        
    戻り値:
        株価データを含む辞書、またはエラー時はNone
    """
    if self.mock_mode:
        return self._get_mock_data(symbol, outputsize)
        
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": self.api_key,
        "outputsize": outputsize,
        "datatype": "json"
    }
    
    return self._make_api_request(params)
```

指定された銘柄の日次株価データを取得するメソッドです。モックモードの場合は、モックデータを生成して返します。それ以外の場合は、APIリクエストを送信します。

`outputsize`パラメータにより、取得するデータ量を制御できます：
- `compact`: 最新の100データポイント（デフォルト）
- `full`: 最大20年分のデータ

### 3.3 APIリクエストの送信

```python
def _make_api_request(self, params: Dict[str, str], max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    指数バックオフリトライを使用してAlpha Vantage APIにリクエストを送信します。
    
    引数:
        params: APIリクエストパラメータ
        max_retries: 最大リトライ回数
        
    戻り値:
        APIレスポンスデータ、またはすべてのリトライが失敗した場合はNone
    """
    retry_count = 0
    while retry_count <= max_retries:
        try:
            logger.debug(f"🛠 Making API request with params: {params}")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"🛠 API request URL: {response.url}")
            
            # レスポンス形式の検証
            if "Time Series (Daily)" not in data:
                error_msg = f"❌ API specification may have changed: 'Time Series (Daily)' key not found! Response: {data}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # サンプルデータポイントの検証
            sample_date = next(iter(data["Time Series (Daily)"]))
            sample_data = data["Time Series (Daily)"][sample_date]
            
            expected_keys = {"1. open", "2. high", "3. low", "4. close", "5. volume"}
            actual_keys = set(sample_data.keys())
            
            if actual_keys != expected_keys:
                error_msg = f"❌ API response format change detected! Expected: {expected_keys}, Actual: {actual_keys}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ API request error (attempt {retry_count+1}/{max_retries+1}): {e}")
        except ValueError as ve:
            logger.error(f"❌ API response validation error: {ve}")
            return None  # 検証エラーの場合はリトライしない
        except Exception as ex:
            logger.exception(f"❌ Unexpected error during API request: {ex}")
        
        # 指数バックオフとジッター
        if retry_count < max_retries:
            sleep_time = (2 ** retry_count) + random.uniform(0, 1)
            logger.info(f"⏱ Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
        retry_count += 1
    
    logger.error(f"❌ All {max_retries+1} API request attempts failed")
    return None
```

APIリクエストを送信し、レスポンスを検証するメソッドです。以下の特徴があります：

1. **指数バックオフリトライ**: リクエストが失敗した場合、指数関数的に増加する待機時間を挟んでリトライします。
2. **ジッター**: リトライ間隔にランダムな変動（ジッター）を加えることで、複数のクライアントが同時にリトライする場合の負荷を分散します。
3. **レスポンス検証**: APIレスポンスの形式が期待通りであることを確認します。
4. **タイムアウト設定**: リクエストのタイムアウトを10秒に設定しています。

### 3.4 モックデータの生成

```python
def _get_mock_data(self, symbol: str, outputsize: str) -> Dict[str, Any]:
    """
    実際のAPIコールを行わずにテストするためのモックデータを生成します。
    
    引数:
        symbol: 株式銘柄
        outputsize: 'compact'または'full'
        
    戻り値:
        モック株価データ
    """
    logger.info(f"🔍 Using MOCK data for {symbol} (outputsize: {outputsize})")
    
    # 日付の生成（今日と過去の日付）
    from datetime import datetime, timedelta
    today = datetime.now()
    
    # 生成するデータ日数の決定
    num_days = 100 if outputsize == 'compact' else 500
    
    # モック時系列データの生成
    time_series = {}
    base_price = 100.0  # 開始価格
    
    for i in range(num_days):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        
        # 価格変動の生成
        daily_change = random.uniform(-5, 5)
        open_price = base_price + daily_change
        high_price = open_price * random.uniform(1.0, 1.05)
        low_price = open_price * random.uniform(0.95, 1.0)
        close_price = random.uniform(low_price, high_price)
        volume = int(random.uniform(1000000, 10000000))
        
        # 次の反復のための基本価格の更新
        base_price = close_price
        
        # APIが返す形式でフォーマット
        time_series[date] = {
            "1. open": f"{open_price:.4f}",
            "2. high": f"{high_price:.4f}",
            "3. low": f"{low_price:.4f}",
            "4. close": f"{close_price:.4f}",
            "5. volume": f"{volume}"
        }
    
    # 完全なレスポンス構造の作成
    mock_data = {
        "Meta Data": {
            "1. Information": f"Daily Prices (open, high, low, close) and Volumes",
            "2. Symbol": symbol,
            "3. Last Refreshed": today.strftime('%Y-%m-%d'),
            "4. Output Size": outputsize,
            "5. Time Zone": "US/Eastern"
        },
        "Time Series (Daily)": time_series
    }
    
    return mock_data
```

モックモード用のテストデータを生成するメソッドです。実際のAPIを呼び出さずにテストできるようにするために使用されます。以下の特徴があります：

1. **現実的なデータ生成**: ランダムな価格変動を持つ、現実的な株価データを生成します。
2. **日付の生成**: 現在の日付から過去に遡って、指定された日数分のデータを生成します。
3. **APIレスポンス形式の模倣**: 実際のAPIレスポンスと同じ形式でデータを返します。

## 4. APIレスポンスの形式

Alpha Vantage APIの日次株価データのレスポンス形式は以下の通りです：

```json
{
  "Meta Data": {
    "1. Information": "Daily Prices (open, high, low, close) and Volumes",
    "2. Symbol": "NVDA",
    "3. Last Refreshed": "2023-01-01",
    "4. Output Size": "Compact",
    "5. Time Zone": "US/Eastern"
  },
  "Time Series (Daily)": {
    "2023-01-01": {
      "1. open": "150.0000",
      "2. high": "155.0000",
      "3. low": "148.0000",
      "4. close": "152.0000",
      "5. volume": "10000000"
    },
    "2022-12-31": {
      "1. open": "148.0000",
      "2. high": "152.0000",
      "3. low": "147.0000",
      "4. close": "150.0000",
      "5. volume": "9500000"
    },
    // ... 他の日付のデータ
  }
}
```

## 5. エラーハンドリングとリトライ戦略

APIクライアントは、以下のエラーハンドリングとリトライ戦略を実装しています：

1. **ネットワークエラー**: リクエストの送信に失敗した場合、指数バックオフでリトライします。
2. **HTTPエラー**: サーバーがエラーステータスコードを返した場合、同様にリトライします。
3. **レスポンス検証エラー**: レスポンスの形式が期待と異なる場合、リトライせずにエラーを返します。
4. **タイムアウト**: リクエストが10秒以内に完了しない場合、タイムアウトエラーとなり、リトライします。

指数バックオフリトライ戦略は、以下のように動作します：

1. 1回目のリトライ: 2^0 + ジッター = 1〜2秒待機
2. 2回目のリトライ: 2^1 + ジッター = 2〜3秒待機
3. 3回目のリトライ: 2^2 + ジッター = 4〜5秒待機

ジッターは0〜1秒のランダムな値で、複数のクライアントが同時にリトライする場合の「サンダーヘード問題」を回避するために使用されます。

## 6. APIクライアントの使用例

```python
# 設定の読み込み
from src.config import Config
config = Config()

# APIクライアントの初期化
from src.api.alpha_vantage.client import AlphaVantageClient
client = AlphaVantageClient(config.api_key, config.api_base_url)

# ロガーの設定
import logging
logger = logging.getLogger("my_logger")
client.set_logger(logger)

# 日次株価データの取得（最新100日分）
data = client.fetch_daily_stock_data("NVDA", outputsize="compact")

# 日次株価データの取得（全履歴）
historical_data = client.fetch_daily_stock_data("AAPL", outputsize="full")

# モックモードでのテスト
import os
os.environ['MOCK_MODE'] = 'True'
mock_client = AlphaVantageClient("dummy_key")
mock_data = mock_client.fetch_daily_stock_data("MSFT")
```

## 7. 設計のポイント

1. **モックモードのサポート**: テスト用のモックモードをサポートすることで、実際のAPIを呼び出さずにテストできるようにしています。

2. **堅牢なエラーハンドリング**: ネットワークエラー、HTTPエラー、レスポンス検証エラーなど、様々なエラーに対応しています。

3. **指数バックオフリトライ**: APIリクエストが失敗した場合、指数関数的に増加する待機時間を挟んでリトライすることで、一時的な問題を回避します。

4. **レスポンス検証**: APIレスポンスの形式が期待通りであることを確認することで、APIの仕様変更に対応しています。

5. **カスタムロガー**: ロガーをカスタマイズできるようにすることで、アプリケーション全体で一貫したロギングを実現しています。

## 8. Alpha Vantage APIの制限

Alpha Vantage APIには以下の制限があります：

1. **リクエスト制限**: 無料APIキーでは、1分間に5リクエスト、1日に500リクエストの制限があります。
2. **データ範囲**: `outputsize=compact`では最新の100データポイント、`outputsize=full`では最大20年分のデータを取得できます。
3. **対応銘柄**: 米国株式市場の主要銘柄に対応していますが、すべての銘柄が利用可能とは限りません。

これらの制限に対応するため、APIクライアントはリトライ戦略を実装し、モックモードをサポートしています。

## 9. 練習問題

1. APIクライアントを使用して、特定の銘柄の株価データを取得してみましょう。

2. モックモードを有効にして、APIを呼び出さずにテストデータを生成してみましょう。

3. リトライ回数やタイムアウト時間などのパラメータをカスタマイズしてみましょう。

4. 新しいAPIエンドポイント（例：週次データ、月次データなど）をサポートするようにクライアントを拡張してみましょう。

## 10. 参考資料

- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/): Alpha Vantage APIの公式ドキュメント
- [Requests: HTTP for Humans](https://requests.readthedocs.io/): Pythonの人気HTTPクライアントライブラリ
- [Exponential Backoff And Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/): AWSによる指数バックオフとジッターの解説
