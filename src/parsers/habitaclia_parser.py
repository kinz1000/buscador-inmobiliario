import re
from src.config import settings
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

    if (
        "habitaclia" not in sender
        and "habitaclia" not in subject
    ):
        return False

    return any(
        zone.casefold() in subject
        for zone in settings.zone_list
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
def extract_habitaclia_advertiser_from_email(
    email: MailMessage,
    external_id: str,
) -> str | None:

    if not email.html:
        return None

    soup = BeautifulSoup(email.html, "html.parser")

    for card in soup.select("table.tableTexto"):

        links = card.find_all("a", href=True)

        if not any(
            extract_habitaclia_id(link["href"]) == external_id
            for link in links
        ):
            continue

        paragraphs = card.find_all("p")

        for paragraph in paragraphs:
            description = paragraph.get_text(
                " ", strip=True
            )

            patterns = [
                r"^(.+?)\s+presenta\s+en\s+exclusiva\b",
                r"^(.+?)\s+ofrece\s+en\s+exclusiva\b",
                r"^(.+?)\s+pone\s+a\s+la\s+venta\b",
            ]

            for pattern in patterns:
                match = re.search(
                    pattern,
                    description,
                    re.IGNORECASE,
                )

                if match:
                    return match.group(1).strip(" ,:-")

    return None