#APIを叩いてdaily adjusted dataを取得する
import os
import requests
from dotenv import load_dotenv
import logging
import pandas as pd


load_dotenv('configs/secrets/.env')
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

BASE_URL = 'https://www.alphavantage.co/query'
SYMBOL = 'NVDA'
FUNCTION = 'TIME_SERIES_DAILY'

params = {
    "function": FUNCTION,
    "symbol": SYMBOL,
    "apikey": API_KEY,
    "outputsize": "compact",  # "compact" = 直近100日間, "full" = 全データ
    "datatype": "json"  # デフォルトはJSONなので省略可能
}

#ログの設定
logger = None
def set_logger():
    log_dir = 'tests/test_log'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'test_fetch.log')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_file)  # ✅ ログファイルの保存先を設定

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    return logger

logger = set_logger()

def fetch_stock_data():

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"API Response: {data}")

        # データ構造の確認
        if "Time Series (Daily)" not in data:
            raise ValueError(f"Unexpected response format: {data}")
        return data
    except requests.exceptions.RequestException as e:
        logger.exception(f"API request failed: {e}")
        return None
    except ValueError as ve:
        logger.exception(f"Data format error: {ve}")
        return None
    
stock_data = fetch_stock_data()

if stock_data:
    latest_date = max(stock_data["Time Series (Daily)"].keys())
    latest_data = stock_data["Time Series (Daily)"][latest_date]

    # 主要データを表示
    print(f"NVIDIA ({SYMBOL}) - {latest_date}")
    print(f"Open: {latest_data['1. open']}")
    print(f"High: {latest_data['2. high']}")
    print(f"Low: {latest_data['3. low']}")
    print(f"Close: {latest_data['4. close']}")
 


def check_data_quality(stock_data):
    """取得したデータの品質をチェック"""
    
    time_series = stock_data.get("Time Series (Daily)", {})

    if not time_series:
        print("⚠️ データが空です！APIレスポンスを確認してください")
        return False

    # DataFrameに変換
    df = pd.DataFrame.from_dict(time_series, orient="index", dtype="float")
    df.index = pd.to_datetime(df.index)  # インデックスを日付型に変換

    # カラム名を分かりやすく変更
    df.columns = ["open", "high", "low", "close", "volume"]

    # **1. 日付の並び順**
    if not df.index.is_monotonic_decreasing:
        print("⚠️ 日付が降順になっていません！")
        return False

    # **2. 欠損値の確認**
    if df.isnull().sum().sum() > 0:
        print(f"⚠️ 欠損値が含まれています！\n{df.isnull().sum()}")
        return False

    # **3. 異常値の確認（出来高 = 0 の行）**
    if (df["volume"] == 0).any():
        print(f"⚠️ 異常値: 出来高が0のデータがあります！\n{df[df['volume'] == 0]}")
        return False

    # **4. 価格の異常値**
    if (df["low"] < 0).any() or (df["high"] > df["high"].quantile(0.99) * 10).any():
        print(f"⚠️ 異常値: 価格に極端な値が含まれています！")
        return False

    print("✅ データ品質チェック OK！問題ありません。")
    return True

# チェック実行
is_valid = check_data_quality(stock_data)

if not is_valid:
    print("⚠️ データに問題があります！")