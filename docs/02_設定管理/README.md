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

設定初期化メソッドは、環境変数から各種設定値を読み込み、クラスの属性として設定します。各行の処理内容は以下の通りです：

1. `self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'`: 環境変数'DEBUG_MODE'の値を取得し、小文字に変換して'true'と比較します。一致する場合はTrueを、それ以外の場合はFalseを設定します。環境変数が設定されていない場合は'False'をデフォルト値として使用します。
2. `self.mock_mode = os.getenv('MOCK_MODE', 'False').lower() == 'true'`: 環境変数'MOCK_MODE'の値を取得し、小文字に変換して'true'と比較します。一致する場合はTrueを、それ以外の場合はFalseを設定します。
3. `self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')`: 環境変数'ALPHA_VANTAGE_API_KEY'の値をAPIキーとして設定します。
4. `self.api_base_url = os.getenv('ALPHA_VANTAGE_BASE_URL', 'https://www.alphavantage.co/query')`: 環境変数'ALPHA_VANTAGE_BASE_URL'の値をAPIのベースURLとして設定します。環境変数が設定されていない場合は'https://www.alphavantage.co/query'をデフォルト値として使用します。
5. `symbols_str = os.getenv('STOCK_SYMBOLS', 'NVDA')`: 環境変数'STOCK_SYMBOLS'の値を取得します。環境変数が設定されていない場合は'NVDA'をデフォルト値として使用します。
6. `if '#' in symbols_str:`: シンボル文字列にコメント（#以降の文字列）が含まれているかチェックします。
7. `symbols_str = symbols_str.split('#')[0].strip()`: コメントが含まれている場合、#より前の部分のみを取得し、前後の空白を削除します。
8. `self.stock_symbols = [s.strip() for s in symbols_str.split(',')]`: カンマで区切られたシンボル文字列をリストに変換します。各シンボルの前後の空白も削除します。
9. `s3_bucket = os.getenv('S3_BUCKET')`: 環境変数'S3_BUCKET'の値を取得します。
10. `if s3_bucket and '#' in s3_bucket:`: S3バケット名が設定されており、かつコメントが含まれているかチェックします。
11. `s3_bucket = s3_bucket.split('#')[0].strip()`: コメントが含まれている場合、#より前の部分のみを取得し、前後の空白を削除します。
12. `self.s3_bucket = s3_bucket`: S3バケット名を設定します。
13. `self.s3_region = os.getenv('AWS_REGION', 'ap-northeast-1')`: 環境変数'AWS_REGION'の値をAWSリージョンとして設定します。環境変数が設定されていない場合は'ap-northeast-1'をデフォルト値として使用します。
14. `self.s3_prefix = os.getenv('S3_PREFIX', 'stock-data')`: 環境変数'S3_PREFIX'の値をS3プレフィックス（パス）として設定します。環境変数が設定されていない場合は'stock-data'をデフォルト値として使用します。
15. `self.email_enabled = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'`: 環境変数'EMAIL_ENABLED'の値を取得し、小文字に変換して'true'と比較します。一致する場合はTrueを、それ以外の場合はFalseを設定します。
16. `if self.email_enabled:`: メール通知が有効かどうかをチェックします。
17. `self.email_config = {...}`: メール通知が有効な場合、メール設定を辞書として作成します。
18. `'smtp_server': os.getenv('SMTP_SERVER')`: SMTPサーバーアドレスを設定します。
19. `'smtp_port': os.getenv('SMTP_PORT', '587')`: SMTPポートを設定します。環境変数が設定されていない場合は'587'をデフォルト値として使用します。
20. `'smtp_user': os.getenv('SMTP_USER')`: SMTPユーザー名を設定します。
21. `'smtp_password': os.getenv('SMTP_PASSWORD')`: SMTPパスワードを設定します。
22. `'from_email': os.getenv('FROM_EMAIL')`: 送信者メールアドレスを設定します。
23. `'to_email': os.getenv('TO_EMAIL')`: 受信者メールアドレスを設定します。
24. `else:`: メール通知が無効な場合の処理です。
25. `self.email_config = None`: メール通知が無効な場合、メール設定をNoneに設定します。
26. `self.slack_enabled = os.getenv('SLACK_ENABLED', 'False').lower() == 'true'`: 環境変数'SLACK_ENABLED'の値を取得し、小文字に変換して'true'と比較します。一致する場合はTrueを、それ以外の場合はFalseを設定します。
27. `if self.slack_enabled:`: Slack通知が有効かどうかをチェックします。
28. `self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')`: Slack通知が有効な場合、Slack Webhook URLを設定します。
29. `else:`: Slack通知が無効な場合の処理です。
30. `self.slack_webhook_url = None`: Slack通知が無効な場合、Slack Webhook URLをNoneに設定します。
31. `self.log_dir = os.getenv('LOG_DIR', str(self.project_root / 'logs'))`: 環境変数'LOG_DIR'の値をログディレクトリとして設定します。環境変数が設定されていない場合は、プロジェクトルートの'logs'ディレクトリをデフォルト値として使用します。
32. `self.log_level = os.getenv('LOG_LEVEL', 'INFO')`: 環境変数'LOG_LEVEL'の値をログレベルとして設定します。環境変数が設定されていない場合は'INFO'をデフォルト値として使用します。
33. `self._validate_config()`: 設定の検証メソッドを呼び出します。

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

設定検証メソッドは、必須の設定値が設定されているかをチェックします。各行の処理内容は以下の通りです：

1. `missing_vars = []`: 不足している環境変数を格納するための空のリストを作成します。
2. `if not self.api_key and not self.mock_mode:`: APIキーが設定されておらず、かつモックモードでない場合の処理です。
3. `missing_vars.append('ALPHA_VANTAGE_API_KEY')`: APIキーが不足している場合、リストに追加します。
4. `if not self.s3_bucket:`: S3バケットが設定されていない場合の処理です。
5. `missing_vars.append('S3_BUCKET')`: S3バケットが不足している場合、リストに追加します。
6. `if self.email_enabled:`: メール通知が有効な場合の処理です。
7. `for key in ['SMTP_SERVER', 'SMTP_USER', 'SMTP_PASSWORD', 'FROM_EMAIL', 'TO_EMAIL']:`: メール通知に必要な環境変数をループで確認します。
8. `if not os.getenv(key):`: 環境変数が設定されていない場合の処理です。
9. `missing_vars.append(key)`: 不足している環境変数をリストに追加します。
10. `if self.slack_enabled and not self.slack_webhook_url:`: Slack通知が有効で、かつSlack Webhook URLが設定されていない場合の処理です。
11. `missing_vars.append('SLACK_WEBHOOK_URL')`: Slack Webhook URLが不足している場合、リストに追加します。
12. `if missing_vars:`: 不足している環境変数がある場合の処理です。
13. `if self.mock_mode and 'ALPHA_VANTAGE_API_KEY' in missing_vars:`: モックモードで、かつAPIキーが不足している環境変数リストに含まれている場合の処理です。
14. `missing_vars.remove('ALPHA_VANTAGE_API_KEY')`: モックモードではAPIキーは不要なため、リストから削除します。
15. `if missing_vars:`: 不足している環境変数がまだある場合の処理です。
16. `logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")`: 不足している環境変数をカンマ区切りで警告ログに出力します。

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
```

S3キー生成メソッドは、株価データを保存するためのS3キー（パス）を生成します。各行の処理内容は以下の通りです：

1. `if is_latest:`: 最新データかどうかをチェックします。
2. `return f"{self.s3_prefix}/{symbol}/latest.json"`: 最新データの場合、「プレフィックス/銘柄/latest.json」という形式のキーを返します。
3. `elif date:`: 日付が指定されているかどうかをチェックします。
4. `return f"{self.s3_prefix}/{symbol}/daily/{date}.json"`: 日付が指定されている場合、「プレフィックス/銘柄/daily/日付.json」という形式のキーを返します。
5. `else:`: 最新データでも日付指定でもない場合の処理です。
6. `return f"{self.s3_prefix}/{symbol}/full.json"`: 全データの場合、「プレフィックス/銘柄/full.json」という形式のキーを返します。

```python
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

メタデータキー生成メソッドは、メタデータを保存するためのS3キー（パス）を生成します：

1. `return f"{self.s3_prefix}/{symbol}/metadata.json"`: 「プレフィックス/銘柄/metadata.json」という形式のキーを返します。

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
```

設定辞書変換メソッドは、設定をPythonの辞書に変換します：

1. `return {...}`: 設定値を含む辞書を返します。
2. `'debug_mode': self.debug_mode`: デバッグモードの値を辞書に追加します。
3. `'mock_mode': self.mock_mode`: モックモードの値を辞書に追加します。
4. `'api_base_url': self.api_base_url`: APIベースURLの値を辞書に追加します。
5. `'stock_symbols': self.stock_symbols`: 株式銘柄のリストを辞書に追加します。
6. `'s3_bucket': self.s3_bucket`: S3バケット名を辞書に追加します。
7. `'s3_region': self.s3_region`: AWSリージョンを辞書に追加します。
8. `'s3_prefix': self.s3_prefix`: S3プレフィックスを辞書に追加します。
9. `'email_enabled': self.email_enabled`: メール通知の有効/無効状態を辞書に追加します。
10. `'slack_enabled': self.slack_enabled`: Slack通知の有効/無効状態を辞書に追加します。
11. `'log_dir': self.log_dir`: ログディレクトリを辞書に追加します。
12. `'log_level': self.log_level`: ログレベルを辞書に追加します。

```python
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

文字列表現メソッドは、設定をJSON形式の文字列に変換します。各行の処理内容は以下の通りです：

1. `config_dict = self.to_dict()`: 設定を辞書に変換します。
2. `if 'api_key' in config_dict:`: APIキーが辞書に含まれているかチェックします。
3. `config_dict['api_key'] = '***'`: APIキーを'***'でマスクします。
4. `if 'email_config' in config_dict and config_dict['email_config']:`: メール設定が辞書に含まれており、かつNoneでないかチェックします。
5. `if 'smtp_password' in config_dict['email_config']:`: SMTPパスワードがメール設定に含まれているかチェックします。
6. `config_dict['email_config']['smtp_password'] = '***'`: SMTPパスワードを'***'でマスクします。
7. `return json.dumps(config_dict, indent=2)`: 辞書をインデント付きのJSON文字列に変換して返します。

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
