import re

from bs4 import BeautifulSoup
from imap_tools import MailMessage


IDEALISTA_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?idealista\.com/inmueble/\d+/?",
    re.IGNORECASE,
)


def is_idealista_email(
    email: MailMessage,
) -> bool:
    sender = (
        email.from_
        or ""
    ).casefold()

    subject = (
        email.subject
        or ""
    ).casefold()

    return (
        "idealista" in sender
        or "idealista" in subject
    )


def extract_idealista_links(
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
            match = IDEALISTA_URL_PATTERN.search(
                element["href"]
            )

            if match:
                links.add(
                    match.group(0)
                )

    if email.text:
        links.update(
            IDEALISTA_URL_PATTERN.findall(
                email.text
            )
        )

    return sorted(links)


def extract_idealista_id(
    url: str,
) -> str | None:
    match = re.search(
        r"/inmueble/(\d+)/?",
        url,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)