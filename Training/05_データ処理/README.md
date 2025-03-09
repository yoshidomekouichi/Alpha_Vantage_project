# データ処理モジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのデータ処理モジュールについて説明します。

## 1. データ処理の概要

データ処理モジュールは、Alpha Vantage APIから取得した株価データを検証、変換、加工するための機能を提供します。主な機能は以下の通りです：

- データの検証と品質チェック
- APIレスポンスからPandasデータフレームへの変換
- データの整形と加工
- 最新データの抽出
- データのJSON形式への変換

## 2. 主要なファイル

- `src/utils/data_processing.py`: データ処理ユーティリティ
- `src/data/processing.py`: データ処理モジュール（このプロジェクトでは使用されていない可能性があります）
- `src/data/validation.py`: データ検証モジュール（このプロジェクトでは使用されていない可能性があります）

## 3. `StockDataProcessor`クラスの詳細

### 3.1 初期化

```python
def __init__(self):
    """株価データプロセッサを初期化します。"""
    pass
    
def set_logger(self, custom_logger):
    """プロセッサのカスタムロガーを設定します。"""
    global logger
    logger = custom_logger
```

初期化は単純で、特別な設定は必要ありません。`set_logger`メソッドを使用して、カスタムロガーを設定できます。

### 3.2 データの検証と変換

```python
def validate_and_transform(self, stock_data: Dict[str, Any]) -> Tuple[bool, Optional[pd.DataFrame]]:
    """
    株価データを検証し、Pandasデータフレームに変換します。
    
    引数:
        stock_data: Alpha Vantage APIからの生の株価データ
        
    戻り値:
        検証結果とデータフレームのタプル
        - is_valid: データが検証に合格したかどうかを示すブール値
        - dataframe: 処理されたデータのPandasデータフレーム、または検証に失敗した場合はNone
    """
    # データの存在確認
    time_series = stock_data.get("Time Series (Daily)", {})
    if not time_series:
        logger.warning("⚠️ Empty data received! Check API response.")
        return False, None
    
    # データフレームに変換
    try:
        df = pd.DataFrame.from_dict(time_series, orient="index")
        
        # カラム名をより使いやすい名前に変更
        df.columns = [col.split('. ')[1] for col in df.columns]
        
        # 文字列値を適切な数値型に変換
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # インデックスをdatetimeに変換
        df.index = pd.to_datetime(df.index)
        
        # 日付で並べ替え（降順）
        df = df.sort_index(ascending=False)
        
        # 品質チェックを実行
        validation_result = self._run_quality_checks(df)
        
        return validation_result, df if validation_result else None
        
    except Exception as e:
        logger.exception(f"❌ Error processing stock data: {e}")
        return False, None
```

このメソッドは、Alpha Vantage APIから取得した株価データを検証し、Pandasデータフレームに変換します。以下の処理を行います：

1. **データの存在確認**: APIレスポンスに時系列データが含まれているかを確認します。
2. **データフレームへの変換**: 辞書形式のデータをPandasデータフレームに変換します。
3. **カラム名の変更**: APIのカラム名（例：`1. open`）をより使いやすい名前（例：`open`）に変更します。
4. **数値型への変換**: 文字列の数値を適切な数値型に変換します。
5. **日付型への変換**: インデックスを日付型に変換します。
6. **データの並べ替え**: 日付で降順に並べ替えます（最新のデータが先頭に来るようにします）。
7. **品質チェック**: データの品質チェックを実行します。

### 3.3 データの品質チェック

```python
def _run_quality_checks(self, df: pd.DataFrame) -> bool:
    """
    処理されたデータフレームに対して品質チェックを実行します。
    
    引数:
        df: 処理されたデータフレーム
        
    戻り値:
        データがすべての品質チェックに合格したかどうかを示すブール値
    """
    # 欠損値のチェック
    if df.isnull().any().any():
        missing_counts = df.isnull().sum()
        logger.warning(f"⚠️ Data contains missing values:\n{missing_counts}")
        return False
    
    # ゼロボリュームのチェック
    if (df["volume"] == 0).any():
        zero_volume_dates = df[df["volume"] == 0].index.tolist()
        logger.warning(f"⚠️ Zero volume detected on dates: {zero_volume_dates}")
        return False
    
    # 負の価格のチェック
    if (df[["open", "high", "low", "close"]] < 0).any().any():
        negative_prices = df[(df[["open", "high", "low", "close"]] < 0).any(axis=1)]
        logger.warning(f"⚠️ Negative prices detected:\n{negative_prices}")
        return False
    
    # 極端な価格の外れ値のチェック（99パーセンタイルの10倍）
    for col in ["open", "high", "low", "close"]:
        threshold = df[col].quantile(0.99) * 10
        outliers = df[df[col] > threshold]
        if not outliers.empty:
            logger.warning(f"⚠️ Extreme {col} price outliers detected:\n{outliers}")
            return False
    
    # 価格の不整合のチェック（low > high、closeが範囲外）
    if (df["low"] > df["high"]).any():
        inconsistent = df[df["low"] > df["high"]]
        logger.warning(f"⚠️ Price inconsistency detected (low > high):\n{inconsistent}")
        return False
    
    if ((df["close"] > df["high"]) | (df["close"] < df["low"])).any():
        inconsistent = df[(df["close"] > df["high"]) | (df["close"] < df["low"])]
        logger.warning(f"⚠️ Price inconsistency detected (close outside range):\n{inconsistent}")
        return False
    
    if ((df["open"] > df["high"]) | (df["open"] < df["low"])).any():
        inconsistent = df[(df["open"] > df["high"]) | (df["open"] < df["low"])]
        logger.warning(f"⚠️ Price inconsistency detected (open outside range):\n{inconsistent}")
        return False
    
    logger.info("✅ Data quality check passed!")
    return True
```

このメソッドは、データフレームに対して以下の品質チェックを実行します：

1. **欠損値のチェック**: データに欠損値（NaN）が含まれていないかを確認します。
2. **ゼロボリュームのチェック**: 取引量がゼロの日がないかを確認します。
3. **負の価格のチェック**: 価格（始値、高値、安値、終値）が負の値になっていないかを確認します。
4. **極端な外れ値のチェック**: 価格が異常に高い値（99パーセンタイルの10倍以上）になっていないかを確認します。
5. **価格の不整合のチェック**:
   - 安値が高値より高くなっていないか
   - 終値が安値と高値の範囲内にあるか
   - 始値が安値と高値の範囲内にあるか

これらのチェックのいずれかに失敗した場合、警告ログを出力し、`False`を返します。すべてのチェックに合格した場合、情報ログを出力し、`True`を返します。

### 3.4 最新データの抽出

```python
def extract_latest_data(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    データフレームから最新のデータポイントを抽出します。
    
    引数:
        df: 処理されたデータフレーム
        
    戻り値:
        最新のデータポイントのみを含むデータフレーム
    """
    return df.head(1)
```

このメソッドは、データフレームから最新のデータポイント（先頭の行）を抽出します。データフレームは既に日付で降順に並べ替えられているため、先頭の行が最新のデータになります。

### 3.5 JSONへの変換

```python
def convert_to_json(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    データフレームをJSON形式の辞書に変換します。
    
    引数:
        df: 処理されたデータフレーム
        
    戻り値:
        データフレームのJSON形式の辞書表現
    """
    # 元のデータフレームを変更しないようにコピーを作成
    df_copy = df.copy()
    
    # インデックスに'date'という名前を付けてからリセット
    df_copy.index.name = 'date'
    
    # インデックスをリセットして日付をカラムにする
    df_reset = df_copy.reset_index()
    
    # 日付を文字列に変換
    df_reset['date'] = df_reset['date'].dt.strftime('%Y-%m-%d')
    
    # レコード形式（辞書のリスト）に変換
    records = df_reset.to_dict(orient='records')
    
    return {"data": records}
```

このメソッドは、Pandasデータフレームを、S3に保存するためのJSON形式の辞書に変換します。以下の処理を行います：

1. **データフレームのコピー**: 元のデータフレームを変更しないように、コピーを作成します。
2. **インデックス名の設定**: インデックスに`'date'`という名前を付けます。
3. **インデックスのリセット**: インデックスをリセットして、日付をカラムにします。
4. **日付の文字列変換**: 日付を`'%Y-%m-%d'`形式の文字列に変換します。
5. **レコード形式への変換**: データフレームをレコード形式（辞書のリスト）に変換します。
6. **最終形式の作成**: `{"data": records}`形式の辞書を返します。

### 3.6 CSVへの変換

```python
def convert_to_csv(self, df: pd.DataFrame) -> str:
    """
    データフレームをCSV文字列に変換します。
    
    引数:
        df: 処理されたデータフレーム
        
    戻り値:
        データフレームのCSV文字列表現
    """
    return df.reset_index().to_csv(index=False)
```

このメソッドは、Pandasデータフレームを、CSV形式の文字列に変換します。インデックスをリセットして日付をカラムにし、CSVに変換します。

## 4. データ処理の使用例

```python
# 設定とAPIクライアントの初期化
from src.config import Config
from src.api.alpha_vantage.client import AlphaVantageClient
from src.utils.data_processing import StockDataProcessor

config = Config()
client = AlphaVantageClient(config.api_key)
processor = StockDataProcessor()

# ロガーの設定
import logging
logger = logging.getLogger("my_logger")
processor.set_logger(logger)

# 株価データの取得
response_data = client.fetch_daily_stock_data("NVDA")

# データの検証と変換
is_valid, df = processor.validate_and_transform(response_data)

if is_valid and df is not None:
    # 最新データの抽出
    latest_df = processor.extract_latest_data(df)
    
    # JSONへの変換
    json_data = processor.convert_to_json(df)
    latest_json_data = processor.convert_to_json(latest_df)
    
    # CSVへの変換
    csv_data = processor.convert_to_csv(df)
    
    # データの使用
    print(f"Latest date: {latest_df.index[0]}")
    print(f"Latest close price: {latest_df['close'].iloc[0]}")
    print(f"Total data points: {len(df)}")
else:
    print("Data validation failed")
```

## 5. Pandasデータフレームについて

Pandasは、Pythonでデータ分析を行うための強力なライブラリです。`DataFrame`は、Pandasの中心的なデータ構造で、以下のような特徴があります：

1. **表形式のデータ構造**: 行と列からなる2次元のテーブル構造です。
2. **ラベル付きインデックス**: 行と列にラベルを付けることができます。
3. **異なる型のデータ**: 異なる列に異なる型のデータを格納できます。
4. **欠損値の処理**: 欠損値（NaN）を扱うための機能が豊富です。
5. **データ操作**: フィルタリング、集計、結合などの操作が簡単に行えます。
6. **時系列データの処理**: 日付や時間のインデックスを使った操作が強力です。

このプロジェクトでは、Pandasデータフレームを使用して、以下のような操作を行っています：

- APIレスポンスからデータフレームへの変換
- データの型変換（文字列から数値、日付など）
- データの並べ替え
- データのフィルタリング（品質チェック）
- データの集計と変換（JSON、CSVへの変換）

## 6. データ品質チェックの重要性

データ品質チェックは、以下の理由から重要です：

1. **データの信頼性**: 品質チェックにより、データの信頼性を確保できます。
2. **エラーの早期発見**: APIの仕様変更や異常なデータを早期に発見できます。
3. **下流の処理の保護**: 品質の低いデータが下流の処理に流れることを防ぎます。
4. **意思決定の質の向上**: 高品質なデータに基づいて、より良い意思決定ができます。

このプロジェクトでは、以下のような品質チェックを実装しています：

- **完全性**: 欠損値のチェック
- **正確性**: 価格の不整合のチェック
- **妥当性**: 負の価格や極端な外れ値のチェック
- **一貫性**: 取引量がゼロの日のチェック

## 7. 設計のポイント

1. **モジュール化**: データ処理ロジックを独立したクラスにカプセル化しています。

2. **段階的な処理**: データの検証、変換、抽出、出力形式への変換など、段階的に処理を行っています。

3. **エラーハンドリング**: 例外をキャッチし、適切なエラーメッセージをログに出力します。

4. **不変性**: 元のデータフレームを変更せず、コピーを作成して処理しています。

5. **カスタマイズ可能なロギング**: カスタムロガーを設定できるようにしています。

## 8. 練習問題

1. `StockDataProcessor`クラスに、移動平均を計算するメソッドを追加してみましょう。

2. `StockDataProcessor`クラスに、ボリンジャーバンドを計算するメソッドを追加してみましょう。

3. 品質チェックに、新しいチェック（例：取引量の急激な変化の検出）を追加してみましょう。

4. データフレームをParquet形式に変換するメソッドを追加してみましょう。

## 9. 参考資料

- [Pandas Documentation](https://pandas.pydata.org/docs/): Pandasの公式ドキュメント
- [Data Quality Dimensions](https://en.wikipedia.org/wiki/Data_quality): データ品質の次元に関するWikipediaの記事
- [Financial Data Analysis with Python](https://www.oreilly.com/library/view/python-for-finance/9781492024323/): Pythonを使った金融データ分析の書籍
