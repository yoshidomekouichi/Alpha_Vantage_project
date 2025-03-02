import os
import logging
import requests
import pandas as pd
import psycopg2
from pathlib import Path
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ✅ 環境変数のロード
dotenv_path = Path(__file__).parent.parent.parent / ".env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    raise FileNotFoundError(f"⚠️ .env ファイルが見つかりません: {dotenv_path}")

# ✅ データベース設定
DB_CONFIG = {
    "dbname": "prod_db",
    "user": "myuser",
    "password": "0000",
    "host": "localhost",
    "port": "5434"  # Docker側のポートに合わせる！
}

# ✅ ログの設定
class LoggerManager:
    def __init__(self, script_name):
        self.log_dir = Path(__file__).parent.parent.parent / "logs"
        os.makedirs(self.log_dir, exist_ok=True)

        log_file = self.log_dir / f"{script_name}.log"

        self.logger = logging.getLogger(script_name)
        self.logger.setLevel(logging.DEBUG)

        # ✅ 既存のハンドラーがなければ追加
        if not self.logger.hasHandlers():
            file_handler = logging.FileHandler(log_file, mode='a')  # ✅ 追記モードにする
            console_handler = logging.StreamHandler()

            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        self.logger.propagate = False  # ✅ root ロガーへの伝播を防ぐ

    def get_logger(self):
        return self.logger

# ✅ APIデータ取得関数（API仕様変更のチェック込み）
def fetch_stock_data(history=False):
    BASE_URL = 'https://www.alphavantage.co/query'
    SYMBOL = 'NVDA'
    API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": SYMBOL,
        "apikey": API_KEY,
        "datatype": "json"
    }

    if history:
        params["outputsize"] = "full"

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"🛠 APIリクエストURL: {response.url}")
        if "Time Series (Daily)" not in data:
            raise ValueError(f"❌ API仕様変更の可能性: 'Time Series (Daily)' キーが見つかりません！\nレスポンス: {data}")

        sample_date = max(data["Time Series (Daily)"].keys())
        sample_data = data["Time Series (Daily)"][sample_date]

        expected_keys = {"1. open", "2. high", "3. low", "4. close", "5. volume"}
        actual_keys = set(sample_data.keys())

        if actual_keys != expected_keys:
            raise ValueError(f"❌ APIレスポンスのフォーマット変更 detected！\n期待: {expected_keys}\n実際: {actual_keys}")

        return {"Time Series (Daily)": data["Time Series (Daily)"]} if history else {"Time Series (Daily)": {max(data["Time Series (Daily)"].keys()): data["Time Series (Daily)"][max(data["Time Series (Daily)"].keys())]}}

    except requests.exceptions.RequestException as e:
        logging.exception(f"❌ API リクエストエラー: {e}")
        return None
    except ValueError as ve:
        logging.exception(f"❌ APIレスポンス異常: {ve}")
        return None

# ✅ データ品質チェック関数
def check_data_quality(stock_data):
    time_series = stock_data.get("Time Series (Daily)", {})

    if not time_series:
        logging.warning("⚠️ データが空です！APIレスポンスを確認してください")
        return False

    df = pd.DataFrame.from_dict(time_series, orient="index")
    df = df.astype(float)  # ここで明示的に変換
    df.index = pd.to_datetime(df.index)
    df.columns = ["open", "high", "low", "close", "volume"]

    if not df.index.is_monotonic_decreasing:
        logging.warning("⚠️ 日付が降順になっていません！")
        return False
    if df.isnull().sum().sum() > 0:
        logging.warning(f"⚠️ 欠損値が含まれています！\n{df.isnull().sum()}")
        return False
    if (df["volume"] == 0).any():
        logging.warning(f"⚠️ 出来高が0のデータがあります！\n{df[df['volume'] == 0]}")
        return False
    if (df["low"] < 0).any() or (df["high"] > df["high"].quantile(0.99) * 10).any():
        logging.warning("⚠️ 価格に極端な値が含まれています！")
        return False

    logging.info("✅ データ品質チェック OK！")
    return True

# ✅ DB保存関数
def save_to_db(stock_data):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        time_series = stock_data.get("Time Series (Daily)", {})
        rows = [(date, float(data["1. open"]), float(data["2. high"]), float(data["3. low"]),
                 float(data["4. close"]), int(data["5. volume"]))
                for date, data in time_series.items()]

        insert_sql = """
        INSERT INTO test_stock_prices (date, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (date) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume;
        """
        execute_values(cur, insert_sql, rows)
        conn.commit()
        logging.info(f"✅ {len(rows)}件のデータを保存しました！")
    except Exception as e:
        logging.exception(f"❌ データ保存エラー: {e}")
    finally:
        if conn:
            conn.close()
            logging.debug("データベース接続を閉じました")