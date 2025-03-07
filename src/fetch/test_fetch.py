import os
import requests
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv



# ✅ 環境変数のロード
load_dotenv('/Users/koichi/Library/CloudStorage/GoogleDrive-yoshidome.kouichi@gmail.com/.shortcut-targets-by-id/1YPflACfNCBy1sNnuIrSAGpX5J8mL3Pcn/Google Drive/01.Private/Documents/Alpha_Vantage_project/configs/secrets/.env')
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
if not API_KEY:
    raise ValueError("APIキーがロードされていません。環境変数を確認してください。")

# ✅ Alpha Vantage API 設定
BASE_URL = 'https://www.alphavantage.co/query'
SYMBOL = 'NVDA'
FUNCTION = 'TIME_SERIES_DAILY'

params = {
    "function": FUNCTION,
    "symbol": SYMBOL,
    "apikey": API_KEY,
    "outputsize": "compact",
    "datatype": "json"
}

# ✅ データベース設定

DB_CONFIG = {
    "dbname": "prod_db",
    "user": "myuser",
    "password": "0000",
    "host": "localhost",
    "port": "5434",  # Docker側のポートに合わせる！
}


# ✅ ログの設定
def set_logger():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'alpha_vantage_API_fetch.log')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_file)

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

logger = set_logger()

# ✅ API からデータ取得
def fetch_stock_data():
    logger.debug("スクリプト開始")
    logger.debug(f"API_KEY: {API_KEY}")  # APIキーの確認
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"API Response Status: {response.status_code}")
        logger.debug(f"API Response Content: {response.text[:500]}")  # 500文字だけ出力
        logger.debug(f"API Request URL: {response.url}")  # リクエストURLの確認

        if "Time Series (Daily)" not in data:
            raise ValueError(f"Unexpected response format: {data}")
        return data
    except requests.exceptions.RequestException as e:
        logger.exception(f"API request failed: {e}")
        return None
    except ValueError as ve:
        logger.exception(f"Data format error: {ve}")
        return None

# ✅ データ品質チェック
def check_data_quality(stock_data):
    time_series = stock_data.get("Time Series (Daily)", {})

    if not time_series:
        logger.warning("⚠️ データが空です！APIレスポンスを確認してください")
        return False

    df = pd.DataFrame.from_dict(time_series, orient="index", dtype="float")
    df.index = pd.to_datetime(df.index)
    df.columns = ["open", "high", "low", "close", "volume"]

    if not df.index.is_monotonic_decreasing:
        logger.warning("⚠️ 日付が降順になっていません！")
        return False
    if df.isnull().sum().sum() > 0:
        logger.warning(f"⚠️ 欠損値が含まれています！\n{df.isnull().sum()}")
        return False
    if (df["volume"] == 0).any():
        logger.warning(f"⚠️ 出来高が0のデータがあります！\n{df[df['volume'] == 0]}")
        return False
    if (df["low"] < 0).any() or (df["high"] > df["high"].quantile(0.99) * 10).any():
        logger.warning("⚠️ 価格に極端な値が含まれています！")
        return False

    logger.info("✅ データ品質チェック OK！")
    return True

def save_to_db(stock_data):
    conn = None
    try:
        logger.debug("データベース接続を開始")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # テーブルが無ければ作成
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS test_stock_prices (
            date DATE PRIMARY KEY,
            open NUMERIC(10,2),
            high NUMERIC(10,2),
            low NUMERIC(10,2),
            close NUMERIC(10,2),
            volume BIGINT
        );
        """
        cur.execute(create_table_sql)  # テーブル作成を実行
        conn.commit()  # 変更を確定

        time_series = stock_data.get("Time Series (Daily)", {})
        rows = [
            (date, float(data["1. open"]), float(data["2. high"]), float(data["3. low"]),
             float(data["4. close"]), int(data["5. volume"]))
            for date, data in time_series.items()
        ]

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
        logger.info(f"✅ {len(rows)}件のデータを保存しました！")
    except Exception as e:
        logger.exception(f"❌ データ保存エラー: {e}")
    finally:
        if conn:
            conn.close()
            logger.debug("データベース接続を閉じました")

# ✅ メイン処理
if __name__ == "__main__":
    logger.info("🚀 データ取得を開始")

    stock_data = fetch_stock_data()

    if stock_data:
        is_valid = check_data_quality(stock_data)
        if is_valid:
            save_to_db(stock_data)

    logger.info("🎉 処理完了")