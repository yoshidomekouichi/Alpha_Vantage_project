# 通知モジュール

このドキュメントでは、Alpha Vantage株価データパイプラインの通知モジュールについて説明します。

## 1. 通知モジュールの概要

通知モジュールは、アプリケーションの実行結果や重要なイベントをユーザーに通知するための機能を提供します。主な機能は以下の通りです：

- メールによる通知
- Slackによる通知
- 成功、警告、エラーなど、異なる種類の通知
- カスタマイズ可能なメッセージ形式
- 通知の送信条件の制御

## 2. 主要なファイル

- `src/utils/alerts.py`: 通知機能を提供するクラスと関数
- `src/notifications/alerts.py`: 通知システムの実装（このプロジェクトでは使用されていない可能性があります）

## 3. `AlertManager`クラスの詳細

### 3.1 初期化

```python
def __init__(
    self,
    email_config: Optional[Dict[str, str]] = None,
    slack_webhook_url: Optional[str] = None,
    slack_webhook_url_error: Optional[str] = None,
    slack_webhook_url_warning: Optional[str] = None,
    slack_webhook_url_info: Optional[str] = None
):
    """
    アラートマネージャーを初期化します。
    
    引数:
        email_config: 以下のキーを持つメール設定辞書:
            - smtp_server: SMTPサーバーアドレス
            - smtp_port: SMTPサーバーポート
            - smtp_user: SMTPユーザー名
            - smtp_password: SMTPパスワード
            - from_email: 送信者メールアドレス
            - to_email: 受信者メールアドレス（文字列またはリスト）
        slack_webhook_url: メッセージ送信用のデフォルトSlack webhook URL
        slack_webhook_url_error: エラーメッセージ用のSlack webhook URL
        slack_webhook_url_warning: 警告メッセージ用のSlack webhook URL
        slack_webhook_url_info: 情報メッセージ用のSlack webhook URL
    """
    self.email_config = email_config
    self.slack_webhook_url = slack_webhook_url
    
    # 異なるアラートレベル用のSlack webhook URL
    self.slack_webhook_url_error = slack_webhook_url_error or slack_webhook_url
    self.slack_webhook_url_warning = slack_webhook_url_warning or slack_webhook_url
    self.slack_webhook_url_info = slack_webhook_url_info or slack_webhook_url
```

初期化時に、メール設定とSlack webhook URLを設定します。異なるアラートレベル（エラー、警告、情報）に対して異なるSlack webhook URLを設定することもできます。

### 3.2 メール送信

```python
def send_email(
    self,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    to_email: Optional[Union[str, List[str]]] = None
) -> bool:
    """
    メールアラートを送信します。
    
    引数:
        subject: メールの件名
        body: プレーンテキストのメール本文
        html_body: HTMLメール本文（オプション）
        to_email: 受信者メールアドレスを上書き
        
    戻り値:
        成功を示すブール値
    """
    if not self.email_config:
        logger.warning("⚠️ Email configuration not provided, skipping email alert")
        return False
    
    try:
        # メッセージの作成
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_config['from_email']
        
        # 受信者の決定
        recipients = to_email or self.email_config['to_email']
        if isinstance(recipients, list):
            msg['To'] = ', '.join(recipients)
            to_list = recipients
        else:
            msg['To'] = recipients
            to_list = [recipients]
        
        # パートの添付
        msg.attach(MIMEText(body, 'plain'))
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        # メールの送信
        server = smtplib.SMTP(
            self.email_config['smtp_server'],
            int(self.email_config['smtp_port'])
        )
        server.starttls()
        server.login(
            self.email_config['smtp_user'],
            self.email_config['smtp_password']
        )
        server.sendmail(
            self.email_config['from_email'],
            to_list,
            msg.as_string()
        )
        server.quit()
        
        logger.info(f"✅ Email alert sent: {subject}")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Error sending email alert: {e}")
        return False
```

このメソッドは、指定された件名と本文でメールを送信します。HTML形式のメール本文もサポートしています。メール設定が提供されていない場合や、エラーが発生した場合は`False`を返します。

### 3.3 Slack送信

```python
def send_slack(
    self,
    message: str,
    title: Optional[str] = None,
    color: str = "#36a64f",  # 緑
    fields: Optional[List[Dict[str, str]]] = None,
    webhook_url: Optional[str] = None
) -> bool:
    """
    Slackアラートを送信します。
    
    引数:
        message: メッセージテキスト
        title: メッセージタイトル（オプション）
        color: メッセージアタッチメントの色
        fields: メッセージに含める追加フィールド
        webhook_url: webhook URLの上書き
        
    戻り値:
        成功を示すブール値
    """
    webhook = webhook_url or self.slack_webhook_url
    
    if not webhook:
        logger.warning("⚠️ Slack webhook URL not provided, skipping Slack alert")
        return False
    
    try:
        # アタッチメントの作成
        attachment = {
            "color": color,
            "text": message,
            "mrkdwn_in": ["text", "fields"]
        }
        
        if title:
            attachment["title"] = title
            
        if fields:
            attachment["fields"] = fields
        
        # ペイロードの作成
        payload = {
            "attachments": [attachment]
        }
        
        # メッセージの送信
        response = requests.post(
            webhook,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Slack alert sent: {title or message[:30]}...")
            return True
        else:
            logger.error(f"❌ Error sending Slack alert: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        logger.exception(f"❌ Error sending Slack alert: {e}")
        return False
```

このメソッドは、指定されたメッセージとタイトルでSlackにメッセージを送信します。メッセージの色や追加フィールドをカスタマイズすることもできます。Slack webhook URLが提供されていない場合や、エラーが発生した場合は`False`を返します。

### 3.4 エラーアラートの送信

```python
def send_error_alert(
    self,
    error_message: str,
    error_details: Optional[str] = None,
    source: Optional[str] = None,
    send_email: bool = True,
    send_slack: bool = True,
    additional_fields: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    設定されたすべてのチャネルにエラーアラートを送信します。
    
    引数:
        error_message: 短いエラーメッセージ
        error_details: 詳細なエラー情報
        source: エラーのソース（例：スクリプト名）
        send_email: メールアラートを送信するかどうか
        send_slack: Slackアラートを送信するかどうか
        additional_fields: Slackメッセージに含める追加フィールド
        
    戻り値:
        少なくとも1つのアラートが正常に送信されたかどうかを示すブール値
    """
    source_info = f" in {source}" if source else ""
    subject = f"❌ ERROR{source_info}: {error_message}"
    
    # メッセージ本文の作成
    body = f"Error{source_info}:\n\n{error_message}"
    if error_details:
        body += f"\n\nDetails:\n{error_details}"
    
    # メール用のHTML本文の作成
    html_body = f"""
    <h2>Error{source_info}</h2>
    <p><strong>{error_message}</strong></p>
    """
    if error_details:
        html_body += f"<h3>Details:</h3><pre>{error_details}</pre>"
    
    # アラートの送信
    email_success = False
    slack_success = False
    
    if send_email and self.email_config:
        email_success = self.send_email(subject, body, html_body)
        
    if send_slack and self.slack_webhook_url_error:
        fields = []
        if source:
            fields.append({"title": "Source", "value": source, "short": True})
        if error_details:
            fields.append({"title": "Details", "value": f"```{error_details}```", "short": False})
        
        # 追加フィールドが提供されている場合は追加
        if additional_fields:
            fields.extend(additional_fields)
            
        slack_success = self.send_slack(
            message=error_message,
            title="❌ ERROR",
            color="#FF0000",  # 赤
            fields=fields,
            webhook_url=self.slack_webhook_url_error
        )
    
    return email_success or slack_success
```

このメソッドは、エラーアラートを設定されたすべてのチャネル（メールとSlack）に送信します。エラーメッセージ、詳細、ソースなどの情報を含めることができます。

### 3.5 成功アラートの送信

```python
def send_success_alert(
    self,
    message: str,
    details: Optional[str] = None,
    source: Optional[str] = None,
    send_email: bool = True,
    send_slack: bool = True,
    additional_fields: Optional[List[Dict[str, str]]] = None,
    stock_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    設定されたすべてのチャネルに成功アラートを送信します。
    
    引数:
        message: 成功メッセージ
        details: 追加の詳細
        source: 成功のソース（例：スクリプト名）
        send_email: メールアラートを送信するかどうか
        send_slack: Slackアラートを送信するかどうか
        additional_fields: Slackメッセージに含める追加フィールド
        stock_data: メッセージに含める株価データ（日次更新用）
        
    戻り値:
        少なくとも1つのアラートが正常に送信されたかどうかを示すブール値
    """
    source_info = f" in {source}" if source else ""
    subject = f"✅ SUCCESS{source_info}: {message}"
    
    # メッセージ本文の作成
    body = f"Success{source_info}:\n\n{message}"
    if details:
        body += f"\n\nDetails:\n{details}"
    
    # メール用のHTML本文の作成
    html_body = f"""
    <h2>Success{source_info}</h2>
    <p><strong>{message}</strong></p>
    """
    if details:
        html_body += f"<h3>Details:</h3><pre>{details}</pre>"
    
    # アラートの送信
    email_success = False
    slack_success = False
    
    if send_email and self.email_config:
        email_success = self.send_email(subject, body, html_body)
        
    if send_slack and self.slack_webhook_url_info:
        fields = []
        if source:
            fields.append({"title": "Source", "value": source, "short": True})
        
        # 株価データが提供されている場合は追加
        if stock_data:
            # 表示用に株価データをフォーマット
            if 'symbol' in stock_data:
                fields.append({"title": "Symbol", "value": stock_data['symbol'], "short": True})
            
            if 'latest_date' in stock_data:
                fields.append({"title": "Date", "value": stock_data['latest_date'], "short": True})
            
            # 価格情報が利用可能な場合は追加
            if 'data_points' in stock_data and stock_data['data_points'] > 0:
                price_info = "Latest price information available"
                fields.append({"title": "Data Points", "value": str(stock_data['data_points']), "short": True})
                
            # 日付範囲が利用可能な場合は追加
            if 'date_range' in stock_data:
                date_range = stock_data['date_range']
                range_text = f"From {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}"
                fields.append({"title": "Date Range", "value": range_text, "short": False})
        
        if details:
            fields.append({"title": "Details", "value": f"```{details}```", "short": False})
        
        # 追加フィールドが提供されている場合は追加
        if additional_fields:
            fields.extend(additional_fields)
            
        slack_success = self.send_slack(
            message=message,
            title="✅ SUCCESS",
            color="#36a64f",  # 緑
            fields=fields,
            webhook_url=self.slack_webhook_url_info
        )
    
    return email_success or slack_success
```

このメソッドは、成功アラートを設定されたすべてのチャネル（メールとSlack）に送信します。成功メッセージ、詳細、ソースなどの情報を含めることができます。また、株価データに関する情報も含めることができます。

### 3.6 警告アラートの送信

```python
def send_warning_alert(
    self,
    warning_message: str,
    warning_details: Optional[str] = None,
    source: Optional[str] = None,
    send_email: bool = True,
    send_slack: bool = True,
    additional_fields: Optional[List[Dict[str, str]]] = None,
    data_issues: Optional[Dict[str, Any]] = None
) -> bool:
    """
    設定されたすべてのチャネルに警告アラートを送信します。
    
    引数:
        warning_message: 警告メッセージ
        warning_details: 追加の詳細
        source: 警告のソース（例：スクリプト名）
        send_email: メールアラートを送信するかどうか
        send_slack: Slackアラートを送信するかどうか
        additional_fields: Slackメッセージに含める追加フィールド
        data_issues: メッセージに含めるデータの問題（データ警告用）
        
    戻り値:
        少なくとも1つのアラートが正常に送信されたかどうかを示すブール値
    """
    source_info = f" in {source}" if source else ""
    subject = f"⚠️ WARNING{source_info}: {warning_message}"
    
    # メッセージ本文の作成
    body = f"Warning{source_info}:\n\n{warning_message}"
    if warning_details:
        body += f"\n\nDetails:\n{warning_details}"
    
    # メール用のHTML本文の作成
    html_body = f"""
    <h2>Warning{source_info}</h2>
    <p><strong>{warning_message}</strong></p>
    """
    if warning_details:
        html_body += f"<h3>Details:</h3><pre>{warning_details}</pre>"
    
    # アラートの送信
    email_success = False
    slack_success = False
    
    if send_email and self.email_config:
        email_success = self.send_email(subject, body, html_body)
        
    if send_slack and self.slack_webhook_url_warning:
        fields = []
        if source:
            fields.append({"title": "Source", "value": source, "short": True})
        
        # データの問題が提供されている場合は追加
        if data_issues:
            # 表示用にデータの問題をフォーマット
            if 'symbol' in data_issues:
                fields.append({"title": "Symbol", "value": data_issues['symbol'], "short": True})
            
            if 'date' in data_issues:
                fields.append({"title": "Date", "value": data_issues['date'], "short": True})
            
            if 'issue_type' in data_issues:
                fields.append({"title": "Issue Type", "value": data_issues['issue_type'], "short": True})
            
            if 'affected_fields' in data_issues:
                affected_fields = data_issues['affected_fields']
                if isinstance(affected_fields, list):
                    affected_fields = ", ".join(affected_fields)
                fields.append({"title": "Affected Fields", "value": affected_fields, "short": True})
        
        if warning_details:
            fields.append({"title": "Details", "value": f"```{warning_details}```", "short": False})
        
        # 追加フィールドが提供されている場合は追加
        if additional_fields:
            fields.extend(additional_fields)
            
        slack_success = self.send_slack(
            message=warning_message,
            title="⚠️ WARNING",
            color="#FFA500",  # オレンジ
            fields=fields,
            webhook_url=self.slack_webhook_url_warning
        )
    
    return email_success or slack_success
```

このメソッドは、警告アラートを設定されたすべてのチャネル（メールとSlack）に送信します。警告メッセージ、詳細、ソースなどの情報を含めることができます。また、データの問題に関する情報も含めることができます。

## 4. 通知の種類

このモジュールでは、以下の3種類の通知をサポートしています：

1. **成功通知** (`send_success_alert`):
   - 処理が正常に完了した場合に送信されます。
   - 緑色（`#36a64f`）で表示されます。
   - 成功メッセージ、詳細、ソース、株価データなどの情報を含めることができます。

2. **警告通知** (`send_warning_alert`):
   - 潜在的な問題がある場合に送信されます。
   - オレンジ色（`#FFA500`）で表示されます。
   - 警告メッセージ、詳細、ソース、データの問題などの情報を含めることができます。

3. **エラー通知** (`send_error_alert`):
   - 重大な問題が発生した場合に送信されます。
   - 赤色（`#FF0000`）で表示されます。
   - エラーメッセージ、詳細、ソースなどの情報を含めることができます。

## 5. 通知チャネル

このモジュールでは、以下の2つの通知チャネルをサポートしています：

1. **メール**:
   - SMTPサーバーを使用してメールを送信します。
   - プレーンテキストとHTML形式の両方をサポートしています。
   - 複数の受信者にメールを送信することができます。

2. **Slack**:
   - Slack Incoming Webhookを使用してメッセージを送信します。
   - メッセージのタイトル、色、追加フィールドなどをカスタマイズできます。
   - 異なるアラートレベル（エラー、警告、情報）に対して異なるwebhook URLを設定できます。

## 6. 通知の使用例

### 6.1 基本的な使用例

```python
# アラートマネージャーの初期化
from src.utils.alerts import AlertManager

# メール設定
email_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': '587',
    'smtp_user': 'your-email@gmail.com',
    'smtp_password': 'your-app-password',
    'from_email': 'your-email@gmail.com',
    'to_email': 'recipient@example.com'
}

# Slack webhook URL
slack_webhook_url = 'https://hooks.slack.com/services/xxx/yyy/zzz'

# アラートマネージャーの作成
alert_manager = AlertManager(email_config, slack_webhook_url)

# 成功アラートの送信
alert_manager.send_success_alert(
    message="Data processing completed successfully",
    details="Processed 100 records in 5.2 seconds",
    source="process_data.py"
)

# 警告アラートの送信
alert_manager.send_warning_alert(
    warning_message="Some data points are missing",
    warning_details="10 out of 100 records have missing values",
    source="validate_data.py",
    data_issues={
        'symbol': 'AAPL',
        'date': '2023-01-01',
        'issue_type': 'Missing Values',
        'affected_fields': ['volume', 'close']
    }
)

# エラーアラートの送信
alert_manager.send_error_alert(
    error_message="Failed to connect to the database",
    error_details="Connection timeout after 30 seconds",
    source="db_connector.py"
)
```

### 6.2 スクリプト内での使用例

```python
from src.config import Config
from src.utils.alerts import AlertManager
import time

def main():
    # 設定の読み込み
    config = Config()
    
    # アラートマネージャーの初期化
    alert_manager = AlertManager(config.email_config, config.slack_webhook_url)
    
    # 実行開始時間
    start_time = time.time()
    
    try:
        # データ処理
        print("Processing data...")
        # ... データ処理のコード ...
        
        # 成功
        success = True
        processed_records = 100
        
    except Exception as e:
        # エラー
        print(f"Error: {e}")
        
        # エラーアラートの送信
        alert_manager.send_error_alert(
            error_message="Data processing failed",
            error_details=str(e),
            source="process_data.py"
        )
        
        success = False
        return 1
    
    # 実行時間の計算
    execution_time = time.time() - start_time
    
    # 成功アラートの送信
    if success:
        alert_manager.send_success_alert(
            message="Data processing completed successfully",
            details=f"Processed {processed_records} records in {execution_time:.2f} seconds",
            source="process_data.py"
        )
    
    return 0

if __name__ == "__main__":
    exit(main())
```

### 6.3 株価データ取得スクリプトでの使用例

```python
from src.config import Config
from src.utils.alerts import AlertManager
from src.api.alpha_vantage.client import AlphaVantageClient
from src.utils.data_processing import StockDataProcessor
from src.utils.storage import S3Storage
from src.utils.atomic_s3 import AtomicS3
import time

def main():
    # 設定の読み込み
    config = Config()
    
    # コンポーネントの初期化
    api_client = AlphaVantageClient(config.api_key)
    data_processor = StockDataProcessor()
    s3_storage = S3Storage(config.s3_bucket, config.s3_region)
    atomic_s3 = AtomicS3(s3_storage)
    alert_manager = AlertManager(config.email_config, config.slack_webhook_url)
    
    # 実行開始時間
    start_time = time.time()
    
    # 結果の追跡
    results = {}
    success_count = 0
    failure_count = 0
    
    # 各銘柄の処理
    for symbol in config.stock_symbols:
        try:
            # APIからデータを取得
            stock_data = api_client.fetch_daily_stock_data(symbol)
            
            if not stock_data:
                results[symbol] = "API_ERROR"
                failure_count += 1
                continue
            
            # データの検証と変換
            is_valid, df = data_processor.validate_and_transform(stock_data)
            
            if not is_valid or df is None:
                results[symbol] = "VALIDATION_ERROR"
                failure_count += 1
                continue
            
            # 最新データの抽出
            latest_df = data_processor.extract_latest_data(df)
            latest_date = latest_df.index[0].strftime('%Y-%m-%d')
            
            # JSONに変換
            json_data = data_processor.convert_to_json(df)
            latest_json_data = data_processor.convert_to_json(latest_df)
            
            # メタデータの追加
            json_data['symbol'] = symbol
            latest_json_data['symbol'] = symbol
            
            # S3に保存
            full_key = config.get_s3_key(symbol)
            latest_key = config.get_s3_key(symbol, is_latest=True)
            
            if not atomic_s3.atomic_json_update(latest_key, latest_json_data):
                results[symbol] = "STORAGE_ERROR"
                failure_count += 1
                continue
            
            if not atomic_s3.atomic_json_update(full_key, json_data):
                results[symbol] = "STORAGE_WARNING"
                # 最新データは保存できたので、警告として扱う
            
            # メタデータの更新
            metadata = {
                'symbol': symbol,
                'last_updated': time.time(),
                'latest_date': latest_date,
                'data_points': len(df),
                'date_range': {
                    'start': df.index[-1].strftime('%Y-%m-%d'),
                    'end': latest_date
                }
            }
            
            metadata_key = config.get_metadata_key(symbol)
            atomic_s3.atomic_json_update(metadata_key, metadata)
            
            # 成功
            results[symbol] = "SUCCESS"
            success_count += 1
            
        except Exception as e:
            # エラー
            results[symbol] = f"ERROR: {str(e)}"
            failure_count += 1
    
    # 実行時間の計算
    execution_time = time.time() - start_time
    
    # 結果の詳細
    details = f"""
Execution time: {execution_time:.2f} seconds
Successful: {success_count}
Failed: {failure_count}

Results by symbol:
{results}
"""
    
    # アラートの送信
    if failure_count > 0:
        # 一部失敗した場合は警告アラート
        alert_manager.send_warning_alert(
            warning_message=f"Stock data fetch completed with {failure_count} failures",
            warning_details=details,
            source="fetch_daily.py"
        )
    else:
        # すべて成功した場合は成功アラート
        alert_manager.send_success_alert(
            message="Stock data fetch completed successfully",
            details=details,
            source="fetch_daily.py"
        )
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    exit(main())
```

## 7. 通知の利点

適切な通知システムは、以下のような利点があります：

1. **即時性**: 問題が発生した場合、すぐに通知を受け取ることができます。
2. **可視性**: システムの状態や重要なイベントを可視化できます。
3. **トラブルシューティングの迅速化**: 問題の詳細情報を含めることで、トラブルシューティングを迅速化できます。
4. **監視の自動化**: 手動での監視が不要になります。
5. **ユーザー体験の向上**: エンドユーザーに重要な情報を提供できます。
6. **履歴の記録**: 通知の履歴を記録することで、過去の問題や成功を追跡できます。

## 8. 通知のベストプラクティス

1. **適切な通知レベルの使用**: 通知の重要度に応じて、適切な通知レベル（成功、警告、エラー）を使用します。

2. **通知の頻度の調整**: 通知が多すぎると「通知疲れ」を引き起こす可能性があります。重要なイベントのみを通知するようにします。

3. **コンテキスト情報の提供**: 通知には、問題の原因や解決策を理解するために必要なコンテキスト情報を含めます。

4. **アクション可能な通知**: 通知には、問題を解決するために必要なアクションを含めます。

5. **複数のチャネルの使用**: 重要な通知は、複数のチャネル（メール、Slackなど）で送信します。

6. **通知のフィルタリング**: 受信者が関心のある通知のみを受け取れるように、通知をフィルタリングします。

7. **通知の集約**: 関連する複数の問題を1つの通知にまとめることで、通知の数を減らします。

8. **通知の優先順位付け**: 通知に優先順位を付けることで、重要な問題に迅速に対応できるようにします。

## 9. 設計のポイント

1. **モジュール化**: 通知機能を独立したクラスにカプセル化しています。

2. **複数のチャネルのサポート**: メールとSlackの両方をサポートしています。

3. **異なる通知レベル**: 成功、警告、エラーの3つの通知レベルをサポートしています。

4. **カスタマイズ可能なメッセージ**: メッセージの内容、形式、追加フィールドなどをカスタマイズできます。

5. **エラーハンドリング**: 通知の送信に失敗した場合でも、アプリケーションの実行は継続します。

6. **条件付き通知**: 特定の条件を満たす場合のみ通知を送信できます。

7. **視覚的な区別**: 異なる通知レベルに異なる色やアイコンを使用することで、視覚的に区別しやすくしています。

## 10. 練習問題

1. `AlertManager`クラスに、新しい通知チャネル（例：Microsoft Teams、Discord）を追加してみましょう。

2. `AlertManager`クラスに、通知の送信履歴を記録する機能を追加してみましょう。

3. `AlertManager`クラスに、通知の送信条件（例：特定の時間帯のみ、特定の条件を満たす場合のみ）を設定する機能を追加してみましょう。

4. 通知メッセージに、グラフや画像を含める機能を追加してみましょう。

## 11. 参考資料

- [SMTP Protocol](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol): SMTPプロトコルに関するWikipediaの記事
- [Slack API Documentation](https://api.slack.com/): Slack APIの公式ドキュメント
- [Email MIME Format](https://en.wikipedia.org/wiki/MIME): メールのMIME形式に関するWikipediaの記事
- [Notification Design Patterns](https://www.nngroup.com/articles/notification-design/): 通知のデザインパターンに関する記事
