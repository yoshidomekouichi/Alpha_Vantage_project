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
        slack_webhook_url: Optional[str] = None
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
            slack_webhook_url: Slack webhook URL for sending messages
        """
        self.email_config = email_config
        self.slack_webhook_url = slack_webhook_url
        
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
        
        try:
            # Create attachment
            attachment = {
                "color": color,
                "text": message,
                "mrkdwn_in": ["text", "fields"]
            }
            
            if title:
                attachment["title"] = title
                
            if fields:
                attachment["fields"] = fields
            
            # Create payload
            payload = {
                "attachments": [attachment]
            }
            
            # Send message
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
    
    def send_error_alert(
        self,
        error_message: str,
        error_details: Optional[str] = None,
        source: Optional[str] = None,
        send_email: bool = True,
        send_slack: bool = True
    ) -> bool:
        """
        Send an error alert to all configured channels.
        
        Args:
            error_message: Short error message
            error_details: Detailed error information
            source: Source of the error (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            
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
            
        if send_slack and self.slack_webhook_url:
            fields = []
            if source:
                fields.append({"title": "Source", "value": source, "short": True})
            if error_details:
                fields.append({"title": "Details", "value": f"```{error_details}```", "short": False})
                
            slack_success = self.send_slack(
                message=error_message,
                title="❌ ERROR",
                color="#FF0000",  # Red
                fields=fields
            )
        
        return email_success or slack_success
    
    def send_success_alert(
        self,
        message: str,
        details: Optional[str] = None,
        source: Optional[str] = None,
        send_email: bool = True,
        send_slack: bool = True
    ) -> bool:
        """
        Send a success alert to all configured channels.
        
        Args:
            message: Success message
            details: Additional details
            source: Source of the success (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            
        Returns:
            Boolean indicating if at least one alert was sent successfully
        """
        source_info = f" in {source}" if source else ""
        subject = f"✅ SUCCESS{source_info}: {message}"
        
        # Create message body
        body = f"Success{source_info}:\n\n{message}"
        if details:
            body += f"\n\nDetails:\n{details}"
        
        # Create HTML body for email
        html_body = f"""
        <h2>Success{source_info}</h2>
        <p><strong>{message}</strong></p>
        """
        if details:
            html_body += f"<h3>Details:</h3><pre>{details}</pre>"
        
        # Send alerts
        email_success = False
        slack_success = False
        
        if send_email and self.email_config:
            email_success = self.send_email(subject, body, html_body)
            
        if send_slack and self.slack_webhook_url:
            fields = []
            if source:
                fields.append({"title": "Source", "value": source, "short": True})
            if details:
                fields.append({"title": "Details", "value": f"```{details}```", "short": False})
                
            slack_success = self.send_slack(
                message=message,
                title="✅ SUCCESS",
                color="#36a64f",  # Green
                fields=fields
            )
        
        return email_success or slack_success
    
    def send_warning_alert(
        self,
        warning_message: str,
        warning_details: Optional[str] = None,
        source: Optional[str] = None,
        send_email: bool = True,
        send_slack: bool = True
    ) -> bool:
        """
        Send a warning alert to all configured channels.
        
        Args:
            warning_message: Warning message
            warning_details: Additional details
            source: Source of the warning (e.g., script name)
            send_email: Whether to send an email alert
            send_slack: Whether to send a Slack alert
            
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
            
        if send_slack and self.slack_webhook_url:
            fields = []
            if source:
                fields.append({"title": "Source", "value": source, "short": True})
            if warning_details:
                fields.append({"title": "Details", "value": f"```{warning_details}```", "short": False})
                
            slack_success = self.send_slack(
                message=warning_message,
                title="⚠️ WARNING",
                color="#FFA500",  # Orange
                fields=fields
            )
        
        return email_success or slack_success
