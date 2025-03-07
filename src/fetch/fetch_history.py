from utils import LoggerManager, fetch_stock_data, save_to_db, check_data_quality

logger = LoggerManager("fetch_history").get_logger()  # ✅ インスタンス化して呼び出す！

logger.info("🚀 過去データの取得を開始")

stock_data = fetch_stock_data(history=True)
logger.debug(f"📊 取得したデータ: {stock_data}")

if stock_data:
    if check_data_quality(stock_data):
        save_to_db(stock_data)
        logger.info("✅ 過去データの保存完了！")
        logger.info("🎉 過去データの保存処理が正常に終了しました")
    else:
        logger.warning("⚠️ データ品質チェックに失敗したため、データは保存されませんでした！")
        logger.warning("⚠️ 過去データの保存処理は異常終了しました")
else:
    logger.error("❌ APIレスポンスに問題があるため、データ保存をスキップしました！")
    logger.error("❌ 過去データの保存処理は異常終了しました")