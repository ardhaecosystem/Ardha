"""
Email service for sending notification emails.

This module provides email functionality including:
- SMTP client integration with aiosmtplib
- Jinja2 template rendering for HTML emails
- Email validation and configuration
- Support for single notifications and daily/weekly digests
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from ardha.core.config import get_settings
from ardha.models.notification import Notification
from ardha.models.user import User

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails via SMTP.

    Handles email composition, template rendering with Jinja2,
    and SMTP delivery using aiosmtplib. Supports both single
    notification emails and aggregated digest emails.

    Attributes:
        settings: Application settings with email configuration
        jinja_env: Jinja2 environment for template rendering
    """

    def __init__(self) -> None:
        """Initialize EmailService with settings and Jinja2 environment."""
        self.settings = get_settings()

        # Get template directory path
        template_dir = Path(__file__).parent.parent / "templates" / "email"

        # Initialize Jinja2 environment for email templates
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.info(f"EmailService initialized with template directory: {template_dir}")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text fallback (optional, generated from HTML if not provided)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Validate email configuration
            if not self._is_configured():
                logger.warning("Email not configured, skipping email send")
                return False

            # Create multipart message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.settings.email.from_name} <{self.settings.email.from_email}>"
            message["To"] = to_email

            # Add plain text part (fallback)
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            else:
                # Generate simple text version from HTML
                text_part = MIMEText(self._html_to_text(html_content), "plain")
                message.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send via SMTP
            await aiosmtplib.send(
                message,
                hostname=self.settings.email.smtp_host,
                port=self.settings.email.smtp_port,
                username=self.settings.email.smtp_username,
                password=self.settings.email.smtp_password,
                use_tls=self.settings.email.use_tls,
            )

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            return False

    async def send_notification_email(self, user: User, notification: Notification) -> bool:
        """
        Send notification as email using template.

        Args:
            user: User to send email to
            notification: Notification to send

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Render email template
            html_content = self.render_template(
                "notification_single.html",
                {
                    "user_name": user.full_name or user.username,
                    "notification": {
                        "title": notification.title,
                        "message": notification.message,
                        "type": notification.type,
                        "link_type": notification.link_type,
                        "link_id": str(notification.link_id) if notification.link_id else None,
                        "created_at": notification.created_at.isoformat(),
                    },
                    "app_url": self._get_app_url(),
                },
            )

            # Create subject from notification title
            subject = f"Ardha: {notification.title}"

            return await self.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
            )

        except Exception as e:
            logger.error(f"Error sending notification email to {user.email}: {e}")
            return False

    async def send_daily_digest(self, user: User, notifications: List[Notification]) -> bool:
        """
        Send daily digest email with all unread notifications.

        Args:
            user: User to send digest to
            notifications: List of notifications for digest

        Returns:
            True if email sent successfully, False otherwise
        """
        if not notifications:
            logger.debug(f"No notifications for daily digest for user {user.id}")
            return False

        try:
            # Render digest template
            html_content = self.render_template(
                "notification_digest.html",
                {
                    "user_name": user.full_name or user.username,
                    "digest_type": "Daily",
                    "notification_count": len(notifications),
                    "notifications": [
                        {
                            "title": notif.title,
                            "message": notif.message,
                            "type": notif.type,
                            "link_type": notif.link_type,
                            "link_id": str(notif.link_id) if notif.link_id else None,
                            "created_at": notif.created_at.isoformat(),
                        }
                        for notif in notifications
                    ],
                    "app_url": self._get_app_url(),
                },
            )

            subject = f"Ardha Daily Digest: {len(notifications)} notifications"

            return await self.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
            )

        except Exception as e:
            logger.error(f"Error sending daily digest to {user.email}: {e}")
            return False

    async def send_weekly_digest(self, user: User, notifications: List[Notification]) -> bool:
        """
        Send weekly digest email with all unread notifications.

        Args:
            user: User to send digest to
            notifications: List of notifications for digest

        Returns:
            True if email sent successfully, False otherwise
        """
        if not notifications:
            logger.debug(f"No notifications for weekly digest for user {user.id}")
            return False

        try:
            # Render digest template
            html_content = self.render_template(
                "notification_digest.html",
                {
                    "user_name": user.full_name or user.username,
                    "digest_type": "Weekly",
                    "notification_count": len(notifications),
                    "notifications": [
                        {
                            "title": notif.title,
                            "message": notif.message,
                            "type": notif.type,
                            "link_type": notif.link_type,
                            "link_id": str(notif.link_id) if notif.link_id else None,
                            "created_at": notif.created_at.isoformat(),
                        }
                        for notif in notifications
                    ],
                    "app_url": self._get_app_url(),
                },
            )

            subject = f"Ardha Weekly Digest: {len(notifications)} notifications"

            return await self.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
            )

        except Exception as e:
            logger.error(f"Error sending weekly digest to {user.email}: {e}")
            return False

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context.

        Args:
            template_name: Name of template file (e.g., "notification_single.html")
            context: Dictionary of template variables

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)

        except TemplateNotFound:
            logger.error(f"Email template not found: {template_name}")
            raise

        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise

    def validate_email_config(self) -> bool:
        """
        Validate SMTP configuration on startup.

        Returns:
            True if configuration is valid and complete
        """
        required_fields = [
            self.settings.email.smtp_host,
            self.settings.email.smtp_username,
            self.settings.email.smtp_password,
            self.settings.email.from_email,
        ]

        is_valid = all(field for field in required_fields)

        if is_valid:
            logger.info("Email configuration validated successfully")
        else:
            logger.warning("Email configuration incomplete - email sending disabled")

        return is_valid

    def _is_configured(self) -> bool:
        """
        Check if email is configured.

        Returns:
            True if SMTP credentials are configured
        """
        return bool(self.settings.email.smtp_username and self.settings.email.smtp_password)

    def _get_app_url(self) -> str:
        """
        Get application URL for email links.

        Returns:
            Application URL (defaults to localhost for development)
        """
        # TODO: Make configurable via settings
        if self.settings.is_production:
            return "https://app.ardha.dev"
        return "http://localhost:3000"

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text for email fallback.

        Args:
            html: HTML content

        Returns:
            Plain text version (simple implementation)
        """
        # Simple HTML stripping (for better results, use html2text library)
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text
