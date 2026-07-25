from unittest.mock import MagicMock

import pytest
import smtplib

from app.services.email_service import EmailService
import app.services.email_service as email_module


def configure(monkeypatch, **overrides):
    values = {
        "smtp_from_email": "lia@example.com",
        "smtp_username": "lia@example.com",
        "smtp_password": "app-password",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_from_name": "LIA",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setattr(email_module.settings, key, value)


def smtp_context():
    smtp = MagicMock()
    manager = MagicMock()
    manager.__enter__.return_value = smtp
    manager.__exit__.return_value = False
    return manager, smtp


def test_sender_prefiere_from_email(monkeypatch):
    configure(monkeypatch, smtp_from_email="from@example.com", smtp_username="user@example.com")
    assert EmailService._get_sender_email() == "from@example.com"


def test_sender_usa_username_como_fallback(monkeypatch):
    configure(monkeypatch, smtp_from_email=None, smtp_username="user@example.com")
    assert EmailService._get_sender_email() == "user@example.com"


def test_host_explicito(monkeypatch):
    configure(monkeypatch, smtp_host="smtp.custom.test")
    assert EmailService._get_smtp_host() == "smtp.custom.test"


def test_host_gmail_inferido(monkeypatch):
    configure(monkeypatch, smtp_host=None, smtp_from_email="lia@gmail.com")
    assert EmailService._get_smtp_host() == "smtp.gmail.com"


def test_host_no_inferible_devuelve_none(monkeypatch):
    configure(monkeypatch, smtp_host=None, smtp_from_email="lia@example.com")
    assert EmailService._get_smtp_host() is None


def test_build_message_texto_y_html(monkeypatch):
    configure(monkeypatch)
    msg = EmailService._build_message(
        "destino@example.com",
        "https://lia/reset",
        "TOKEN123",
    )
    assert msg["To"] == "destino@example.com"
    assert "LIA" in msg["Subject"]
    assert "TOKEN123" in msg.get_body(preferencelist=("plain",)).get_content()
    assert "https://lia/reset" in msg.get_body(preferencelist=("html",)).get_content()


def test_build_message_sin_sender_falla(monkeypatch):
    configure(monkeypatch, smtp_from_email=None, smtp_username=None)
    with pytest.raises(RuntimeError, match="SMTP no configurado"):
        EmailService._build_message("a@b.com", "https://reset")


def test_password_reset_smtp_tls(monkeypatch):
    configure(monkeypatch, smtp_port=587, smtp_use_tls=True)
    manager, smtp = smtp_context()
    monkeypatch.setattr(email_module.smtplib, "SMTP", MagicMock(return_value=manager))

    EmailService.send_password_reset_email("a@b.com", "https://reset", "TOKEN")

    smtp.ehlo.assert_called()
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("lia@example.com", "app-password")
    smtp.send_message.assert_called_once()


def test_password_reset_smtp_ssl(monkeypatch):
    configure(monkeypatch, smtp_port=465)
    manager, smtp = smtp_context()
    monkeypatch.setattr(email_module.smtplib, "SMTP_SSL", MagicMock(return_value=manager))
    monkeypatch.setattr(email_module.ssl, "create_default_context", MagicMock(return_value="CTX"))

    EmailService.send_password_reset_email("a@b.com", "https://reset")

    smtp.login.assert_called_once()
    smtp.send_message.assert_called_once()


def test_password_reset_gmail_sin_password_falla(monkeypatch):
    configure(
        monkeypatch,
        smtp_host="smtp.gmail.com",
        smtp_password=None,
    )
    with pytest.raises(RuntimeError, match="contraseña de aplicación"):
        EmailService.send_password_reset_email("a@b.com", "https://reset")


def test_temporary_password_email(monkeypatch):
    configure(monkeypatch, smtp_port=587, smtp_use_tls=False)
    manager, smtp = smtp_context()
    monkeypatch.setattr(email_module.smtplib, "SMTP", MagicMock(return_value=manager))

    EmailService.send_temporary_password_email("a@b.com", "Temp1234")

    sent = smtp.send_message.call_args.args[0]
    assert "Temp1234" in sent.get_content()
    smtp.starttls.assert_not_called()


@pytest.mark.parametrize(
    ("exc", "fragment"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad"), "autenticar"),
        (smtplib.SMTPException("smtp roto"), "Error SMTP"),
        (OSError("sin red"), "conectar"),
    ],
)
def test_temporary_password_traduce_errores(monkeypatch, exc, fragment):
    configure(monkeypatch)
    manager, smtp = smtp_context()
    smtp.send_message.side_effect = exc
    monkeypatch.setattr(email_module.smtplib, "SMTP", MagicMock(return_value=manager))

    with pytest.raises(RuntimeError, match=fragment):
        EmailService.send_temporary_password_email("a@b.com", "Temp1234")
