#!/usr/bin/env python3
"""
AWS Lambda Function for Daily Stock Data Fetching (Mock Test Version)

This Lambda function simulates fetching the latest daily stock data from Alpha Vantage API
and storing it in AWS S3 or PostgreSQL. It is designed to be used for testing with mock mode enabled.
"""

import os
import sys
import json
import logging
import time
import traceback
from datetime import datetime, timedelta

# タイムゾーン処理用
try:
    # Python 3.9以降の標準ライブラリ
    from zoneinfo import ZoneInfo
    def get_jst_time():
        return datetime.now(ZoneInfo("Asia/Tokyo"))
except ImportError:
    # Python 3.9未満またはzoneinfo非対応環境用
    try:
        import pytz
        def get_jst_time():
            return datetime.now(pytz.timezone('Asia/Tokyo'))
    except ImportError:
        # pytzも利用できない場合は、UTCに9時間を加算
        def get_jst_time():
            return datetime.now() + timedelta(hours=9)

# PostgreSQL接続用
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("psycopg2がインストールされていないため、PostgreSQLは使用できません。")

# ロガー初期化
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def setup_logging():
    """
    Set up logging configuration.
    
    Returns:
        Logger object
    """
    # ロガー初期化
    logger = logging.getLogger(__name__)
    
    # Lambda環境ではログディレクトリを/tmp以下に設定
    log_dir = '/tmp/logs'
    
    # ログディレクトリが存在しない場合は作成
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"ログディレクトリを作成しました: {log_dir}")
    except Exception as e:
        logger.error(f"ログディレクトリの作成に失敗しました: {e}")
        logger.error(traceback.format_exc())
    
    # ハンドラーを設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # フォーマッターを設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # ロガーにハンドラーを追加
    logger.addHandler(console_handler)
    
    return logger

def get_postgres_connection():
    """
    PostgreSQLデータベースへの接続を取得する
    
    Returns:
        Connection: PostgreSQL接続オブジェクト
    """
    if not POSTGRES_AVAILABLE:
        raise ImportError("psycopg2がインストールされていないため、PostgreSQLは使用できません。")
    
    # 環境変数から接続情報を取得
    db_name = os.environ.get('POSTGRES_DB', 'prod_db')
    user = os.environ.get('POSTGRES_USER', 'myuser')
    password = os.environ.get('POSTGRES_PASSWORD', '0000')
    host = os.environ.get('POSTGRES_HOST', 'localhost')
    port = os.environ.get('POSTGRES_PORT', '5434')
    
    # 接続文字列を作成
    conn_string = f"dbname='{db_name}' user='{user}' password='{password}' host='{host}' port='{port}'"
    
    # 接続を作成
    conn = psycopg2.connect(conn_string)
    
    return conn

def create_tables_if_not_exist(conn):
    """
    必要なテーブルが存在しない場合は作成する
    
    Args:
        conn: PostgreSQL接続オブジェクト
    """
    with conn.cursor() as cur:
        # stock_dataテーブルの作成
        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open NUMERIC(10, 2) NOT NULL,
            high NUMERIC(10, 2) NOT NULL,
            low NUMERIC(10, 2) NOT NULL,
            close NUMERIC(10, 2) NOT NULL,
            volume BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        );
        """)
        
        # stock_metadataテーブルの作成
        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_metadata (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            last_updated TIMESTAMP NOT NULL,
            latest_date DATE NOT NULL,
            data_points INTEGER NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol)
        );
        """)
        
        conn.commit()

def save_to_postgres(conn, stock_data, logger):
    """
    PostgreSQLにデータを保存する
    
    Args:
        conn: PostgreSQL接続オブジェクト
        stock_data: 保存するデータ
        logger: ロガーオブジェクト
    """
    try:
        with conn.cursor() as cur:
            # stock_dataテーブルにデータを挿入または更新
            cur.execute("""
            INSERT INTO stock_data (symbol, date, timestamp, open, high, low, close, volume)
            VALUES (%(symbol)s, %(date)s, %(timestamp)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
            ON CONFLICT (symbol, date) 
            DO UPDATE SET 
                timestamp = EXCLUDED.timestamp,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
            """, {
                'symbol': stock_data['symbol'],
                'date': stock_data['date'],
                'timestamp': stock_data['timestamp'],
                'open': stock_data['open'],
                'high': stock_data['high'],
                'low': stock_data['low'],
                'close': stock_data['close'],
                'volume': stock_data['volume']
            })
            
            # stock_metadataテーブルにデータを挿入または更新
            cur.execute("""
            INSERT INTO stock_metadata (symbol, last_updated, latest_date, data_points, start_date, end_date)
            VALUES (%(symbol)s, %(last_updated)s, %(latest_date)s, %(data_points)s, %(start_date)s, %(end_date)s)
            ON CONFLICT (symbol) 
            DO UPDATE SET 
                last_updated = EXCLUDED.last_updated,
                latest_date = EXCLUDED.latest_date,
                data_points = EXCLUDED.data_points,
                start_date = EXCLUDED.start_date,
                end_date = EXCLUDED.end_date;
            """, {
                'symbol': stock_data['symbol'],
                'last_updated': datetime.now().isoformat(),
                'latest_date': stock_data['date'],
                'data_points': 1,
                'start_date': stock_data['date'],
                'end_date': stock_data['date']
            })
            
            conn.commit()
            logger.info(f"PostgreSQLにデータを保存しました: {stock_data['symbol']} ({stock_data['date']})")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"PostgreSQLへのデータ保存に失敗しました: {e}")
        logger.error(traceback.format_exc())
        raise

def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Dictionary with execution results
    """
    start_time = time.time()
    
    # ロギングの設定
    logger = setup_logging()
    
    # 環境変数を取得
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')
    s3_bucket = os.environ.get('S3_BUCKET', 'mock-bucket')
    region = os.environ.get('REGION', 'ap-northeast-1')
    stock_symbols = os.environ.get('STOCK_SYMBOLS', 'NVDA,AAPL,MSFT')
    mock_mode = os.environ.get('MOCK_MODE', 'true').lower() == 'true'  # デフォルトでmockモード
    debug_mode = os.environ.get('DEBUG_MODE', 'true').lower() == 'true'  # デフォルトでdebugモード
    storage_type = os.environ.get('STORAGE_TYPE', 's3').lower()  # デフォルトでS3
    
    # 実行モードを設定
    env_type = "Lambda (SAM Test)"
    if mock_mode:
        env_type += " (Mock)"
    
    # 実行開始ログ
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Lambda function for daily stock data fetch at {datetime.now().isoformat()}")
    logger.info(f"🔧 Environment: {env_type}")
    logger.info(f"🔑 API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'}")
    logger.info(f"🪣 S3 Bucket: {s3_bucket}")
    logger.info(f"🌐 Region: {region}")
    logger.info(f"📊 Stock Symbols: {stock_symbols}")
    logger.info(f"🐛 Debug Mode: {debug_mode}")
    logger.info(f"💾 Storage Type: {storage_type}")
    logger.info("=" * 80)
    
    # PostgreSQL接続の初期化（storage_typeがpostgresの場合）
    postgres_conn = None
    if storage_type == 'postgres':
        try:
            logger.info("PostgreSQLに接続しています...")
            postgres_conn = get_postgres_connection()
            create_tables_if_not_exist(postgres_conn)
            logger.info("PostgreSQLに接続しました")
        except Exception as e:
            logger.error(f"PostgreSQLへの接続に失敗しました: {e}")
            logger.error(traceback.format_exc())
            if storage_type == 'postgres':
                # PostgreSQLが必須の場合はエラーを発生させる
                raise
    
    try:
        # モックモードの場合はダミーデータを返す
        if mock_mode:
            logger.info("モックモードで実行中です。ダミーデータを返します。")
            
            # 株式シンボルのリスト
            symbols = stock_symbols.split(',')
            
            # 各シンボルに対してダミーデータを生成
            results = {}
            for symbol in symbols:
                logger.info(f"シンボル {symbol} のダミーデータを生成します...")
                
                # ダミーデータを生成
                dummy_data = {
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'open': 100.0 + (hash(symbol) % 100),
                    'high': 110.0 + (hash(symbol) % 100),
                    'low': 90.0 + (hash(symbol) % 100),
                    'close': 105.0 + (hash(symbol) % 100),
                    'volume': 1000000 + (hash(symbol) % 1000000)
                }
                
                logger.info(f"ダミーデータを生成しました: {symbol}")
                logger.info(f"データ: {json.dumps(dummy_data, indent=2)}")
                
                # データを保存
                if storage_type == 'postgres' and postgres_conn:
                    try:
                        save_to_postgres(postgres_conn, dummy_data, logger)
                        results[symbol] = 'success'
                    except Exception as e:
                        logger.error(f"PostgreSQLへのデータ保存に失敗しました: {e}")
                        results[symbol] = 'error'
                else:
                    # S3への保存はモックとして成功を返す
                    logger.info(f"S3にデータを保存します（モック）: s3://{s3_bucket}/{symbol}/latest.json")
                    results[symbol] = 'success'
                
            # 実行時間を計算
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 結果を集計
            success_count = sum(1 for result in results.values() if result == 'success')
            failure_count = sum(1 for result in results.values() if result != 'success')
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'execution_time': f"{execution_time:.2f} seconds",
                    'message': 'Mock mode execution successful',
                    'storage_type': storage_type,
                    'results': results,
                    'success_count': success_count,
                    'failure_count': failure_count,
                    'data': {
                        'symbols': symbols,
                        'timestamp': datetime.now().isoformat()
                    }
                })
            }
        
        # 実際のデータ取得処理（モックモードでない場合）
        logger.info("Alpha Vantage APIからデータを取得します...")
        
        # ここで実際のデータ取得処理を行う（今回は実装しない）
        logger.warning("モックモードが無効ですが、実際のAPI呼び出しは実装されていません。")
        
        # 実行時間を計算
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': False,
                'execution_time': f"{execution_time:.2f} seconds",
                'message': 'Non-mock mode not implemented',
            })
        }
    except Exception as e:
        # エラーが発生した場合
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.error(f"❌ Lambda関数でエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        
        # Lambda関数の戻り値（エラー）
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'execution_time': f"{execution_time:.2f} seconds",
                'error': str(e)
            })
        }
    finally:
        # PostgreSQL接続を閉じる
        if postgres_conn:
            postgres_conn.close()
            logger.info("PostgreSQL接続を閉じました")

# ローカルテスト用
if __name__ == "__main__":
    try:
        # テスト用のイベントとコンテキスト
        test_event = {}
        test_context = None
        
        # Lambda関数を実行
        result = lambda_handler(test_event, test_context)
        print(f"Lambda function result: {json.dumps(result, indent=2)}")
    except Exception as e:
        # Catch any unexpected exceptions
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)
