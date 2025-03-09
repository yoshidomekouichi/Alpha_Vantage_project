# ストレージモジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのストレージモジュールについて説明します。

## 1. ストレージモジュールの概要

ストレージモジュールは、処理された株価データをAWS S3に保存し、必要に応じて取得するための機能を提供します。主な機能は以下の通りです：

- S3へのデータの保存（JSON、CSV、Parquet形式）
- S3からのデータの読み込み
- アトミックな更新操作によるデータの整合性確保
- S3オブジェクトの存在確認
- S3オブジェクトのリスト取得

## 2. 主要なファイル

- `src/storage/s3.py`: S3ストレージ操作の基本クラス
- `src/utils/atomic_s3.py`: アトミックなS3更新操作を提供するクラス
- `src/utils/storage.py`: ストレージユーティリティ（このプロジェクトでは使用されていない可能性があります）

## 3. `S3Storage`クラスの詳細

### 3.1 初期化

```python
def __init__(self, bucket_name: str, region_name: str = 'ap-northeast-1'):
    """
    S3ストレージハンドラを初期化します。
    
    引数:
        bucket_name: S3バケット名
        region_name: AWSリージョン名
    """
    self.bucket_name = bucket_name
    self.region_name = region_name
    
    # boto3をここでインポートして、モックモードでboto3がインストールされていなくても動作するようにする
    import boto3
    from botocore.exceptions import ClientError
    self.ClientError = ClientError
    self.s3_client = boto3.client('s3', region_name=region_name)
```

初期化時に、S3バケット名とAWSリージョンを設定し、boto3クライアントを作成します。boto3のインポートを初期化メソッド内で行うことで、モックモードでboto3がインストールされていなくても動作するようにしています。

### 3.2 JSONデータの保存

```python
def save_json(self, data: Dict[str, Any], key: str) -> bool:
    """
    データをJSONとしてS3に保存します。
    
    引数:
        data: 保存するデータ
        key: S3オブジェクトキー（パス）
        
    戻り値:
        成功を示すブール値
    """
    try:
        json_data = json.dumps(data, indent=2)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json_data,
            ContentType='application/json'
        )
        logger.info(f"✅ Successfully saved JSON data to s3://{self.bucket_name}/{key}")
        return True
    except Exception as e:
        logger.exception(f"❌ Error saving JSON data to S3: {e}")
        return False
```

このメソッドは、Pythonの辞書をJSON形式に変換し、S3に保存します。成功した場合は`True`を、失敗した場合は`False`を返します。

### 3.3 CSVデータの保存

```python
def save_csv(self, df: pd.DataFrame, key: str) -> bool:
    """
    DataFrameをCSVとしてS3に保存します。
    
    引数:
        df: 保存するDataFrame
        key: S3オブジェクトキー（パス）
        
    戻り値:
        成功を示すブール値
    """
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=True)
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        logger.info(f"✅ Successfully saved CSV data to s3://{self.bucket_name}/{key}")
        return True
    except Exception as e:
        logger.exception(f"❌ Error saving CSV data to S3: {e}")
        return False
```

このメソッドは、PandasのDataFrameをCSV形式に変換し、S3に保存します。一時的なバッファを使用して、メモリ上でCSVを生成します。

### 3.4 Parquetデータの保存

```python
def save_parquet(self, df: pd.DataFrame, key: str) -> bool:
    """
    DataFrameをParquetとしてS3に保存します。
    
    引数:
        df: 保存するDataFrame
        key: S3オブジェクトキー（パス）
        
    戻り値:
        成功を示すブール値
    """
    try:
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer)
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=parquet_buffer.getvalue()
        )
        logger.info(f"✅ Successfully saved Parquet data to s3://{self.bucket_name}/{key}")
        return True
    except Exception as e:
        logger.exception(f"❌ Error saving Parquet data to S3: {e}")
        return False
```

このメソッドは、PandasのDataFrameをParquet形式に変換し、S3に保存します。Parquetは列指向の圧縮ファイル形式で、大規模なデータセットに適しています。

### 3.5 JSONデータの読み込み

```python
def load_json(self, key: str) -> Optional[Dict[str, Any]]:
    """
    S3からJSONデータを読み込みます。
    
    引数:
        key: S3オブジェクトキー（パス）
        
    戻り値:
        読み込まれたデータ、またはエラーが発生した場合はNone
    """
    try:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        json_data = json.loads(response['Body'].read().decode('utf-8'))
        logger.info(f"✅ Successfully loaded JSON data from s3://{self.bucket_name}/{key}")
        return json_data
    except self.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"⚠️ Object not found: s3://{self.bucket_name}/{key}")
        else:
            logger.exception(f"❌ Error loading JSON data from S3: {e}")
        return None
    except Exception as e:
        logger.exception(f"❌ Error loading JSON data from S3: {e}")
        return None
```

このメソッドは、S3からJSONデータを読み込み、Pythonの辞書に変換します。オブジェクトが存在しない場合や、その他のエラーが発生した場合は`None`を返します。

### 3.6 CSVデータの読み込み

```python
def load_csv(self, key: str) -> Optional[pd.DataFrame]:
    """
    S3からCSVデータをDataFrameに読み込みます。
    
    引数:
        key: S3オブジェクトキー（パス）
        
    戻り値:
        DataFrame、またはエラーが発生した場合はNone
    """
    try:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        df = pd.read_csv(io.BytesIO(response['Body'].read()))
        logger.info(f"✅ Successfully loaded CSV data from s3://{self.bucket_name}/{key}")
        return df
    except self.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"⚠️ Object not found: s3://{self.bucket_name}/{key}")
        else:
            logger.exception(f"❌ Error loading CSV data from S3: {e}")
        return None
    except Exception as e:
        logger.exception(f"❌ Error loading CSV data from S3: {e}")
        return None
```

このメソッドは、S3からCSVデータを読み込み、PandasのDataFrameに変換します。

### 3.7 Parquetデータの読み込み

```python
def load_parquet(self, key: str) -> Optional[pd.DataFrame]:
    """
    S3からParquetデータをDataFrameに読み込みます。
    
    引数:
        key: S3オブジェクトキー（パス）
        
    戻り値:
        DataFrame、またはエラーが発生した場合はNone
    """
    try:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        df = pd.read_parquet(io.BytesIO(response['Body'].read()))
        logger.info(f"✅ Successfully loaded Parquet data from s3://{self.bucket_name}/{key}")
        return df
    except self.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"⚠️ Object not found: s3://{self.bucket_name}/{key}")
        else:
            logger.exception(f"❌ Error loading Parquet data from S3: {e}")
        return None
    except Exception as e:
        logger.exception(f"❌ Error loading Parquet data from S3: {e}")
        return None
```

このメソッドは、S3からParquetデータを読み込み、PandasのDataFrameに変換します。

### 3.8 オブジェクトの存在確認

```python
def object_exists(self, key: str) -> bool:
    """
    S3にオブジェクトが存在するかを確認します。
    
    引数:
        key: S3オブジェクトキー（パス）
        
    戻り値:
        オブジェクトが存在するかを示すブール値
    """
    try:
        self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
        return True
    except self.ClientError:
        return False
```

このメソッドは、指定されたキーのオブジェクトがS3に存在するかどうかを確認します。`head_object`メソッドを使用することで、オブジェクトの内容を取得せずに存在確認ができます。

### 3.9 オブジェクトのリスト取得

```python
def list_objects(self, prefix: str = '') -> List[str]:
    """
    指定されたプレフィックスでS3バケット内のオブジェクトをリストします。
    
    引数:
        prefix: フィルタリングするS3キープレフィックス
        
    戻り値:
        オブジェクトキーのリスト
    """
    try:
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            return []
            
        return [obj['Key'] for obj in response['Contents']]
    except Exception as e:
        logger.exception(f"❌ Error listing objects in S3: {e}")
        return []
```

このメソッドは、指定されたプレフィックスに一致するS3オブジェクトのリストを取得します。プレフィックスを指定しない場合は、バケット内のすべてのオブジェクトを取得します。

## 4. `AtomicS3`クラスの詳細

### 4.1 初期化

```python
def __init__(self, s3_storage):
    """
    アトミックS3ハンドラを初期化します。
    
    引数:
        s3_storage: S3Storageのインスタンス
    """
    self.s3 = s3_storage
    self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
```

初期化時に、`S3Storage`インスタンスを受け取り、環境変数からモックモードの設定を読み込みます。

### 4.2 アトミック更新

```python
def atomic_update(self, key: str, update_func: Callable, *args, **kwargs) -> bool:
    """
    S3オブジェクトにアトミック更新を実行します。
    
    引数:
        key: S3オブジェクトキー（パス）
        update_func: 更新を実行する関数
        *args, **kwargs: 更新関数に渡す引数
        
    戻り値:
        成功を示すブール値
    """
    if self.mock_mode:
        logger.info(f"🔍 [MOCK] Performed atomic update to s3://{self.s3.bucket_name}/{key}")
        return True
        
    # 一時的なキーを生成
    tmp_key = f"{key}.tmp.{uuid.uuid4()}"
    
    try:
        # 一時的なオブジェクトに対して更新関数を呼び出す
        success = update_func(tmp_key, *args, **kwargs)
        
        if not success:
            logger.error(f"❌ Update function failed for temporary object: {tmp_key}")
            return False
        
        # 一時的なオブジェクトを最終的なキーにコピー
        self.s3.s3_client.copy_object(
            Bucket=self.s3.bucket_name,
            CopySource={'Bucket': self.s3.bucket_name, 'Key': tmp_key},
            Key=key
        )
        
        # 一時的なオブジェクトを削除
        self.s3.s3_client.delete_object(
            Bucket=self.s3.bucket_name,
            Key=tmp_key
        )
        
        logger.info(f"✅ Successfully performed atomic update to s3://{self.s3.bucket_name}/{key}")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Error during atomic update: {e}")
        
        # 一時的なオブジェクトのクリーンアップを試みる
        try:
            if self.s3.object_exists(tmp_key):
                self.s3.s3_client.delete_object(
                    Bucket=self.s3.bucket_name,
                    Key=tmp_key
                )
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Failed to clean up temporary object: {cleanup_error}")
            
        return False
```

このメソッドは、S3オブジェクトにアトミック更新を実行します。アトミック更新とは、更新操作が完全に成功するか、まったく行われないかのいずれかになることを保証する更新方法です。以下の手順で実行されます：

1. 一時的なキー（UUID付き）を生成します。
2. 更新関数を一時的なキーに対して実行します。
3. 更新が成功したら、一時的なオブジェクトを最終的なキーにコピーします。
4. 一時的なオブジェクトを削除します。
5. エラーが発生した場合は、一時的なオブジェクトをクリーンアップし、`False`を返します。

この方法により、更新中にエラーが発生しても、元のデータが破損することはありません。

### 4.3 アトミックJSON更新

```python
def atomic_json_update(self, key: str, data: Dict[str, Any]) -> bool:
    """
    S3のJSONオブジェクトをアトミックに更新します。
    
    引数:
        key: S3オブジェクトキー（パス）
        data: 保存するJSONデータ
        
    戻り値:
        成功を示すブール値
    """
    return self.atomic_update(key, self.s3.save_json, data)
```

このメソッドは、JSONデータをS3にアトミックに保存します。`atomic_update`メソッドを使用して、`save_json`メソッドを実行します。

### 4.4 アトミックCSV更新

```python
def atomic_csv_update(self, key: str, df) -> bool:
    """
    S3のCSVオブジェクトをアトミックに更新します。
    
    引数:
        key: S3オブジェクトキー（パス）
        df: 保存するDataFrame
        
    戻り値:
        成功を示すブール値
    """
    return self.atomic_update(key, self.s3.save_csv, df)
```

このメソッドは、CSVデータをS3にアトミックに保存します。

### 4.5 アトミックParquet更新

```python
def atomic_parquet_update(self, key: str, df) -> bool:
    """
    S3のParquetオブジェクトをアトミックに更新します。
    
    引数:
        key: S3オブジェクトキー（パス）
        df: 保存するDataFrame
        
    戻り値:
        成功を示すブール値
    """
    return self.atomic_update(key, self.s3.save_parquet, df)
```

このメソッドは、Parquetデータをs3にアトミックに保存します。

## 5. ストレージモジュールの使用例

```python
# 設定の読み込み
from src.config import Config
config = Config()

# S3ストレージの初期化
from src.storage.s3 import S3Storage
from src.utils.atomic_s3 import AtomicS3

s3_storage = S3Storage(config.s3_bucket, config.s3_region)
atomic_s3 = AtomicS3(s3_storage)

# ロガーの設定
import logging
logger = logging.getLogger("my_logger")
s3_storage.set_logger(logger)
atomic_s3.set_logger(logger)

# JSONデータの保存
data = {"symbol": "NVDA", "price": 150.0, "date": "2023-01-01"}
key = "stock-data/NVDA/latest.json"
s3_storage.save_json(data, key)

# JSONデータのアトミック更新
data["price"] = 155.0
atomic_s3.atomic_json_update(key, data)

# JSONデータの読み込み
loaded_data = s3_storage.load_json(key)
print(loaded_data)

# DataFrameの保存
import pandas as pd
df = pd.DataFrame({
    "date": ["2023-01-01", "2023-01-02"],
    "open": [150.0, 155.0],
    "close": [155.0, 160.0]
})
csv_key = "stock-data/NVDA/data.csv"
parquet_key = "stock-data/NVDA/data.parquet"
s3_storage.save_csv(df, csv_key)
s3_storage.save_parquet(df, parquet_key)

# オブジェクトの存在確認
if s3_storage.object_exists(key):
    print(f"Object {key} exists")

# オブジェクトのリスト取得
objects = s3_storage.list_objects(prefix="stock-data/NVDA/")
for obj in objects:
    print(obj)
```

## 6. S3ストレージの利点

AWS S3（Simple Storage Service）は、以下のような利点があります：

1. **耐久性**: 99.999999999%（11個の9）の耐久性を提供します。
2. **可用性**: 99.99%の可用性を提供します。
3. **スケーラビリティ**: 自動的にスケールするため、容量を気にする必要がありません。
4. **セキュリティ**: 様々なセキュリティ機能（暗号化、アクセス制御など）を提供します。
5. **コスト効率**: 使用した分だけ支払うモデルで、コスト効率が高いです。
6. **柔軟性**: 様々なデータ形式やサイズのデータを保存できます。

## 7. アトミック更新の重要性

アトミック更新は、以下の理由から重要です：

1. **データの整合性**: 更新操作が途中で失敗しても、データが不整合な状態になることはありません。
2. **並行アクセス**: 複数のプロセスが同じデータにアクセスする場合でも、データの整合性が保たれます。
3. **障害耐性**: システム障害が発生しても、データが破損することはありません。

このプロジェクトでは、「一時ファイル + リネーム」パターンを使用してアトミック更新を実現しています：

1. 一時的なキーにデータを書き込みます。
2. 書き込みが成功したら、一時的なオブジェクトを最終的なキーにコピーします。
3. 一時的なオブジェクトを削除します。

この方法により、更新操作が途中で失敗しても、元のデータは変更されません。

## 8. データ形式の比較

このプロジェクトでは、以下の3つのデータ形式をサポートしています：

1. **JSON**:
   - 人間が読みやすい形式
   - 構造化されたデータを表現できる
   - テキストベースで、サイズが大きくなる可能性がある
   - 処理速度は比較的遅い

2. **CSV**:
   - シンプルな表形式のデータに適している
   - 多くのツールでサポートされている
   - テキストベースで、サイズが大きくなる可能性がある
   - 複雑なデータ構造を表現するのは難しい

3. **Parquet**:
   - 列指向の圧縮ファイル形式
   - 大規模なデータセットに適している
   - 高い圧縮率と処理速度
   - バイナリ形式で、人間が直接読むことはできない

用途に応じて適切な形式を選択することが重要です：

- **人間が読みやすさを重視する場合**: JSON
- **シンプルな表形式のデータで互換性を重視する場合**: CSV
- **大規模なデータセットでパフォーマンスを重視する場合**: Parquet

## 9. 設計のポイント

1. **モジュール化**: ストレージ操作を独立したクラスにカプセル化しています。

2. **エラーハンドリング**: 様々なエラーに対応し、適切なエラーメッセージをログに出力します。

3. **アトミック更新**: データの整合性を確保するために、アトミック更新を実装しています。

4. **複数のデータ形式**: JSON、CSV、Parquetなど、複数のデータ形式をサポートしています。

5. **モックモード**: テスト用のモックモードをサポートしています。

## 10. 練習問題

1. `S3Storage`クラスに、オブジェクトのメタデータを取得するメソッドを追加してみましょう。

2. `S3Storage`クラスに、オブジェクトのバージョン履歴を取得するメソッドを追加してみましょう（バージョニングが有効な場合）。

3. `AtomicS3`クラスに、条件付き更新（既存のオブジェクトが特定の条件を満たす場合のみ更新）を実装してみましょう。

4. 大きなファイルをマルチパートアップロードで保存するメソッドを追加してみましょう。

## 11. 参考資料

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/index.html): AWS S3の公式ドキュメント
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html): Python用AWS SDKの公式ドキュメント
- [Atomic File Operations](https://en.wikipedia.org/wiki/Atomicity_(database_systems)): アトミック操作に関するWikipediaの記事
- [Parquet Format](https://parquet.apache.org/): Apache Parquetの公式サイト
