"""
Alerts Module

This module provides functionality for sending alerts via email and Slack.
It is used to notify about errors, warnings, and important events.
"""

import os
import logging
import json
import smtplib
import requests
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List, Union

# Default logger - will be replaced by the configured logger
logger = logging.getLogger(__name__)

class AlertManager:
    """Manages sending alerts via different channels."""
    
    def __init__(
        self,
        email_config: Optional[Dict[str, str]] = None,
        slack_webhook_url: Optional[str] = None,
        slack_webhook_url_error: Optional[str] = None,
        slack_webhook_url_warning: Optional[str] = None,
        slack_webhook_url_info: Optional[str] = None
    ):
        """
        Initialize the alert manager.
        
        Args:
            email_config: Email configuration dictionary with keys:
                - smtp_server: SMTP server address
                - smtp_port: SMTP server port
                - smtp_user: SMTP username
                - smtp_password: SMTP password
                - from_email: Sender email address
                - to_email: Recipient email address(es) (string or list)
            slack_webhook_url: Default Slack webhook URL for sending messages
            slack_webhook_url_error: Slack webhook URL for error messages
            slack_webhook_url_warning: Slack webhook URL for warning messages
            slack_webhook_url_info: Slack webhook URL for info messages
        """
        self.email_config = email_config
        self.slack_webhook_url = slack_webhook_url
        
        # Slack webhook URLs for different alert levels
        self.slack_webhook_url_error = slack_webhook_url_error or slack_webhook_url
        self.slack_webhook_url_warning = slack_webhook_url_warning or slack_webhook_url
        self.slack_webhook_url_info = slack_webhook_url_info or slack_webhook_url
        
    def set_logger(self, custom_logger):
        """Set a custom logger for the alert manager."""
        global logger
        logger = custom_logger
    
    def send_email(
        self,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        to_email: Optional[Union[str, List[str]]] = None
    ) -> bool:
        """
        Send an email alert.
        
        Args:
            subject: Email subject
            body: Plain text email body
            html_body: HTML email body (optional)
            to_email: Override recipient email address(es)
            
        Returns:
            Boolean indicating success
        """
        if not self.email_config:
            logger.warning("⚠️ Email configuration not provided, skipping email alert")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config['from_email']
            
            # Determine recipients
            recipients = to_email or self.email_config['to_email']
            if isinstance(recipients, list):
                msg['To'] = ', '.join(recipients)
                to_list = recipients
            else:
                msg['To'] = recipients
                to_list = [recipients]
            
            # Attach parts
            msg.attach(MIMEText(body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
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
    
    def send_slack(
        self,
        message: str,
        title: Optional[str] = None,
        color: str = "#36a64f",  # Green
        fields: Optional[List[Dict[str, str]]] = None,
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        Send a Slack alert.
        
        Args:
            message: Message text
            title: Message title (optional)
            color: Color for the message attachment
            fields: Additional fields to include in the message
            webhook_url: Override webhook URL
            
        Returns:
            Boolean indicating success
        """
        webhook = webhook_url or self.slack_webhook_url
        
        if not webhook:
            logger.warning("⚠️ Slack webhook URL not provided, skipping Slack alert")
            return False
        
        # URLの形式を確認
        if not webhook.startswith('https://hooks.slack.com/'):
            logger.error(f"❌ Invalid Slack webhook URL format: {webhook}")
            return False
        
        try:
            # Slack APIの最新仕様に合わせたペイロードを作成
            payload = {"text": title or message}
            blocks = []
            
            # タイトルがある場合はヘッダーブロックを追加
            if title:
                blocks.append({
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                })
            
            # メッセージ本文を追加
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            })
            
            # フィールドがある場合は追加
            if fields and len(fields) > 0:
                for field in fields:
                    blocks.append({
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*{field['title']}*\n{field['value']}"
                            }
                        ]
                    })
            
            # 区切り線を追加
            blocks.append({"type": "divider"})
            
            # ペイロードにブロックを設定
            payload["blocks"] = blocks
            
            # Slack APIにリクエストを送信
            response = requests.post(
                webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Slack alert sent: {title or message[:30]}...")
                return True
            else:
                logger.error(f"❌ Error sending Slack alert: {response.status_code} {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout error when sending Slack alert")
            return False
        except requests.exceptions.ConnectionError as conn_error:
            logger.error(f"❌ Connection error when sending Slack alert: {conn_error}")
            return False
        except Exception as e:
            logger.exception(f"❌ Error sending Slack alert: {e}")
            return False
            
    def test_slack_connection(self, webhook_url: Optional[str] = None) -> bool:
        """
        Test the Slack connection by sending a simple test message.
        
        Args:
            webhook_url: Override webhook URL
            
        Returns:
            Boolean indicating success
        """
        test_message = "🔍 This is a test message from AlertManager"
        return self.send_slack(
            message=test_message,
            title="Slack Connection Test",
            webhook_url=webhook_url
        )
    
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
        Send an error alert to all configured channels.
        
        Args:
            error_message: Short error message
            error_details: Detailed error information
            source: Source of the error (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            additional_fields: Additional fields to include in the Slack message
            
        Returns:
            Boolean indicating if at least one alert was sent successfully
        """
        source_info = f" in {source}" if source else ""
        subject = f"❌ ERROR{source_info}: {error_message}"
        
        # Create message body
        body = f"Error{source_info}:\n\n{error_message}"
        if error_details:
            body += f"\n\nDetails:\n{error_details}"
        
        # Create HTML body for email
        html_body = f"""
        <h2>Error{source_info}</h2>
        <p><strong>{error_message}</strong></p>
        """
        if error_details:
            html_body += f"<h3>Details:</h3><pre>{error_details}</pre>"
        
        # Send alerts
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
            
            # Add additional fields if provided
            if additional_fields:
                fields.extend(additional_fields)
                
            slack_success = self.send_slack(
                message=error_message,
                title="❌ ERROR",
                color="#FF0000",  # Red
                fields=fields,
                webhook_url=self.slack_webhook_url_error
            )
        
        return email_success or slack_success
    
    def send_success_alert(
        self,
        success_message: str,
        success_details: Optional[str] = None,
        source: Optional[str] = None,
        send_email: bool = True,
        send_slack: bool = True,
        additional_fields: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Send a success alert to all configured channels.
        
        Args:
            success_message: Short success message
            success_details: Detailed success information
            source: Source of the success (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            additional_fields: Additional fields to include in the Slack message
            
        Returns:
            Boolean indicating if at least one alert was sent successfully
        """
        source_info = f" in {source}" if source else ""
        subject = f"✅ SUCCESS{source_info}: {success_message}"
        
        # Create message body
        body = f"Success{source_info}:\n\n{success_message}"
        if success_details:
            body += f"\n\nDetails:\n{success_details}"
        
        # Create HTML body for email
        html_body = f"""
        <h2>Success{source_info}</h2>
        <p><strong>{success_message}</strong></p>
        """
        if success_details:
            html_body += f"<h3>Details:</h3><pre>{success_details}</pre>"
        
        # Send alerts
        email_success = False
        slack_success = False
        
        if send_email and self.email_config:
            email_success = self.send_email(subject, body, html_body)
            
        if send_slack and self.slack_webhook_url_info:
            fields = []
            if source:
                fields.append({"title": "Source", "value": source, "short": True})
            if success_details:
                fields.append({"title": "Details", "value": f"```{success_details}```", "short": False})
            
            # Add additional fields if provided
            if additional_fields:
                fields.extend(additional_fields)
                
            slack_success = self.send_slack(
                message=success_message,
                title=subject,
                color="#36a64f",  # Green
                fields=fields,
                webhook_url=self.slack_webhook_url_info
            )
        
        return email_success or slack_success
    
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
        Send a warning alert to all configured channels.
        
        Args:
            warning_message: Warning message
            warning_details: Additional details
            source: Source of the warning (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            additional_fields: Additional fields to include in the Slack message
            data_issues: Data issues to include in the message (for data warnings)
            
        Returns:
            Boolean indicating if at least one alert was sent successfully
        """
        source_info = f" in {source}" if source else ""
        subject = f"⚠️ WARNING{source_info}: {warning_message}"
        
        # Create message body
        body = f"Warning{source_info}:\n\n{warning_message}"
        if warning_details:
            body += f"\n\nDetails:\n{warning_details}"
        
        # Create HTML body for email
        html_body = f"""
        <h2>Warning{source_info}</h2>
        <p><strong>{warning_message}</strong></p>
        """
        if warning_details:
            html_body += f"<h3>Details:</h3><pre>{warning_details}</pre>"
        
        # Send alerts
        email_success = False
        slack_success = False
        
        if send_email and self.email_config:
            email_success = self.send_email(subject, body, html_body)
            
        if send_slack and self.slack_webhook_url_warning:
            fields = []
            if source:
                fields.append({"title": "Source", "value": source, "short": True})
            
            # Add data issues if provided
            if data_issues:
                # Format data issues for display
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
            
            # Add additional fields if provided
            if additional_fields:
                fields.extend(additional_fields)
                
            slack_success = self.send_slack(
                message=warning_message,
                title="⚠️ WARNING",
                color="#FFA500",  # Orange
                fields=fields,
                webhook_url=self.slack_webhook_url_warning
            )
        
        return email_success or slack_success
    
    def send_info_alert(
        self,
        info_message: str,
        info_details: Optional[str] = None,
        source: Optional[str] = None,
        send_email: bool = True,
        send_slack: bool = True,
        additional_fields: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Send an informational alert to all configured channels.
        
        Args:
            info_message: Short informational message
            info_details: Detailed information
            source: Source of the information (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            additional_fields: Additional fields to include in the Slack message
            
        Returns:
            Boolean indicating if at least one alert was sent successfully
        """
        source_info = f" from {source}" if source else ""
        subject = f"ℹ️ INFO{source_info}: {info_message}"
        
        # Create message body
        body = f"Information{source_info}:\n\n{info_message}"
        if info_details:
            body += f"\n\nDetails:\n{info_details}"
        
        # Create HTML body for email
        html_body = f"""
        <h2>Information{source_info}</h2>
        <p><strong>{info_message}</strong></p>
        """
        if info_details:
            html_body += f"<h3>Details:</h3><pre>{info_details}</pre>"
        
        # Send alerts
        email_success = False
        slack_success = False
        
        if send_email and self.email_config:
            email_success = self.send_email(subject, body, html_body)
            
        if send_slack and self.slack_webhook_url_info:
            fields = []
            if source:
                fields.append({"title": "Source", "value": source, "short": True})
            if info_details:
                fields.append({"title": "Details", "value": f"```{info_details}```", "short": False})
            
            # Add additional fields if provided
            if additional_fields:
                fields.extend(additional_fields)
                
            slack_success = self.send_slack(
                message=info_message,
                title=subject,
                color="#3AA3E3",  # Blue
                fields=fields,
                webhook_url=self.slack_webhook_url_info
            )
        
        return email_success or slack_success
