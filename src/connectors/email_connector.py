from imap_tools import (
    MailBox,
    MailMessage,
    MailMessageFlags,
)

from src.config import settings


# Gmail buscará solamente mensajes no leídos enviados
# directamente por alguno de estos portales. No se busca
# por asunto para evitar capturar correos ajenos que solo
# mencionen el nombre de una web inmobiliaria.
PORTAL_EMAIL_CRITERIA = (
    'X-GM-RAW "is:unread '
    '{from:idealista '
    'from:fotocasa '
    'from:habitaclia '
    'from:pisos.com '
    'from:milanuncios}"'
)


def connect_to_mailbox() -> MailBox:
    if not settings.imap_user:
        raise ValueError(
            "Falta IMAP_USER en el archivo .env"
        )

    if not settings.imap_password:
        raise ValueError(
            "Falta IMAP_PASSWORD en el archivo .env"
        )

    mailbox = MailBox(
        settings.imap_host,
        port=settings.imap_port,
    )

    mailbox.login(
        settings.imap_user,
        settings.imap_password,
        initial_folder="INBOX",
    )

    return mailbox


def close_mailbox(
    mailbox: MailBox,
) -> None:
    try:
        mailbox.logout()

    except Exception:
        # Gmail puede devolver una respuesta extraña
        # al cerrar una conexión que funcionó correctamente.
        pass


def fetch_unread_emails(
    limit: int = 50,
) -> list[MailMessage]:
    mailbox = connect_to_mailbox()

    try:
        emails = list(
            mailbox.fetch(
                PORTAL_EMAIL_CRITERIA,
                mark_seen=False,
                reverse=True,
                limit=limit,
            )
        )

        return [
            email
            for email in emails
            if is_portal_alert_email(email)
        ]

    finally:
        close_mailbox(mailbox)

def mark_emails_as_read(
    email_uids: set[str] | list[str],
) -> int:
    unique_uids = list({
        uid
        for uid in email_uids
        if uid
    })

    if not unique_uids:
        return 0

    mailbox = connect_to_mailbox()

    try:
        mailbox.flag(
            unique_uids,
            MailMessageFlags.SEEN,
            True,
        )

        return len(unique_uids)

    finally:
        close_mailbox(mailbox)


IGNORED_SUBJECT_KEYWORDS = (
    "bienvenido",
    "bienvenida",
    "welcome",
    "confirma tu email",
    "verifica tu cuenta",
    "activar alertas",
    "activa tus alertas",
    "contraseña",
    "password",
    "cuenta",
)


def is_portal_alert_email(
    email,
) -> bool:
    subject = (
        email.subject or ""
    ).strip().casefold()

    return not any(
        keyword in subject
        for keyword in IGNORED_SUBJECT_KEYWORDS
    )