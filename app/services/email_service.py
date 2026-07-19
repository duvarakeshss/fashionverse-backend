import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anyio

from app.config import settings

logger = logging.getLogger("fashionverse.email")

class EmailService:
    """Service to handle sending emails asynchronously via SMTP."""

    @staticmethod
    async def send_verification_email(to_email: str, name: str, code: str) -> None:
        """Sends a verification email containing a 6-digit verification code."""
        subject = "FashionVerse — Verify Your Email Address"
        body_text = f"Hi {name},\n\nThank you for registering at FashionVerse! Your 6-digit verification code is: {code}\n\nThis code will expire in 15 minutes.\n\nBest regards,\nThe FashionVerse Team"
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4A90E2;">Welcome to FashionVerse, {name}!</h2>
                <p>Thank you for signing up. Please verify your email address to log in.</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; font-size: 20px; font-weight: bold; text-align: center; margin: 20px 0; letter-spacing: 2px;">
                    {code}
                </div>
                <p>This code will expire in 15 minutes. If you did not request this, please ignore this email.</p>
                <br/>
                <p>Best regards,<br/><strong>The FashionVerse Team</strong></p>
            </body>
        </html>
        """

        # Fallback to local console logger if SMTP credentials are not set
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info("=========================================")
            logger.info("SMTP CREDENTIALS NOT CONFIGURED. LOGGING EMAIL:")
            logger.info(f"To: {to_email}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Verification Code: {code}")
            logger.info("=========================================")
            return

        def _sync_send():
            # Setup MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email

            msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))

            # Connect and send
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()  # Upgrade connection to secure encrypted TLS
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())

        try:
            # Offload blocking SMTP operations to worker threads
            await anyio.to_thread.run_sync(_sync_send)
            logger.info(f"Verification email successfully sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            # Re-raise error to let the API client know that email transmission failed
            raise Exception("Failed to send verification email. Please try again later.")
