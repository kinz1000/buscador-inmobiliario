import re

from bs4 import BeautifulSoup
from imap_tools import MailMessage


FOTOCASA_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?fotocasa\.es/"
    r"es/comprar/vivienda/"
    r"[^\s\"'<>]+/\d+/d/?",
    re.IGNORECASE,
)


def is_fotocasa_email(email: MailMessage) -> bool:
    sender = (email.from_ or "").casefold()
    subject = (email.subject or "").casefold()

    return "fotocasa" in sender or "fotocasa" in subject


def extract_fotocasa_links(
    email: MailMessage,
) -> list[str]:
    links: set[str] = set()

    if email.html:
        soup = BeautifulSoup(email.html, "html.parser")

        for element in soup.find_all("a", href=True):
            match = FOTOCASA_URL_PATTERN.search(
                element["href"]
            )

            if match:
                links.add(match.group(0))

    if email.text:
        links.update(
            FOTOCASA_URL_PATTERN.findall(email.text)
        )

    return sorted(links)


def extract_fotocasa_id(url: str) -> str | None:
    match = re.search(
        r"/(\d+)/d/?(?:[?#]|$)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)