import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "support@adet.app")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@adet.app")
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@adet.app")

        self.enabled = bool(self.smtp_username and self.smtp_password)

    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send an email"""
        if not self.enabled:
            logger.warning("Email service not configured. Skipping email send.")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add plain text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_support_request_notification(self, user_email: str, request_id: int, category: str, subject: str) -> bool:
        """Send notification for new support request"""
        subject_line = f"Support Request #{request_id} Received"

        body = f"""
Thank you for contacting Adet Support!

We have received your support request and will get back to you as soon as possible.

Request Details:
- Request ID: #{request_id}
- Category: {category}
- Subject: {subject}
- Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

We typically respond within 24 hours. If you need immediate assistance, please contact us through our alternative channels:
- Telegram: https://t.me/adet_support
- Email: {self.support_email}

Best regards,
The Adet Support Team
        """.strip()

        html_body = f"""
<html>
<body>
    <h2>Support Request Received</h2>
    <p>Thank you for contacting Adet Support!</p>
    <p>We have received your support request and will get back to you as soon as possible.</p>

    <h3>Request Details:</h3>
    <ul>
        <li><strong>Request ID:</strong> #{request_id}</li>
        <li><strong>Category:</strong> {category}</li>
        <li><strong>Subject:</strong> {subject}</li>
        <li><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
    </ul>

    <p>We typically respond within 24 hours. If you need immediate assistance, please contact us through our alternative channels:</p>
    <ul>
        <li><strong>Telegram:</strong> <a href="https://t.me/adet_support">https://t.me/adet_support</a></li>
        <li><strong>Email:</strong> <a href="mailto:{self.support_email}">{self.support_email}</a></li>
    </ul>

    <p>Best regards,<br>The Adet Support Team</p>
</body>
</html>
        """

        return self.send_email(user_email, subject_line, body, html_body)

    def send_bug_report_notification(self, user_email: str, report_id: int, category: str, severity: str, title: str) -> bool:
        """Send notification for new bug report"""
        subject_line = f"Bug Report #{report_id} Received"

        body = f"""
Thank you for reporting this bug to Adet!

We have received your bug report and our development team will investigate it.

Bug Report Details:
- Report ID: #{report_id}
- Category: {category}
- Severity: {severity}
- Title: {title}
- Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

We will keep you updated on the progress. For critical bugs, we aim to respond within 4 hours.

Alternative contact methods:
- GitHub Issues: https://github.com/adet-app/issues
- Email: {self.support_email}

Best regards,
The Adet Development Team
        """.strip()

        html_body = f"""
<html>
<body>
    <h2>Bug Report Received</h2>
    <p>Thank you for reporting this bug to Adet!</p>
    <p>We have received your bug report and our development team will investigate it.</p>

    <h3>Bug Report Details:</h3>
    <ul>
        <li><strong>Report ID:</strong> #{report_id}</li>
        <li><strong>Category:</strong> {category}</li>
        <li><strong>Severity:</strong> {severity}</li>
        <li><strong>Title:</strong> {title}</li>
        <li><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
    </ul>

    <p>We will keep you updated on the progress. For critical bugs, we aim to respond within 4 hours.</p>

    <p>Alternative contact methods:</p>
    <ul>
        <li><strong>GitHub Issues:</strong> <a href="https://github.com/adet-app/issues">https://github.com/adet-app/issues</a></li>
        <li><strong>Email:</strong> <a href="mailto:{self.support_email}">{self.support_email}</a></li>
    </ul>

    <p>Best regards,<br>The Adet Development Team</p>
</body>
</html>
        """

        return self.send_email(user_email, subject_line, body, html_body)

    def send_admin_notification(self, request_type: str, request_id: int, user_email: str, category: str, subject: str, severity: Optional[str] = None) -> bool:
        """Send notification to admin about new support request/bug report"""
        if request_type == "support":
            subject_line = f"New Support Request #{request_id}"
            body = f"""
New support request received:

Request ID: #{request_id}
User Email: {user_email}
Category: {category}
Subject: {subject}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review and respond as soon as possible.
            """.strip()
        else:  # bug report
            subject_line = f"New Bug Report #{request_id}"
            body = f"""
New bug report received:

Report ID: #{request_id}
User Email: {user_email}
Category: {category}
Severity: {severity}
Title: {subject}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review and prioritize accordingly.
            """.strip()

        return self.send_email(self.admin_email, subject_line, body)

    def send_status_update_notification(self, user_email: str, request_type: str, request_id: int, status: str, message: str) -> bool:
        """Send notification about status update"""
        subject_line = f"Update on your {request_type} #{request_id}"

        body = f"""
Your {request_type} has been updated:

{request_type.title()} ID: #{request_id}
New Status: {status}
Update: {message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Thank you for your patience.

Best regards,
The Adet Support Team
        """.strip()

        return self.send_email(user_email, subject_line, body)


# Global email service instance
email_service = EmailService()
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "support@adet.app")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@adet.app")
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@adet.app")

        self.enabled = bool(self.smtp_username and self.smtp_password)

    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send an email"""
        if not self.enabled:
            logger.warning("Email service not configured. Skipping email send.")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add plain text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_support_request_notification(self, user_email: str, request_id: int, category: str, subject: str) -> bool:
        """Send notification for new support request"""
        subject_line = f"Support Request #{request_id} Received"

        body = f"""
Thank you for contacting Adet Support!

We have received your support request and will get back to you as soon as possible.

Request Details:
- Request ID: #{request_id}
- Category: {category}
- Subject: {subject}
- Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

We typically respond within 24 hours. If you need immediate assistance, please contact us through our alternative channels:
- Telegram: https://t.me/adet_support
- Email: {self.support_email}

Best regards,
The Adet Support Team
        """.strip()

        html_body = f"""
<html>
<body>
    <h2>Support Request Received</h2>
    <p>Thank you for contacting Adet Support!</p>
    <p>We have received your support request and will get back to you as soon as possible.</p>

    <h3>Request Details:</h3>
    <ul>
        <li><strong>Request ID:</strong> #{request_id}</li>
        <li><strong>Category:</strong> {category}</li>
        <li><strong>Subject:</strong> {subject}</li>
        <li><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
    </ul>

    <p>We typically respond within 24 hours. If you need immediate assistance, please contact us through our alternative channels:</p>
    <ul>
        <li><strong>Telegram:</strong> <a href="https://t.me/adet_support">https://t.me/adet_support</a></li>
        <li><strong>Email:</strong> <a href="mailto:{self.support_email}">{self.support_email}</a></li>
    </ul>

    <p>Best regards,<br>The Adet Support Team</p>
</body>
</html>
        """

        return self.send_email(user_email, subject_line, body, html_body)

    def send_bug_report_notification(self, user_email: str, report_id: int, category: str, severity: str, title: str) -> bool:
        """Send notification for new bug report"""
        subject_line = f"Bug Report #{report_id} Received"

        body = f"""
Thank you for reporting this bug to Adet!

We have received your bug report and our development team will investigate it.

Bug Report Details:
- Report ID: #{report_id}
- Category: {category}
- Severity: {severity}
- Title: {title}
- Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

We will keep you updated on the progress. For critical bugs, we aim to respond within 4 hours.

Alternative contact methods:
- GitHub Issues: https://github.com/adet-app/issues
- Email: {self.support_email}

Best regards,
The Adet Development Team
        """.strip()

        html_body = f"""
<html>
<body>
    <h2>Bug Report Received</h2>
    <p>Thank you for reporting this bug to Adet!</p>
    <p>We have received your bug report and our development team will investigate it.</p>

    <h3>Bug Report Details:</h3>
    <ul>
        <li><strong>Report ID:</strong> #{report_id}</li>
        <li><strong>Category:</strong> {category}</li>
        <li><strong>Severity:</strong> {severity}</li>
        <li><strong>Title:</strong> {title}</li>
        <li><strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
    </ul>

    <p>We will keep you updated on the progress. For critical bugs, we aim to respond within 4 hours.</p>

    <p>Alternative contact methods:</p>
    <ul>
        <li><strong>GitHub Issues:</strong> <a href="https://github.com/adet-app/issues">https://github.com/adet-app/issues</a></li>
        <li><strong>Email:</strong> <a href="mailto:{self.support_email}">{self.support_email}</a></li>
    </ul>

    <p>Best regards,<br>The Adet Development Team</p>
</body>
</html>
        """

        return self.send_email(user_email, subject_line, body, html_body)

    def send_admin_notification(self, request_type: str, request_id: int, user_email: str, category: str, subject: str, severity: Optional[str] = None) -> bool:
        """Send notification to admin about new support request/bug report"""
        if request_type == "support":
            subject_line = f"New Support Request #{request_id}"
            body = f"""
New support request received:

Request ID: #{request_id}
User Email: {user_email}
Category: {category}
Subject: {subject}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review and respond as soon as possible.
            """.strip()
        else:  # bug report
            subject_line = f"New Bug Report #{request_id}"
            body = f"""
New bug report received:

Report ID: #{request_id}
User Email: {user_email}
Category: {category}
Severity: {severity}
Title: {subject}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review and prioritize accordingly.
            """.strip()

        return self.send_email(self.admin_email, subject_line, body)

    def send_status_update_notification(self, user_email: str, request_type: str, request_id: int, status: str, message: str) -> bool:
        """Send notification about status update"""
        subject_line = f"Update on your {request_type} #{request_id}"

        body = f"""
Your {request_type} has been updated:

{request_type.title()} ID: #{request_id}
New Status: {status}
Update: {message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Thank you for your patience.

Best regards,
The Adet Support Team
        """.strip()

        return self.send_email(user_email, subject_line, body)


# Global email service instance
email_service = EmailService()

