import re

import requests
from bs4 import BeautifulSoup
from imap_tools import MailMessage


MILANUNCIOS_TRACKING_HOST = (
    "sgt.milanuncios.com/ls/click"
)

MILANUNCIOS_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?milanuncios\.com/"
    r"ads/[^?\s\"'<>]+-(\d+)\.htm",
    re.IGNORECASE,
)


def is_milanuncios_email(
    email: MailMessage,
) -> bool:
    sender = (email.from_ or "").casefold()
    subject = (email.subject or "").casefold()

    return (
        "milanuncios" in sender
        or "milanuncios" in subject
    )


def resolve_milanuncios_url(
    url: str,
) -> str | None:
    """
    Convierte una URL de tracking de Milanuncios
    en la URL real del anuncio.

    Aunque la ficha final pueda responder 403,
    requests conserva correctamente response.url
    después de las redirecciones.
    """

    if not url:
        return None

    # Ya es una URL directa.
    if MILANUNCIOS_URL_PATTERN.search(url):
        return url.split("?", 1)[0]

    if MILANUNCIOS_TRACKING_HOST not in url:
        return None

    try:
        response = requests.get(
            url,
            timeout=15,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/152.0.0.0 "
                    "Safari/537.36"
                ),
                "Accept-Language": (
                    "es-ES,es;q=0.9,en;q=0.8"
                ),
            },
        )

        final_url = response.url

        if not MILANUNCIOS_URL_PATTERN.search(
            final_url
        ):
            return None

        # Eliminamos UTM y otros parámetros.
        return final_url.split("?", 1)[0]

    except requests.RequestException:
        return None


def extract_milanuncios_id(
    url: str,
) -> str | None:
    if not url:
        return None

    match = re.search(
        r"-(\d+)\.htm(?:[?#]|$)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)


def _extract_price(
    text: str,
) -> float | None:
    """
    Convierte:
        730.000 €
        3.290.077 €
        220.000 €

    en:
        730000
        3290077
        220000
    """

    if not text:
        return None

    match = re.search(
        r"(\d{1,3}(?:\.\d{3})+|\d{4,8})"
        r"(?:,\d{1,2})?\s*€",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    number = (
        match.group(1)
        .replace(".", "")
        .replace(" ", "")
    )

    try:
        return float(number)
    except ValueError:
        return None


def _find_listing_card(
    button_table,
):
    """
    Parte desde el botón 'Ver anuncio' y sube
    por las tablas hasta encontrar la tarjeta
    que contiene su precio.

    De esta forma no mezclamos los datos de
    diferentes anuncios.
    """

    for table in button_table.find_parents(
        "table"
    ):
        price_element = table.select_one(
            "p.euros"
        )

        if price_element is not None:
            return table

    return None


def extract_milanuncios_cards(
    email: MailMessage,
) -> dict[str, dict]:
    """
    Devuelve los anuncios del correo indexados
    por su URL real.

    Ejemplo:

    {
        "https://www.milanuncios.com/ads/..."
        : {
            "price": 730000,
            "location": "Madrid Capital",
            "image_url": "...",
        }
    }
    """

    if not email.html:
        return {}

    soup = BeautifulSoup(
        email.html,
        "html.parser",
    )

    listings: dict[str, dict] = {}

    # En el correo real de Milanuncios existe
    # exactamente un tableButtonBusqueda por
    # tarjeta/anuncio.
    buttons = soup.select(
        "table.tableButtonBusqueda"
    )

    for button_table in buttons:
        link_element = button_table.find(
            "a",
            href=True,
        )

        if link_element is None:
            continue

        tracking_url = link_element.get(
            "href"
        )

        if (
            not tracking_url
            or MILANUNCIOS_TRACKING_HOST
            not in tracking_url
        ):
            continue

        listing_card = _find_listing_card(
            button_table
        )

        if listing_card is None:
            continue

        # -----------------------------------------
        # PRECIO
        # -----------------------------------------
        price = None

        price_element = listing_card.select_one(
            "p.euros"
        )

        if price_element is not None:
            price = _extract_price(
                price_element.get_text(
                    " ",
                    strip=True,
                )
            )

        # -----------------------------------------
        # UBICACIÓN
        # -----------------------------------------
        location = None

        # El correo real coloca textos del estilo:
        #
        # Madrid Capital
        # 730.000 €
        # Madrid
        #
        # Queremos el primero.
        paragraphs = listing_card.find_all("p")

        for paragraph in paragraphs:
            text = paragraph.get_text(
                " ",
                strip=True,
            )

            if not text:
                continue

            # Ignorar precio.
            if "€" in text:
                continue

            normalized = text.casefold()

            if (
                "madrid capital" in normalized
                or normalized == "madrid"
            ):
                location = text

                # Preferimos Madrid Capital
                # antes que Madrid.
                if (
                    "madrid capital"
                    in normalized
                ):
                    break

        # -----------------------------------------
        # IMAGEN
        # -----------------------------------------
        image_url = None

        image = listing_card.find(
            "img",
            src=re.compile(
                r"images-re\.milanuncios\.com",
                re.IGNORECASE,
            ),
        )

        if image is not None:
            image_url = image.get("src")

        # -----------------------------------------
        # URL REAL
        # -----------------------------------------
        final_url = resolve_milanuncios_url(
            tracking_url
        )

        if not final_url:
            continue

        external_id = extract_milanuncios_id(
            final_url
        )

        if not external_id:
            continue

        listings[final_url] = {
            "external_id": external_id,
            "price": price,
            "location": location,
            "image_url": image_url,
            "tracking_url": tracking_url,
        }

    return listings


def extract_milanuncios_links(
    email: MailMessage,
) -> list[str]:
    """
    Mantiene la interfaz genérica del registry.

    Devuelve únicamente las URLs reales de
    los anuncios encontrados.
    """

    cards = extract_milanuncios_cards(
        email
    )

    return sorted(cards.keys())