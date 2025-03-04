from utils import LoggerManager, fetch_stock_data, save_to_db, check_data_quality

logger = LoggerManager("fetch_daily").get_logger()  # ✅ インスタンス化して呼び出す！

logger.info("🚀 cron で1日分のデータを取得開始")
logger.debug(f"📂 ログの出力先: {logger.handlers}")

stock_data = fetch_stock_data()
logger.debug(f"📊 取得したデータ: {stock_data}")

if stock_data:
    if check_data_quality(stock_data):
        save_to_db(stock_data)
        logger.info("✅ データ保存完了！")
        logger.info("🎉 cron 処理が正常に終了しました")
    else:
        logger.warning("⚠️ データ品質チェックに失敗したため、データは保存されませんでした！")
        logger.warning("⚠️ cron 処理は異常終了しました")
else:
    logger.error("❌ APIレスポンスに問題があるため、データ保存をスキップしました！")
    logger.error("❌ cron 処理は異常終了しました")