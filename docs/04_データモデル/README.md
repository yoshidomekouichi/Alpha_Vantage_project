# データモデルモジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのデータモデルモジュールについて説明します。

## 1. データモデルの概要

データモデルモジュールは、Alpha Vantage APIから取得した株価データを扱いやすい形式に変換するためのデータ構造を定義します。主な機能は以下の通りです：

- APIレスポンスデータの構造化
- 日付や数値の適切な型への変換
- データの整理と並べ替え
- データアクセスの簡素化

## 2. 主要なファイル

- `src/api/alpha_vantage/models.py`: Alpha Vantage APIレスポンス用のデータモデル

## 3. データモデルの詳細

### 3.1 `StockPrice`クラス

```python
@dataclass
class StockPrice:
    """1日分の株価データ。"""
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    @classmethod
    def from_api_response(cls, date_str: str, data: Dict[str, str]) -> 'StockPrice':
        """
        APIレスポンスデータからStockPriceインスタンスを作成します。
        
        引数:
            date_str: YYYY-MM-DD形式の日付文字列
            data: 1日分のAPIレスポンスデータ
            
        戻り値:
            StockPriceインスタンス
        """
        return cls(
            date=datetime.strptime(date_str, '%Y-%m-%d'),
            open=float(data['1. open']),
            high=float(data['2. high']),
            low=float(data['3. low']),
            close=float(data['4. close']),
            volume=int(data['5. volume'])
        )
```

`StockPrice`クラスは、1日分の株価データを表します。以下の特徴があります：

1. **データクラス**: Pythonの`dataclass`デコレータを使用して、簡潔なデータクラスとして定義されています。
2. **型アノテーション**: 各フィールドに型アノテーションが付けられており、コード補完やタイプチェックに役立ちます。
3. **ファクトリーメソッド**: `from_api_response`クラスメソッドを使用して、APIレスポンスデータからインスタンスを作成できます。
4. **型変換**: 文字列の日付を`datetime`オブジェクトに、文字列の数値を`float`や`int`に変換します。

### 3.2 `StockMetadata`クラス

```python
@dataclass
class StockMetadata:
    """株価データのメタデータ。"""
    symbol: str
    last_refreshed: datetime
    time_zone: str
    
    @classmethod
    def from_api_response(cls, metadata: Dict[str, str]) -> 'StockMetadata':
        """
        APIレスポンスのメタデータからStockMetadataインスタンスを作成します。
        
        引数:
            metadata: APIレスポンスのメタデータ
            
        戻り値:
            StockMetadataインスタンス
        """
        return cls(
            symbol=metadata['2. Symbol'],
            last_refreshed=datetime.strptime(metadata['3. Last Refreshed'], '%Y-%m-%d'),
            time_zone=metadata['5. Time Zone']
        )
```

`StockMetadata`クラスは、株価データに関するメタデータを表します。以下の特徴があります：

1. **データクラス**: `StockPrice`と同様に、`dataclass`デコレータを使用しています。
2. **メタデータの抽出**: APIレスポンスから必要なメタデータを抽出します。
3. **日付の変換**: 文字列の日付を`datetime`オブジェクトに変換します。

### 3.3 `StockTimeSeries`クラス

```python
@dataclass
class StockTimeSeries:
    """株価の時系列データ。"""
    metadata: StockMetadata
    prices: List[StockPrice]
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'StockTimeSeries':
        """
        完全なAPIレスポンスからStockTimeSeriesインスタンスを作成します。
        
        引数:
            response: 完全なAPIレスポンス
            
        戻り値:
            StockTimeSeriesインスタンス
        """
        metadata = StockMetadata.from_api_response(response['Meta Data'])
        
        time_series = response['Time Series (Daily)']
        prices = [
            StockPrice.from_api_response(date, data)
            for date, data in time_series.items()
        ]
        
        # 日付で並べ替え（最新順）
        prices.sort(key=lambda x: x.date, reverse=True)
        
        return cls(metadata=metadata, prices=prices)
```

`StockTimeSeries`クラスは、株価の時系列データ全体を表します。以下の特徴があります：

1. **データの集約**: メタデータと価格データを1つのオブジェクトにまとめます。
2. **データの変換**: APIレスポンスから`StockMetadata`と`StockPrice`のリストを作成します。
3. **データの並べ替え**: 日付で並べ替えて、最新のデータが先頭に来るようにします。

## 4. データモデルの使用例

```python
# APIクライアントの初期化と株価データの取得
from src.config import Config
from src.api.alpha_vantage.client import AlphaVantageClient
from src.api.alpha_vantage.models import StockTimeSeries

config = Config()
client = AlphaVantageClient(config.api_key)
response_data = client.fetch_daily_stock_data("NVDA")

# APIレスポンスからStockTimeSeriesオブジェクトを作成
time_series = StockTimeSeries.from_api_response(response_data)

# メタデータへのアクセス
print(f"Symbol: {time_series.metadata.symbol}")
print(f"Last Refreshed: {time_series.metadata.last_refreshed}")
print(f"Time Zone: {time_series.metadata.time_zone}")

# 最新の株価データへのアクセス
latest_price = time_series.prices[0]
print(f"Latest Date: {latest_price.date}")
print(f"Open: {latest_price.open}")
print(f"High: {latest_price.high}")
print(f"Low: {latest_price.low}")
print(f"Close: {latest_price.close}")
print(f"Volume: {latest_price.volume}")

# すべての株価データの処理
for price in time_series.prices:
    # 各日の株価データを処理
    print(f"{price.date}: Open={price.open}, Close={price.close}")
```

## 5. データモデルの利点

データモデルを使用することで、以下のような利点があります：

1. **型安全性**: 型アノテーションにより、コード補完やタイプチェックが可能になります。
2. **データアクセスの簡素化**: ドット記法（`time_series.metadata.symbol`など）でデータにアクセスできます。
3. **データ変換の一元化**: APIレスポンスからのデータ変換ロジックが一箇所にまとまります。
4. **コードの可読性向上**: データ構造が明確になり、コードが読みやすくなります。
5. **拡張性**: 必要に応じて、メソッドやプロパティを追加できます。

## 6. データクラスについて

Pythonの`dataclass`デコレータは、データを保持するためのクラスを簡潔に定義するための機能です。以下のような特徴があります：

1. **自動生成**: `__init__`、`__repr__`、`__eq__`などのメソッドが自動的に生成されます。
2. **不変性**: `frozen=True`を指定することで、不変（イミュータブル）なオブジェクトを作成できます。
3. **デフォルト値**: フィールドにデフォルト値を設定できます。
4. **後処理**: `__post_init__`メソッドを定義することで、初期化後の処理を追加できます。

例：
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class StockPrice:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def __post_init__(self):
        # 初期化後の検証
        if self.low > self.high:
            raise ValueError("Low price cannot be higher than high price")
        if self.close < self.low or self.close > self.high:
            raise ValueError("Close price must be between low and high prices")
```

## 7. 設計のポイント

1. **階層的なデータモデル**: `StockTimeSeries`が`StockMetadata`と`StockPrice`のリストを含む階層的な構造になっています。

2. **ファクトリーメソッド**: `from_api_response`クラスメソッドを使用して、APIレスポンスからオブジェクトを作成します。これにより、オブジェクト作成のロジックがカプセル化されます。

3. **データの並べ替え**: 日付で並べ替えることで、最新のデータに簡単にアクセスできるようになっています。

4. **型アノテーション**: すべてのフィールドに型アノテーションが付けられており、コード補完やタイプチェックに役立ちます。

5. **データクラスの使用**: `dataclass`デコレータを使用することで、簡潔なデータクラスを定義しています。

## 8. 練習問題

1. `StockPrice`クラスに、値上がり率（前日比）を計算するメソッドを追加してみましょう。

2. `StockTimeSeries`クラスに、特定の期間の株価データを抽出するメソッドを追加してみましょう。

3. `StockTimeSeries`クラスに、移動平均を計算するメソッドを追加してみましょう。

4. APIレスポンスの形式が変わった場合に対応できるように、`from_api_response`メソッドを拡張してみましょう。

## 9. 参考資料

- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html): Pythonのデータクラスに関する公式ドキュメント
- [Type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html): Pythonの型ヒントのチートシート
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/): Alpha Vantage APIの公式ドキュメント
