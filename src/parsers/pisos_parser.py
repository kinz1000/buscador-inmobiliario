import re

from bs4 import BeautifulSoup
from imap_tools import MailMessage


PISOS_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?pisos\.com/"
    r"(?:"
    r"comprar/[^\s\"'<>?]+-\d+_\d+"
    r"|"
    r"promocion-[^\s\"'<>?]+-\d+_\d+"
    r")/?",
    re.IGNORECASE,
)


def is_pisos_email(
    email: MailMessage,
) -> bool:
    sender = (email.from_ or "").casefold()
    subject = (email.subject or "").casefold()

    return (
        "pisos.com" in sender
        or "pisos.com" in subject
    )


def extract_pisos_links(
    email: MailMessage,
) -> list[str]:
    links: set[str] = set()

    if email.html:
        soup = BeautifulSoup(email.html, "html.parser")

        for element in soup.find_all("a", href=True):
            match = PISOS_URL_PATTERN.search(
                element["href"]
            )

            if match:
                links.add(match.group(0))

    if email.text:
        links.update(
            PISOS_URL_PATTERN.findall(email.text)
        )

    return sorted(links)


def extract_pisos_id(
    url: str,
) -> str | None:
    match = re.search(
        r"-(\d+_\d+)/?(?:[?#]|$)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)
