from email.message import EmailMessage
import smtplib
import ssl

from app.core.config import settings


class EmailService:
    @staticmethod
    def _get_sender_email() -> str | None:
        return settings.smtp_from_email or settings.smtp_username

    @staticmethod
    def _get_smtp_host() -> str | None:
        if settings.smtp_host:
            return settings.smtp_host

        sender_email = EmailService._get_sender_email()
        if sender_email and sender_email.lower().endswith("@gmail.com"):
            return "smtp.gmail.com"

        return None

    @staticmethod
    def _build_message(
        to_email: str,
        reset_url: str,
        reset_token: str | None = None,
    ) -> EmailMessage:
        sender_email = EmailService._get_sender_email()
        if not sender_email:
            raise RuntimeError(
                "SMTP no configurado. Define SMTP_FROM_EMAIL o SMTP_USERNAME para enviar correos."
            )

        token_text = (
            "\n\nSi el botón o el enlace no se abren, copia este token en la pantalla de "
            f"recuperación de contraseña:\n{reset_token}\n"
            if reset_token
            else ""
        )
        token_html = (
            "<p>Si el botón o el enlace no se abren, copia este token en la pantalla de "
            f"recuperación de contraseña:</p><pre style=\"white-space: pre-wrap; word-break: break-all;\">{reset_token}</pre>"
            if reset_token
            else ""
        )

        message = EmailMessage()
        message["Subject"] = "Recupera tu contraseña de LIA"
        message["From"] = f"{settings.smtp_from_name} <{sender_email}>"
        message["To"] = to_email
        message.set_content(
            "Hola,\n\n"
            "Hemos recibido una solicitud para restablecer tu contraseña de LIA.\n\n"
            "Pulsa o copia este enlace para crear una contraseña nueva:\n"
            f"{reset_url}"
            f"{token_text}\n"
            "Este enlace caduca en 30 minutos. Si no has solicitado este cambio, puedes ignorar este correo.\n"
        )
        message.add_alternative(
            f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #20243A; line-height: 1.5;">
                <p>Hola,</p>
                <p>Hemos recibido una solicitud para restablecer tu contraseña de LIA.</p>
                <p>
                  <a href="{reset_url}"
                     style="display: inline-block; padding: 12px 18px; border-radius: 10px; background: #7F83F5; color: #ffffff; text-decoration: none; font-weight: bold;">
                    Crear nueva contraseña
                  </a>
                </p>
                <p>Si el botón no aparece o Gmail no lo abre, copia y pega este enlace completo:</p>
                <p style="word-break: break-all; background: #F4F6FD; border: 1px solid #DCE3F7; border-radius: 10px; padding: 12px;">
                  {reset_url}
                </p>
                {token_html}
                <p>Este enlace caduca en 30 minutos. Si no has solicitado este cambio, puedes ignorar este correo.</p>
              </body>
            </html>
            """,
            subtype="html",
        )
        return message

    @staticmethod
    def send_password_reset_email(
        to_email: str,
        reset_url: str,
        reset_token: str | None = None,
    ) -> None:
        smtp_host = EmailService._get_smtp_host()
        sender_email = EmailService._get_sender_email()

        if not smtp_host or not sender_email:
            raise RuntimeError(
                "SMTP no configurado. Para Gmail define SMTP_USERNAME, SMTP_PASSWORD y SMTP_FROM_EMAIL "
                "(o SMTP_HOST=smtp.gmail.com)."
            )

        if smtp_host == "smtp.gmail.com" and not settings.smtp_password:
            raise RuntimeError(
                "Gmail requiere SMTP_PASSWORD con una contraseña de aplicación. "
                "Activa la verificación en dos pasos en Gmail y crea una App Password."
            )

        message = EmailService._build_message(to_email, reset_url, reset_token)

        try:
            if settings.smtp_port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host, settings.smtp_port, context=context) as smtp:
                    if settings.smtp_username and settings.smtp_password:
                        smtp.login(settings.smtp_username, settings.smtp_password)
                    smtp.send_message(message)
                return

            with smtplib.SMTP(smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.ehlo()
                if settings.smtp_use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(
                "No se pudo autenticar con SMTP. Si usas Gmail, usa una contraseña de aplicación, "
                "no tu contraseña normal."
            ) from exc
        except smtplib.SMTPException as exc:
            raise RuntimeError(f"Error SMTP al enviar el correo: {str(exc)}") from exc
        except OSError as exc:
            raise RuntimeError(f"No se pudo conectar con el servidor SMTP: {str(exc)}") from exc

    @staticmethod
    def send_temporary_password_email(
        to_email: str,
        temporary_password: str,
    ) -> None:
        smtp_host = EmailService._get_smtp_host()
        sender_email = EmailService._get_sender_email()

        if not smtp_host or not sender_email:
            raise RuntimeError(
                "SMTP no configurado. Para Gmail define SMTP_USERNAME, SMTP_PASSWORD y SMTP_FROM_EMAIL "
                "(o SMTP_HOST=smtp.gmail.com)."
            )

        message = EmailMessage()
        message["Subject"] = "Tu nueva contraseña temporal de LIA"
        message["From"] = f"{settings.smtp_from_name} <{sender_email}>"
        message["To"] = to_email
        message.set_content(
            "Hola,\n\n"
            "Hemos recibido una solicitud para recuperar tu contraseña de LIA.\n"
            "Hemos generado una contraseña temporal para que puedas iniciar sesión:\n\n"
            f"{temporary_password}\n\n"
            "Te recomendamos iniciar sesión y cambiarla inmediatamente desde tu perfil.\n"
            "Si no has solicitado este cambio, contacta con soporte.\n"
        )

        try:
            if settings.smtp_port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host, settings.smtp_port, context=context) as smtp:
                    if settings.smtp_username and settings.smtp_password:
                        smtp.login(settings.smtp_username, settings.smtp_password)
                    smtp.send_message(message)
                return

            with smtplib.SMTP(smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.ehlo()
                if settings.smtp_use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(
                "No se pudo autenticar con SMTP. Si usas Gmail, usa una contraseña de aplicación, "
                "no tu contraseña normal."
            ) from exc
        except smtplib.SMTPException as exc:
            raise RuntimeError(f"Error SMTP al enviar el correo: {str(exc)}") from exc
        except OSError as exc:
            raise RuntimeError(f"No se pudo conectar con el servidor SMTP: {str(exc)}") from exc