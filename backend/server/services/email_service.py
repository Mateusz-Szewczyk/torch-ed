"""
TorchED Email Service - Resend API Integration
Modern, Apple-style transactional emails.
"""
import os
import logging
from typing import Optional

import resend

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service using Resend API with beautiful, inline-styled templates.
    """

    # Brand colors
    PRIMARY_COLOR = "#4f46e5"
    PRIMARY_GRADIENT_END = "#7c3aed"
    TEXT_COLOR = "#1a1a1a"
    MUTED_TEXT = "#64748b"
    BACKGROUND = "#f8fafc"
    CARD_BACKGROUND = "#ffffff"
    WARNING_BG = "#fef3c7"
    WARNING_BORDER = "#f59e0b"
    WARNING_TEXT = "#92400e"

    def __init__(self):
        api_key = os.environ.get("RESEND_API_KEY")
        if not api_key:
            raise ValueError(
                "RESEND_API_KEY environment variable is required. "
                "Please set it in your .env file or Railway variables."
            )
        resend.api_key = api_key
        self.from_email = os.environ.get("RESEND_FROM_EMAIL", "TorchED <noreply@torched.pl>")
        logger.info("EmailService initialized with Resend API")

    def _base_template(self, header_title: str, header_subtitle: str, content_html: str) -> str:
        """
        Generate the base HTML email template with Apple-esque design.
        All CSS is inline for maximum email client compatibility.
        """
        return f"""
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{header_title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background-color: {self.BACKGROUND}; color: {self.TEXT_COLOR}; -webkit-font-smoothing: antialiased;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {self.BACKGROUND};">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <!-- Main Container -->
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: {self.CARD_BACKGROUND}; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {self.PRIMARY_COLOR} 0%, {self.PRIMARY_GRADIENT_END} 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0 0 8px 0; font-size: 28px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">{header_title}</h1>
                            <p style="margin: 0; font-size: 16px; color: rgba(255, 255, 255, 0.85);">{header_subtitle}</p>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {content_html}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: {self.BACKGROUND}; padding: 24px 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 13px; color: {self.MUTED_TEXT};">
                                © 2025 TorchED. Wiadomość wysłana automatycznie.
                            </p>
                            <p style="margin: 8px 0 0 0; font-size: 12px; color: {self.MUTED_TEXT};">
                                <a href="https://torched.pl" style="color: {self.PRIMARY_COLOR}; text-decoration: none;">torched.pl</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def _cta_button(self, text: str, url: str) -> str:
        """Generate a centered Call-to-Action button."""
        return f"""
<div style="text-align: center; margin: 32px 0;">
    <a href="{url}" style="display: inline-block; padding: 16px 32px; background-color: {self.PRIMARY_COLOR}; color: #ffffff !important; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 16px; letter-spacing: -0.2px; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);">
        {text}
    </a>
</div>
<p style="margin: 24px 0 0 0; font-size: 13px; color: {self.MUTED_TEXT}; text-align: center;">
    Jeśli przycisk nie działa, skopiuj ten link:<br>
    <a href="{url}" style="color: {self.PRIMARY_COLOR}; word-break: break-all;">{url}</a>
</p>
"""

    def _warning_box(self, content_html: str) -> str:
        """Generate a warning/info box."""
        return f"""
<div style="background-color: {self.WARNING_BG}; border: 1px solid {self.WARNING_BORDER}; border-radius: 8px; padding: 16px; margin: 24px 0; color: {self.WARNING_TEXT};">
    {content_html}
</div>
"""

    def send_confirmation_email(self, to: str, user_name: str, confirmation_link: str) -> bool:
        """Send account confirmation email."""
        content = f"""
<p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6;">Cześć <strong>{user_name}</strong>!</p>
<p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: {self.MUTED_TEXT};">
    Dziękujemy za rejestrację w TorchED. Aby aktywować swoje konto, kliknij przycisk poniżej:
</p>
{self._cta_button("✨ Potwierdź konto", confirmation_link)}
"""
        html = self._base_template(
            header_title="🎉 Witaj w TorchED!",
            header_subtitle="Potwierdź swoje konto",
            content_html=content
        )
        return self._send(to, "Potwierdź rejestrację w TorchED", html)

    def send_password_reset_email(self, to: str, reset_link: str) -> bool:
        """Send password reset email."""
        warning_content = """
<strong>⚠️ Ważne:</strong>
<ul style="margin: 8px 0 0 16px; padding: 0;">
    <li>Link jest ważny przez <strong>30 minut</strong></li>
    <li>Jeśli nie prosiłeś o reset, zignoruj tę wiadomość</li>
    <li>Nie udostępniaj tego linku nikomu</li>
</ul>
"""
        content = f"""
<p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6;">Cześć!</p>
<p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: {self.MUTED_TEXT};">
    Otrzymaliśmy prośbę o zresetowanie hasła do Twojego konta w TorchED.
</p>
{self._cta_button("🔑 Zresetuj hasło", reset_link)}
{self._warning_box(warning_content)}
"""
        html = self._base_template(
            header_title="🔒 Resetowanie hasła",
            header_subtitle="TorchED - Bezpieczne resetowanie",
            content_html=content
        )
        return self._send(to, "🔒 Resetowanie hasła - TorchED", html)

    def send_transactional(
        self,
        to: str,
        subject: str,
        content_body: str,
        action_text: Optional[str] = None,
        action_link: Optional[str] = None
    ) -> bool:
        """
        Generic transactional email sender.
        Injects content into the base template.
        """
        content = f'<p style="margin: 0; font-size: 16px; line-height: 1.6;">{content_body}</p>'
        if action_text and action_link:
            content += self._cta_button(action_text, action_link)

        html = self._base_template(
            header_title="TorchED",
            header_subtitle="Powiadomienie",
            content_html=content
        )
        return self._send(to, subject, html)

    def _send(self, to: str, subject: str, html: str) -> bool:
        """
        Internal method to send email via Resend API.
        Returns True on success, False on failure (logs error without crashing).
        """
        try:
            params: resend.Emails.SendParams = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            response = resend.Emails.send(params)
            logger.info(f"Email sent successfully to {to}. ID: {response.get('id', 'N/A')}")
            return True
        except resend.exceptions.ResendError as e:
            logger.error(f"Resend API error sending to {to}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to}: {e}")
            return False


# Singleton instance for easy import
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the EmailService singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
