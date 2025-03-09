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

初期化メソッドの各行は以下の処理を行います：

1. `self.api_key = api_key`: 引数で受け取ったAPIキーをインスタンス変数に保存します。このキーは後でAPIリクエストの認証に使用されます。
2. `self.base_url = base_url`: 引数で受け取ったベースURLをインスタンス変数に保存します。デフォルト値は'https://www.alphavantage.co/query'です。
3. `self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'`: 環境変数'MOCK_MODE'の値を読み取り、モックモードを有効にするかどうかを決定します。環境変数が設定されていない場合は'False'をデフォルト値として使用します。値を小文字に変換し、'true'と等しいかどうかをチェックします。

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

日次株価データ取得メソッドの各行は以下の処理を行います：

1. `if self.mock_mode:`: モックモードが有効かどうかをチェックします。モックモードはテスト時に実際のAPIを呼び出さずにダミーデータを使用するために使われます。
2. `return self._get_mock_data(symbol, outputsize)`: モックモードが有効な場合、内部メソッド`_get_mock_data`を呼び出してモックデータを生成し返します。
3. `params = {...}`: モックモードが無効な場合、APIリクエストに必要なパラメータを辞書として定義します：
   - `"function": "TIME_SERIES_DAILY"`: 日次株価データを取得するAPIエンドポイントを指定します。
   - `"symbol": symbol`: 引数で受け取った株式銘柄（例：'NVDA'）を指定します。
   - `"apikey": self.api_key`: 初期化時に保存したAPIキーを指定します。
   - `"outputsize": outputsize`: データ量を制御するパラメータを指定します（'compact'または'full'）。
   - `"datatype": "json"`: レスポンス形式としてJSONを指定します。
4. `return self._make_api_request(params)`: 内部メソッド`_make_api_request`を呼び出してAPIリクエストを送信し、結果を返します。

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

APIリクエスト送信メソッドの各行は以下の処理を行います：

1. `retry_count = 0`: リトライカウンターを0に初期化します。
2. `while retry_count <= max_retries:`: 最大リトライ回数に達するまでループします。
3. `try:`: 例外処理のためのtryブロックを開始します。
4. `logger.debug(f"🛠 Making API request with params: {params}")`: リクエストパラメータをデバッグログに出力します。
5. `response = requests.get(self.base_url, params=params, timeout=10)`: HTTPリクエストを送信します。タイムアウトは10秒に設定されています。
6. `response.raise_for_status()`: HTTPエラーがあれば例外を発生させます（400や500系のステータスコード）。
7. `data = response.json()`: レスポンスをJSON形式でパースします。
8. `logger.debug(f"🛠 API request URL: {response.url}")`: 実際に送信されたURLをデバッグログに出力します。
9. `if "Time Series (Daily)" not in data:`: レスポンスに必要なキーが含まれているか検証します。
10. `error_msg = f"❌ API specification may have changed: 'Time Series (Daily)' key not found! Response: {data}"`: エラーメッセージを作成します。
11. `logger.error(error_msg)`: エラーメッセージをログに出力します。
12. `raise ValueError(error_msg)`: 検証エラーを示す例外を発生させます。
13. `sample_date = next(iter(data["Time Series (Daily)"]))`: 最初の日付キーを取得します。
14. `sample_data = data["Time Series (Daily)"][sample_date]`: その日付のデータを取得します。
15. `expected_keys = {"1. open", "2. high", "3. low", "4. close", "5. volume"}`: 期待されるデータキーのセットを定義します。
16. `actual_keys = set(sample_data.keys())`: 実際のデータキーのセットを取得します。
17. `if actual_keys != expected_keys:`: 期待されるキーと実際のキーが一致するか検証します。
18. `error_msg = f"❌ API response format change detected! Expected: {expected_keys}, Actual: {actual_keys}"`: エラーメッセージを作成します。
19. `logger.error(error_msg)`: エラーメッセージをログに出力します。
20. `raise ValueError(error_msg)`: 検証エラーを示す例外を発生させます。
21. `return data`: すべての検証に合格した場合、データを返します。
22. `except requests.exceptions.RequestException as e:`: HTTPリクエスト関連の例外をキャッチします。
23. `logger.warning(f"❌ API request error (attempt {retry_count+1}/{max_retries+1}): {e}")`: 警告ログを出力します。
24. `except ValueError as ve:`: 検証エラーの例外をキャッチします。
25. `logger.error(f"❌ API response validation error: {ve}")`: エラーログを出力します。
26. `return None`: 検証エラーの場合はリトライせずにNoneを返します。
27. `except Exception as ex:`: その他の例外をキャッチします。
28. `logger.exception(f"❌ Unexpected error during API request: {ex}")`: 例外の詳細をログに出力します。
29. `if retry_count < max_retries:`: まだリトライ可能かチェックします。
30. `sleep_time = (2 ** retry_count) + random.uniform(0, 1)`: 指数バックオフとジッターを使用して待機時間を計算します。
31. `logger.info(f"⏱ Retrying in {sleep_time:.2f} seconds...")`: 待機時間をログに出力します。
32. `time.sleep(sleep_time)`: 計算された時間だけ待機します。
33. `retry_count += 1`: リトライカウンターをインクリメントします。
34. `logger.error(f"❌ All {max_retries+1} API request attempts failed")`: すべてのリトライが失敗した場合、エラーログを出力します。
35. `return None`: すべてのリトライが失敗した場合、Noneを返します。

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

モックデータ生成メソッドの各行は以下の処理を行います：

1. `logger.info(f"🔍 Using MOCK data for {symbol} (outputsize: {outputsize})")`: モックデータを使用していることをログに記録します。
2. `from datetime import datetime, timedelta`: 日付操作に必要なクラスをインポートします。
3. `today = datetime.now()`: 現在の日時を取得します。
4. `num_days = 100 if outputsize == 'compact' else 500`: 生成するデータポイントの数を決定します。'compact'なら100日分、それ以外なら500日分。
5. `time_series = {}`: 時系列データを格納する空の辞書を作成します。
6. `base_price = 100.0`: 開始価格を100.0に設定します。
7. `for i in range(num_days):`: 指定された日数分のデータを生成するループを開始します。
8. `date = (today - timedelta(days=i)).strftime('%Y-%m-%d')`: 現在の日付からi日前の日付を'YYYY-MM-DD'形式の文字列として生成します。
9. `daily_change = random.uniform(-5, 5)`: -5から5の間のランダムな価格変動を生成します。
10. `open_price = base_price + daily_change`: 基本価格に日々の変動を加えて始値を計算します。
11. `high_price = open_price * random.uniform(1.0, 1.05)`: 始値の1.0〜1.05倍の範囲でランダムな高値を生成します。
12. `low_price = open_price * random.uniform(0.95, 1.0)`: 始値の0.95〜1.0倍の範囲でランダムな安値を生成します。
13. `close_price = random.uniform(low_price, high_price)`: 安値と高値の間でランダムな終値を生成します。
14. `volume = int(random.uniform(1000000, 10000000))`: 100万〜1000万の間でランダムな取引量を生成します。
15. `base_price = close_price`: 次の日のための基本価格を今日の終値に更新します。
16. `time_series[date] = {...}`: 生成した価格データを日付をキーとして辞書に格納します。
17. `"1. open": f"{open_price:.4f}"`: 始値を小数点以下4桁でフォーマットします。
18. `"2. high": f"{high_price:.4f}"`: 高値を小数点以下4桁でフォーマットします。
19. `"3. low": f"{low_price:.4f}"`: 安値を小数点以下4桁でフォーマットします。
20. `"4. close": f"{close_price:.4f}"`: 終値を小数点以下4桁でフォーマットします。
21. `"5. volume": f"{volume}"`: 取引量を文字列に変換します。
22. `mock_data = {...}`: 完全なAPIレスポンス構造を作成します。
23. `"Meta Data": {...}`: メタデータ部分を作成します。
24. `"1. Information": f"Daily Prices (open, high, low, close) and Volumes"`: 情報説明を設定します。
25. `"2. Symbol": symbol`: 引数で受け取った銘柄シンボルを設定します。
26. `"3. Last Refreshed": today.strftime('%Y-%m-%d')`: 最終更新日を今日の日付に設定します。
27. `"4. Output Size": outputsize`: 出力サイズを引数で受け取った値に設定します。
28. `"5. Time Zone": "US/Eastern"`: タイムゾーンを米国東部時間に設定します。
29. `"Time Series (Daily)": time_series`: 生成した時系列データを設定します。
30. `return mock_data`: 作成したモックデータを返します。

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
