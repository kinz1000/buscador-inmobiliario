import re
from src.config import settings
from bs4 import BeautifulSoup
from imap_tools import MailMessage


FOTOCASA_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?fotocasa\.es/"
    r"es/comprar/vivienda/"
    r"[^\s\"'<>]+/\d+/d/?",
    re.IGNORECASE,
)


# Correos de Fotocasa que NO son alertas de inmuebles.
FOTOCASA_IGNORED_SENDERS = {
    "novedades.fotocasa@novedades.fotocasa.es",
}


def is_fotocasa_email(
    email: MailMessage,
) -> bool:
    sender = (email.from_ or "").casefold()
    subject = (email.subject or "").casefold()

    if (
        "fotocasa" not in sender
        and "fotocasa" not in subject
    ):
        return False

    # Solo nos interesan correos relacionados
    # con alguna de las zonas configuradas.
    return any(
        zone.casefold() in subject
        for zone in settings.zone_list
    )

def extract_fotocasa_links(
    email: MailMessage,
) -> list[str]:
    links: set[str] = set()

    if email.html:
        soup = BeautifulSoup(
            email.html,
            "html.parser",
        )

        for element in soup.find_all(
            "a",
            href=True,
        ):
            match = FOTOCASA_URL_PATTERN.search(
                element["href"]
            )

            if match:
                links.add(
                    match.group(0)
                )

    if email.text:
        links.update(
            FOTOCASA_URL_PATTERN.findall(
                email.text
            )
        )

    return sorted(links)


def extract_fotocasa_id(
    url: str,
) -> str | None:
    match = re.search(
        r"/(\d+)/d/?(?:[?#]|$)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)