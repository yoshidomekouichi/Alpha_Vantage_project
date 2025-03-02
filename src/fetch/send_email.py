import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv

# ✅ 環境変数のロード
dotenv_path = "/Users/koichi/Desktop/local_document/Alpha_Vantage_project/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    raise FileNotFoundError(f"⚠️ .env ファイルが見つかりません: {dotenv_path}")

# ✅ メール設定（環境変数から取得）
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = TO_EMAIL

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, TO_EMAIL, msg.as_string())
        server.quit()
        print("✅ メール送信成功！")
    except Exception as e:
        print(f"❌ メール送信失敗: {e}")

# ✅ `fetch_daily.py` のログを送信
LOG_PATH = "/Users/koichi/Desktop/local_document/Alpha_Vantage_project/logs/cron_fetch_daily.log"
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r") as f:
        log_content = f.read()
    send_email("【cron】fetch_daily.py 実行結果", log_content)
else:
    send_email("【cron】fetch_daily.py 実行結果", "⚠️ ログファイルが見つかりませんでした！")