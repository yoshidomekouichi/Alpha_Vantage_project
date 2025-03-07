# ロギングモジュール

このドキュメントでは、Alpha Vantage株価データパイプラインのロギングモジュールについて説明します。

## 1. ロギングモジュールの概要

ロギングモジュールは、アプリケーションの実行中に発生するイベント、エラー、警告などの情報を記録するための機能を提供します。主な機能は以下の通りです：

- コンソールと複数のファイルへのログ出力
- 異なるログレベル（DEBUG、INFO、WARNING、ERROR、CRITICAL）のサポート
- カスタマイズ可能なログフォーマット
- 実行環境（本番、モック）に応じたログ出力先の切り替え
- 実行時間の計測と記録
- デバッグモードのサポート

## 2. 主要なファイル

- `src/utils/logging_utils.py`: ロギングユーティリティクラスと関数
- `src/core/logging.py`: コアロギング設定（このプロジェクトでは使用されていない可能性があります）

## 3. `LoggerManager`クラスの詳細

### 3.1 初期化

```python
def __init__(
    self, 
    name: str, 
    log_dir: str = None, 
    console_level: int = logging.INFO, 
    file_level: int = logging.DEBUG,
    log_format: str = "%(asctime)s [%(levelname)s] %(message)s",
    date_format: str = "%Y-%m-%d %H:%M:%S",
    add_timestamp_to_filename: bool = False,
    is_mock: bool = False
):
    """
    ロガーマネージャーを初期化します。
    
    引数:
        name: ロガー名
        log_dir: ログファイルのディレクトリ（デフォルト: project_root/logs）
        console_level: コンソール出力のログレベル
        file_level: ファイル出力のログレベル
        log_format: ログメッセージのフォーマット文字列
        date_format: タイムスタンプのフォーマット文字列
        add_timestamp_to_filename: ログファイル名にタイムスタンプを追加するかどうか
        is_mock: モック環境かどうか
    """
    self.name = name
    self.log_format = log_format
    self.date_format = date_format
    self.is_mock = is_mock
    
    # ログディレクトリの設定
    if log_dir is None:
        # デフォルトはproject_root/logs
        self.log_dir = Path(__file__).parent.parent.parent / "logs"
    else:
        self.log_dir = Path(log_dir)
    
    # 環境固有のサブディレクトリを使用
    if self.is_mock:
        self.log_dir = self.log_dir / "mock"
    else:
        self.log_dir = self.log_dir / "prod"
        
    # デバッグ用に出力
    print(f"Log directory: {self.log_dir}")
    
    try:
        os.makedirs(self.log_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating log directory: {e}")
        # フォールバックディレクトリを使用
        self.log_dir = Path.cwd() / "logs"
        if self.is_mock:
            self.log_dir = self.log_dir / "mock"
        else:
            self.log_dir = self.log_dir / "prod"
        print(f"Using fallback log directory: {self.log_dir}")
        os.makedirs(self.log_dir, exist_ok=True)
    
    # ロガーの作成
    self.logger = logging.getLogger(name)
    self.logger.setLevel(logging.DEBUG)  # 最低レベルに設定し、ハンドラーでフィルタリング
    self.logger.propagate = False  # ルートロガーへの伝播を防止
    
    # 既存のハンドラーをクリア
    if self.logger.hasHandlers():
        self.logger.handlers.clear()
    
    # フォーマッターの作成
    self.formatter = logging.Formatter(log_format, date_format)
    
    # コンソールハンドラーの設定
    self.console_handler = logging.StreamHandler(sys.stdout)
    self.console_handler.setLevel(console_level)
    self.console_handler.setFormatter(self.formatter)
    self.logger.addHandler(self.console_handler)
    
    # ファイルハンドラーの設定
    if add_timestamp_to_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{name}_{timestamp}.log"
    else:
        log_filename = f"{name}.log"
        
    log_file_path = self.log_dir / log_filename
    
    self.file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    self.file_handler.setLevel(file_level)
    self.file_handler.setFormatter(self.formatter)
    self.logger.addHandler(self.file_handler)
    
    # 初期化のログ
    env_type = "Mock" if self.is_mock else "Production"
    self.logger.debug(f"{env_type} logger initialized. Log file: {log_file_path}")
```

初期化時に、ロガー名、ログディレクトリ、ログレベル、フォーマットなどを設定し、コンソールとファイルの両方にログを出力するためのハンドラーを作成します。モック環境と本番環境で異なるログディレクトリを使用することで、テスト時のログと本番のログを分離できます。

### 3.2 ロガーの取得

```python
def get_logger(self) -> logging.Logger:
    """設定されたロガーインスタンスを取得します。"""
    return self.logger
```

このメソッドは、設定されたロガーインスタンスを返します。他のクラスやモジュールでこのロガーを使用できます。

### 3.3 区切り線の追加

```python
def add_separator(self, char: str = "-", length: int = 80):
    """ログに区切り線を追加します。"""
    self.logger.info(char * length)
```

このメソッドは、ログに区切り線を追加します。ログの可読性を向上させるために使用されます。

### 3.4 実行開始のログ

```python
def log_execution_start(self, script_name: str, params: Dict[str, Any] = None):
    """明確な区切り線でスクリプト実行の開始をログに記録します。"""
    self.add_separator("=")
    self.logger.info(f"🚀 EXECUTION START: {script_name} at {datetime.now().strftime(self.date_format)}")
    if params:
        self.logger.info(f"📋 Parameters: {params}")
    self.add_separator("=")
```

このメソッドは、スクリプトの実行開始をログに記録します。スクリプト名とパラメータを含め、区切り線で囲むことで、ログの可読性を向上させます。

### 3.5 実行終了のログ

```python
def log_execution_end(self, script_name: str, success: bool = True, execution_time: float = None):
    """明確な区切り線でスクリプト実行の終了をログに記録します。"""
    self.add_separator("=")
    status = "✅ SUCCESS" if success else "❌ FAILURE"
    self.logger.info(f"{status}: {script_name} at {datetime.now().strftime(self.date_format)}")
    if execution_time is not None:
        self.logger.info(f"⏱ Execution time: {execution_time:.2f} seconds")
    self.add_separator("=")
```

このメソッドは、スクリプトの実行終了をログに記録します。成功/失敗のステータスと実行時間を含め、区切り線で囲むことで、ログの可読性を向上させます。

### 3.6 ログレベルの設定

```python
def set_console_level(self, level: int):
    """コンソール出力のログレベルを設定します。"""
    self.console_handler.setLevel(level)

def set_file_level(self, level: int):
    """ファイル出力のログレベルを設定します。"""
    self.file_handler.setLevel(level)
```

これらのメソッドは、コンソールとファイルのログレベルを個別に設定します。例えば、コンソールには重要なメッセージのみを表示し、ファイルには詳細なログを記録するといった使い方ができます。

### 3.7 デバッグモードの設定

```python
def set_debug_mode(self, enabled: bool = True):
    """デバッグモードを有効または無効にします（コンソールレベルをDEBUGに設定）。"""
    if enabled:
        self.set_console_level(logging.DEBUG)
        self.logger.debug("🔍 Debug mode enabled")
    else:
        self.set_console_level(logging.INFO)
        self.logger.info("🔍 Debug mode disabled")
```

このメソッドは、デバッグモードを有効または無効にします。デバッグモードが有効な場合、コンソールのログレベルがDEBUGに設定され、より詳細なログが表示されます。

## 4. ユーティリティ関数

### 4.1 デフォルトロガーの作成

```python
def create_default_logger(name: str, debug_mode: bool = False, is_mock: bool = False) -> logging.Logger:
    """
    デフォルト設定でロガーを作成します。
    
    引数:
        name: ロガー名
        debug_mode: デバッグモードを有効にするかどうか
        is_mock: モック環境かどうか
        
    戻り値:
        設定されたロガーインスタンス
    """
    console_level = logging.DEBUG if debug_mode else logging.INFO
    manager = LoggerManager(name, console_level=console_level, is_mock=is_mock)
    return manager.get_logger()
```

この関数は、デフォルト設定でロガーを作成します。簡単にロガーを作成したい場合に便利です。

### 4.2 実行時間のログ記録デコレータ

```python
def log_execution_time(logger, func_name: str = None):
    """
    関数の実行時間をログに記録するデコレータ。
    
    引数:
        logger: ロガーインスタンス
        func_name: ログに使用する関数名（デフォルトは関数名）
        
    戻り値:
        デコレートされた関数
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = func_name or func.__name__
            start_time = time.time()
            logger.debug(f"⏱ Starting {name}")
            
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time
                logger.debug(f"⏱ {name} completed in {execution_time:.2f} seconds")
                return result
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.error(f"❌ {name} failed after {execution_time:.2f} seconds: {e}")
                raise
                
        return wrapper
    return decorator
```

この関数は、関数の実行時間をログに記録するデコレータを提供します。関数の開始時と終了時にログを出力し、実行時間を計測します。例外が発生した場合も、実行時間とエラーメッセージをログに記録します。

## 5. ログレベル

Pythonのロギングモジュールは、以下の5つのログレベルを提供しています：

1. **DEBUG** (10): 詳細なデバッグ情報
2. **INFO** (20): 一般的な情報メッセージ
3. **WARNING** (30): 警告メッセージ（潜在的な問題）
4. **ERROR** (40): エラーメッセージ（処理を続行できる問題）
5. **CRITICAL** (50): 重大なエラーメッセージ（プログラムが続行できない問題）

ログレベルは数値で表され、設定されたレベル以上のメッセージのみが出力されます。例えば、ログレベルがINFO (20)に設定されている場合、INFO、WARNING、ERROR、CRITICALのメッセージが出力されますが、DEBUGメッセージは出力されません。

## 6. ロギングの使用例

### 6.1 基本的な使用例

```python
# ロガーマネージャーの作成
from src.utils.logging_utils import LoggerManager
logger_manager = LoggerManager(
    name="my_app",
    console_level=logging.INFO,
    file_level=logging.DEBUG,
    add_timestamp_to_filename=True
)

# ロガーの取得
logger = logger_manager.get_logger()

# 各レベルのログ出力
logger.debug("🔍 This is a debug message")
logger.info("ℹ️ This is an info message")
logger.warning("⚠️ This is a warning message")
logger.error("❌ This is an error message")
logger.critical("🔥 This is a critical message")

# 区切り線の追加
logger_manager.add_separator()

# デバッグモードの有効化
logger_manager.set_debug_mode(True)

# 実行開始と終了のログ
logger_manager.log_execution_start("my_script.py", {"param1": "value1"})
# ... スクリプトの処理 ...
logger_manager.log_execution_end("my_script.py", success=True, execution_time=1.23)
```

### 6.2 実行時間のログ記録デコレータの使用例

```python
from src.utils.logging_utils import log_execution_time
import logging

logger = logging.getLogger("my_logger")

@log_execution_time(logger)
def process_data(data):
    # ... データ処理 ...
    return result

@log_execution_time(logger, func_name="Custom Name")
def complex_calculation(a, b):
    # ... 複雑な計算 ...
    return result

# 関数の呼び出し
result1 = process_data(data)
result2 = complex_calculation(10, 20)
```

### 6.3 スクリプト全体での使用例

```python
import time
from src.utils.logging_utils import LoggerManager

def main():
    # ロガーの設定
    logger_manager = LoggerManager(
        name="my_script",
        add_timestamp_to_filename=True,
        is_mock=False
    )
    logger = logger_manager.get_logger()
    
    # 実行開始のログ
    start_time = time.time()
    logger_manager.log_execution_start("my_script.py", {"param1": "value1"})
    
    try:
        # スクリプトの処理
        logger.info("ℹ️ Starting process 1")
        # ... 処理1 ...
        logger.info("✅ Process 1 completed")
        
        logger.info("ℹ️ Starting process 2")
        # ... 処理2 ...
        logger.info("✅ Process 2 completed")
        
        # 成功
        success = True
    except Exception as e:
        # エラーのログ
        logger.exception(f"❌ Error during execution: {e}")
        success = False
    
    # 実行終了のログ
    end_time = time.time()
    execution_time = end_time - start_time
    logger_manager.log_execution_end("my_script.py", success, execution_time)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
```

## 7. ロギングの利点

適切なロギングは、以下のような利点があります：

1. **デバッグの容易さ**: 問題が発生した場合、ログを確認することで原因を特定しやすくなります。
2. **実行の追跡**: スクリプトの実行フローを追跡できます。
3. **パフォーマンスの監視**: 各処理の実行時間を記録することで、パフォーマンスのボトルネックを特定できます。
4. **エラーの検出**: エラーや警告を早期に検出できます。
5. **監査**: 誰が何をいつ行ったかを記録できます。
6. **分析**: ログデータを分析することで、システムの動作パターンや問題点を把握できます。

## 8. ロギングのベストプラクティス

1. **適切なログレベルの使用**: 各メッセージに適切なログレベルを設定します。
   - DEBUG: 詳細なデバッグ情報
   - INFO: 一般的な情報メッセージ
   - WARNING: 潜在的な問題
   - ERROR: 処理を続行できる問題
   - CRITICAL: プログラムが続行できない問題

2. **構造化されたログメッセージ**: ログメッセージは構造化し、必要な情報を含めます。
   - タイムスタンプ
   - ログレベル
   - コンテキスト情報（関数名、ファイル名、行番号など）
   - 明確なメッセージ

3. **適切なログ出力先**: 用途に応じて適切なログ出力先を選択します。
   - コンソール: 開発中のデバッグ
   - ファイル: 永続的な記録
   - Syslog: 集中管理されたログ
   - クラウドロギングサービス: 分散システムのログ

4. **エラーのコンテキスト**: エラーが発生した場合、エラーメッセージだけでなく、エラーのコンテキスト（入力データ、状態など）も記録します。

5. **機密情報の保護**: パスワード、APIキー、個人情報などの機密情報はログに記録しないようにします。

6. **ログの回転**: ログファイルが大きくなりすぎないように、ログの回転（古いログの削除や圧縮）を設定します。

7. **エモジを使用したわかりやすさ**: ログメッセージにエモジを使用することで、視覚的にわかりやすくします。
   - ✅: 成功
   - ❌: エラー
   - ⚠️: 警告
   - ℹ️: 情報
   - 🔍: デバッグ
   - 🚀: 開始
   - ⏱: 時間計測

## 9. 設計のポイント

1. **モジュール化**: ロギング機能を独立したクラスにカプセル化しています。

2. **環境に応じた設定**: 本番環境とモック環境で異なるログ設定を使用できます。

3. **柔軟性**: ログレベル、フォーマット、出力先などをカスタマイズできます。

4. **使いやすさ**: デコレータやユーティリティ関数を提供することで、ロギングを簡単に使用できます。

5. **視覚的な区別**: エモジや区切り線を使用することで、ログの可読性を向上させています。

## 10. 練習問題

1. `LoggerManager`クラスに、ログの回転（ローテーション）機能を追加してみましょう。

2. `LoggerManager`クラスに、Slackやメールにエラーログを送信する機能を追加してみましょう。

3. `log_execution_time`デコレータを拡張して、関数の引数と戻り値もログに記録するようにしてみましょう。

4. 複数のロガーを一元管理するためのクラスを作成してみましょう。

## 11. 参考資料

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html): Pythonのロギングモジュールの公式ドキュメント
- [Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html): Pythonのロギングに関するレシピ集
- [12-Factor App: Logs](https://12factor.net/logs): ログに関するベストプラクティス
