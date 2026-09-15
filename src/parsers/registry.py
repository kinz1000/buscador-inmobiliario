from collections.abc import Callable
from dataclasses import dataclass

from imap_tools import MailMessage

from src.parsers.fotocasa_parser import (
    extract_fotocasa_id,
    extract_fotocasa_links,
    is_fotocasa_email,
)
from src.parsers.habitaclia_parser import (
    extract_habitaclia_id,
    extract_habitaclia_links,
    is_habitaclia_email,
)
from src.parsers.idealista_parser import (
    extract_idealista_id,
    extract_idealista_links,
    is_idealista_email,
)
from src.parsers.milanuncios_parser import (
    extract_milanuncios_id,
    extract_milanuncios_links,
    is_milanuncios_email,
)
from src.parsers.pisos_parser import (
    extract_pisos_id,
    extract_pisos_links,
    is_pisos_email,
)


@dataclass(frozen=True)
class PortalParser:
    portal: str

    is_email: Callable[
        [MailMessage],
        bool,
    ]

    extract_links: Callable[
        [MailMessage],
        list[str],
    ]

    extract_id: Callable[
        [str],
        str | None,
    ]


PORTAL_PARSERS = [
    PortalParser(
        portal="Idealista",
        is_email=is_idealista_email,
        extract_links=extract_idealista_links,
        extract_id=extract_idealista_id,
    ),
    PortalParser(
        portal="Fotocasa",
        is_email=is_fotocasa_email,
        extract_links=extract_fotocasa_links,
        extract_id=extract_fotocasa_id,
    ),
    PortalParser(
        portal="Habitaclia",
        is_email=is_habitaclia_email,
        extract_links=extract_habitaclia_links,
        extract_id=extract_habitaclia_id,
    ),
    PortalParser(
        portal="Pisos.com",
        is_email=is_pisos_email,
        extract_links=extract_pisos_links,
        extract_id=extract_pisos_id,
    ),
    PortalParser(
        portal="Milanuncios",
        is_email=is_milanuncios_email,
        extract_links=extract_milanuncios_links,
        extract_id=extract_milanuncios_id,
    ),
]


def get_portal_parser(
    email: MailMessage,
) -> PortalParser | None:
    for parser in PORTAL_PARSERS:
        if parser.is_email(email):
            return parser

    return None