import re

from bs4 import BeautifulSoup
from imap_tools import MailMessage


HABITACLIA_PUBLIC_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?habitaclia\.com/"
    r"comprar-[^\s\"'<>?]+-i\d+\.htm",
    re.IGNORECASE,
)

# Los correos de alertas no enlazan directamente a la
# URL pública. Utilizan una URL de seguimiento cuyo primer
# segmento contiene el identificador del inmueble.
# Solo aceptamos la sección "nuevo" para no mezclar
# oportunidades y anuncios destacados con las novedades.
HABITACLIA_ALERT_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?habitaclia\.com/"
    r"i\d+/[^\s\"'<>?#]*nuevo[^\s\"'<>?#]*\.htm",
    re.IGNORECASE,
)


def _find_habitaclia_urls(
    content: str,
) -> list[str]:
    urls = [
        match.group(0)
        for pattern in (
            HABITACLIA_PUBLIC_URL_PATTERN,
            HABITACLIA_ALERT_URL_PATTERN,
        )
        for match in pattern.finditer(content)
    ]

    return urls


def _prefer_title_link(
    current_url: str,
    candidate_url: str,
) -> str:
    if (
        "_titulo.htm" in candidate_url.casefold()
        and "_titulo.htm" not in current_url.casefold()
    ):
        return candidate_url

    return current_url


def is_habitaclia_email(
    email: MailMessage,
) -> bool:
    sender = (email.from_ or "").casefold()
    subject = (email.subject or "").casefold()

    return (
        "habitaclia" in sender
        or "habitaclia" in subject
    )


def extract_habitaclia_links(
    email: MailMessage,
) -> list[str]:
    links_by_id: dict[str, str] = {}

    def add_urls(content: str) -> None:
        for url in _find_habitaclia_urls(content):
            external_id = extract_habitaclia_id(
                url
            )

            if not external_id:
                continue

            current_url = links_by_id.get(
                external_id
            )

            if current_url is None:
                links_by_id[external_id] = url
                continue

            links_by_id[external_id] = (
                _prefer_title_link(
                    current_url,
                    url,
                )
            )

    if email.html:
        soup = BeautifulSoup(email.html, "html.parser")

        for element in soup.find_all("a", href=True):
            add_urls(element["href"])

    if email.text:
        add_urls(email.text)

    return sorted(links_by_id.values())


def extract_habitaclia_id(
    url: str,
) -> str | None:
    match = re.search(
        r"(?:-i|/i)(\d+)(?:\.htm|/)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)
