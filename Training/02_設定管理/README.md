# 設定管理モジュール

このドキュメントでは、Alpha Vantage株価データパイプラインの設定管理モジュールについて説明します。

## 1. 設定管理の概要

設定管理モジュールは、アプリケーションの動作を制御するための設定値を一元管理します。主な機能は以下の通りです：

- 環境変数からの設定読み込み
- `.env`ファイルからの設定読み込み
- 設定値の検証
- 設定値へのアクセス提供
- S3キーの生成

## 2. 主要なファイル

- `src/config.py`: メインの設定管理クラス
- `src/core/config.py`: コア設定ユーティリティ（このプロジェクトでは使用されていない可能性があります）

## 3. `Config`クラスの詳細

### 3.1 初期化

```python
def __init__(self, env_file: Optional[str] = None):
    """
    設定マネージャーを初期化します。
    
    引数:
        env_file: .envファイルへのパス（デフォルト: project_root/.env）
    """
    # デフォルトパスの設定
    self.project_root = Path(__file__).parent.parent
    self.default_env_path = self.project_root / ".env"
    
    # 環境変数の読み込み
    if env_file:
        self.env_path = Path(env_file)
    else:
        self.env_path = self.default_env_path
        
    self._load_env_file()
    
    # 設定の初期化
    self._init_config()
```

初期化時に、`.env`ファイルからの環境変数の読み込みと、設定値の初期化が行われます。

### 3.2 環境変数の読み込み

```python
def _load_env_file(self):
    """
    .envファイルから環境変数を読み込みます。
    """
    if self.env_path.exists():
        # 既存の環境変数を強制的に上書き
        load_dotenv(self.env_path, override=True)
        logger.debug(f"Loaded environment variables from {self.env_path}")
    else:
        logger.warning(f"⚠️ Environment file not found: {self.env_path}")
```

`python-dotenv`ライブラリを使用して、`.env`ファイルから環境変数を読み込みます。`override=True`を指定することで、既存の環境変数を上書きします。

### 3.3 設定の初期化

```python
def _init_config(self):
    """
    環境変数から設定を初期化します。
    """
    # デバッグとモックモード
    self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'
    
    # API設定
    self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    self.api_base_url = os.getenv('ALPHA_VANTAGE_BASE_URL', 'https://www.alphavantage.co/query')
    
    # 取得する株式銘柄
    symbols_str = os.getenv('STOCK_SYMBOLS', 'NVDA')
    # シンボル文字列からコメントを削除
    if '#' in symbols_str:
        symbols_str = symbols_str.split('#')[0].strip()
    self.stock_symbols = [s.strip() for s in symbols_str.split(',')]
    
    # S3設定
    s3_bucket = os.getenv('S3_BUCKET')
    # バケット名からコメントを削除
    if s3_bucket and '#' in s3_bucket:
        s3_bucket = s3_bucket.split('#')[0].strip()
    self.s3_bucket = s3_bucket
    self.s3_region = os.getenv('AWS_REGION', 'ap-northeast-1')
    self.s3_prefix = os.getenv('S3_PREFIX', 'stock-data')
    
    # メール設定
    self.email_enabled = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'
    if self.email_enabled:
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': os.getenv('SMTP_PORT', '587'),
            'smtp_user': os.getenv('SMTP_USER'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL'),
            'to_email': os.getenv('TO_EMAIL')
        }
    else:
        self.email_config = None
    
    # Slack設定
    self.slack_enabled = os.getenv('SLACK_ENABLED', 'False').lower() == 'true'
    if self.slack_enabled:
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    else:
        self.slack_webhook_url = None
    
    # ロギング設定
    self.log_dir = os.getenv('LOG_DIR', str(self.project_root / 'logs'))
    self.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    # 必須設定の検証
    self._validate_config()
```

環境変数から各種設定値を読み込み、クラスの属性として設定します。文字列の`'true'`や`'false'`をブール値に変換する処理や、カンマ区切りの文字列をリストに変換する処理などが含まれています。

### 3.4 設定の検証

```python
def _validate_config(self):
    """
    必須設定値を検証します。
    """
    missing_vars = []
    
    # 必須変数のチェック
    if not self.api_key and not self.mock_mode:
        missing_vars.append('ALPHA_VANTAGE_API_KEY')
    
    if not self.s3_bucket:
        missing_vars.append('S3_BUCKET')
    
    if self.email_enabled:
        for key in ['SMTP_SERVER', 'SMTP_USER', 'SMTP_PASSWORD', 'FROM_EMAIL', 'TO_EMAIL']:
            if not os.getenv(key):
                missing_vars.append(key)
    
    if self.slack_enabled and not self.slack_webhook_url:
        missing_vars.append('SLACK_WEBHOOK_URL')
    
    # 不足している変数の警告ログ
    if missing_vars:
        if self.mock_mode and 'ALPHA_VANTAGE_API_KEY' in missing_vars:
            # モックモードではAPIキーは不要
            missing_vars.remove('ALPHA_VANTAGE_API_KEY')
            
        if missing_vars:
            logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
```

必須の設定値が設定されているかをチェックし、不足している場合は警告ログを出力します。モックモードの場合は、APIキーが不要なため、チェックから除外されます。

### 3.5 S3キーの生成

```python
def get_s3_key(self, symbol: str, date: str = None, is_latest: bool = False) -> str:
    """
    株価データを保存するためのS3キーを取得します。
    
    引数:
        symbol: 株式銘柄
        date: 日付文字列（YYYY-MM-DD）
        is_latest: 最新データかどうか
        
    戻り値:
        S3オブジェクトキー
    """
    if is_latest:
        return f"{self.s3_prefix}/{symbol}/latest.json"
    elif date:
        return f"{self.s3_prefix}/{symbol}/daily/{date}.json"
    else:
        return f"{self.s3_prefix}/{symbol}/full.json"

def get_metadata_key(self, symbol: str) -> str:
    """
    メタデータを保存するためのS3キーを取得します。
    
    引数:
        symbol: 株式銘柄
        
    戻り値:
        S3オブジェクトキー
    """
    return f"{self.s3_prefix}/{symbol}/metadata.json"
```

S3にデータを保存する際のキー（パス）を生成するメソッドです。データの種類（最新、日次、全データ、メタデータ）に応じて異なるキーを生成します。

### 3.6 設定の辞書変換とログ出力

```python
def to_dict(self) -> Dict[str, Any]:
    """
    設定を辞書に変換します。
    
    戻り値:
        設定の辞書表現
    """
    return {
        'debug_mode': self.debug_mode,
        'mock_mode': self.mock_mode,
        'api_base_url': self.api_base_url,
        'stock_symbols': self.stock_symbols,
        's3_bucket': self.s3_bucket,
        's3_region': self.s3_region,
        's3_prefix': self.s3_prefix,
        'email_enabled': self.email_enabled,
        'slack_enabled': self.slack_enabled,
        'log_dir': self.log_dir,
        'log_level': self.log_level
    }

def __str__(self) -> str:
    """
    設定の文字列表現を取得します。
    """
    config_dict = self.to_dict()
    # 機密情報を含めない
    if 'api_key' in config_dict:
        config_dict['api_key'] = '***'
    if 'email_config' in config_dict and config_dict['email_config']:
        if 'smtp_password' in config_dict['email_config']:
            config_dict['email_config']['smtp_password'] = '***'
    
    return json.dumps(config_dict, indent=2)
```

設定を辞書に変換するメソッドと、文字列表現を取得するメソッドです。文字列表現では、APIキーやSMTPパスワードなどの機密情報をマスクしています。

## 4. 設定ファイルの例

`.env`ファイルの例：

```
# デバッグとモックモード
DEBUG_MODE=false
MOCK_MODE=false

# Alpha Vantage API設定
ALPHA_VANTAGE_API_KEY=your_api_key_here
ALPHA_VANTAGE_BASE_URL=https://www.alphavantage.co/query

# 取得する株式銘柄（カンマ区切り）
STOCK_SYMBOLS=AAPL,MSFT,GOOGL,AMZN,NVDA

# AWS S3設定
S3_BUCKET=your-s3-bucket-name
AWS_REGION=ap-northeast-1
S3_PREFIX=stock-data

# メール通知設定
EMAIL_ENABLED=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com

# Slack通知設定
SLACK_ENABLED=false
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

# ロギング設定
LOG_LEVEL=INFO
LOG_DIR=logs
```

## 5. 設定の使用例

```python
# 設定の読み込み
config = Config()

# APIキーの取得
api_key = config.api_key

# モックモードの確認
if config.mock_mode:
    print("Running in mock mode")

# S3キーの生成
latest_key = config.get_s3_key("AAPL", is_latest=True)
daily_key = config.get_s3_key("AAPL", date="2023-01-01")
full_key = config.get_s3_key("AAPL")
metadata_key = config.get_metadata_key("AAPL")

# 設定の文字列表現
print(config)
```

## 6. 設計のポイント

1. **環境変数の使用**: 設定値を環境変数から読み込むことで、コードと設定を分離し、異なる環境（開発、テスト、本番）で同じコードを使用できるようにしています。

2. **デフォルト値の提供**: 多くの設定項目にデフォルト値を設定することで、最小限の設定で動作するようにしています。

3. **設定の検証**: 必須の設定値が設定されているかをチェックし、不足している場合は警告を出力します。

4. **モックモードのサポート**: テスト用のモックモードをサポートすることで、実際のAPIを呼び出さずにテストできるようにしています。

5. **機密情報の保護**: 文字列表現では、APIキーやパスワードなどの機密情報をマスクしています。

## 7. 練習問題

1. `.env`ファイルを作成し、必要な設定値を設定してみましょう。

2. `Config`クラスを使用して、設定値を読み込み、S3キーを生成してみましょう。

3. モックモードを有効にして、APIキーなしで動作することを確認してみましょう。

4. 新しい設定項目を追加してみましょう（例：データ保存形式、API呼び出しの最大リトライ回数など）。

## 8. 参考資料

- [python-dotenv](https://github.com/theskumar/python-dotenv): Pythonで`.env`ファイルを扱うためのライブラリ
- [12-Factor App: Config](https://12factor.net/config): 設定管理のベストプラクティス
