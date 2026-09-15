import re
import unicodedata

import requests
from bs4 import BeautifulSoup

from src.config import settings

def normalize_text(text: str) -> str:
    text = text.lower()

    return "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )


def extract_price(text: str) -> float | None:
    if not text:
        return None

    normalized_text = text.replace("\xa0", " ")

    pattern = re.compile(
        r"(\d{1,3}(?:[.\s]\d{3})+|\d{4,7})"
        r"(?:,\d{1,2})?\s*(?:€|eur)",
        re.IGNORECASE,
    )

    matches = pattern.findall(normalized_text)
    possible_prices = []

    for match in matches:
        number_text = (
            match
            .replace(".", "")
            .replace(" ", "")
            .replace(",", ".")
        )

        try:
            price = float(number_text)

            # Evita confundir cantidades pequeñas con precios
            if 10_000 <= price <= 20_000_000:
                possible_prices.append(price)

        except ValueError:
            continue

    if not possible_prices:
        return None

    return possible_prices[0]

def extract_price_for_listing(
    text: str,
    external_id: str,
) -> float | None:
    if not text or not external_id:
        return None

    listing_position = text.find(str(external_id))

    if listing_position == -1:
        return None

    # En Fotocasa, el precio aparece inmediatamente después
    # del primer enlace correspondiente al inmueble.
    listing_content = text[
        listing_position:listing_position + 1200
    ]

    return extract_price(listing_content)

def extract_zone(text: str) -> str | None:
    if not text:
        return None

    normalized_content = normalize_text(text)

    configured_zones = settings.zones

    if isinstance(configured_zones, str):
        zones = [
            zone.strip()
            for zone in configured_zones.split(",")
            if zone.strip()
        ]
    else:
        zones = configured_zones

    for zone in zones:
        if normalize_text(zone) in normalized_content:
            return zone

    return None

def extract_title_for_listing(
    text: str,
    external_id: str,
    zone: str | None,
) -> str | None:
    if not text or not external_id:
        return None

    listing_position = text.find(str(external_id))

    if listing_position == -1:
        return None

    listing_content = text[
        listing_position:listing_position + 1200
    ]

    match = re.search(
        r"\*([^*\n]+)\*\s*[·•-]\s*([^\(\n]+)",
        listing_content,
        re.IGNORECASE,
    )

    if not match:
        return None

    property_type = match.group(1).strip().capitalize()
    address = match.group(2).strip()

    address = re.sub(
        r",\s*Madrid(?:\s+Capital)?\s*$",
        "",
        address,
        flags=re.IGNORECASE,
    )

    address = address.title()

    title = f"{property_type} en venta en {address}"

    if (
        zone
        and normalize_text(zone)
        not in normalize_text(address)
    ):
        title += f", {zone}"

    return title


def extract_habitaclia_listing_details(
    html: str,
    external_id: str,
) -> tuple[
    str | None,
    float | None,
    str | None,
]:
    """
    Extrae los datos de una única tarjeta de Habitaclia.

    El mismo inmueble aparece varias veces en el HTML
    (imagen, precio, título y favorito). Se seleccionan
    únicamente los enlaces que contienen su identificador
    para evitar mezclar sus datos con los demás anuncios.
    """

    if not html or not external_id:
        return None, None, None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    listing_marker = f"/i{external_id}/"

    listing_links = [
        element
        for element in soup.find_all(
            "a",
            href=True,
        )
        if (
            listing_marker
            in element["href"]
            and "nuevo"
            in element["href"].casefold()
        )
    ]

    if not listing_links:
        return None, None, None

    text_parts: list[str] = []

    for element in listing_links:
        element_text = element.get_text(
            " ",
            strip=True,
        )

        if (
            element_text
            and element_text not in text_parts
        ):
            text_parts.append(element_text)

    listing_text = " ".join(text_parts)

    price = extract_price(
        listing_text
    )

    zone = extract_zone(
        listing_text
    )

    title = None

    for element in listing_links:
        for paragraph in element.find_all("p"):
            paragraph_parts = list(
                paragraph.stripped_strings
            )

            if not paragraph_parts:
                continue

            candidate = paragraph_parts[0]

            match = re.match(
                r"(.+?)\s+en\s+Madrid\s*-\s*"
                r"(.+?)(?:\s*\(|$)",
                candidate,
                re.IGNORECASE,
            )

            if not match:
                continue

            property_type = (
                match.group(1)
                .strip()
                .capitalize()
            )

            listing_area = (
                zone
                or match.group(2).strip()
            )

            title = (
                f"{property_type} en venta "
                f"en {listing_area}"
            )

            break

        if title:
            break

    return title, price, zone


def extract_pisos_listing_details(
    html: str,
    external_id: str,
) -> tuple[
    str | None,
    float | None,
    str | None,
]:
    """Extrae título, precio y zona de una tarjeta de Pisos.com."""

    if not html or not external_id:
        return None, None, None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    listing_links = [
        element
        for element in soup.find_all(
            "a",
            href=True,
        )
        if (
            external_id in element["href"]
            and (
                "/comprar/" in element["href"]
                or "/promocion-" in element["href"]
            )
        )
    ]

    if not listing_links:
        return None, None, None

    # El enlace de la imagen puede estar dentro de otra
    # tabla. Subimos hasta la primera tabla que contenga
    # el precio de ese inmueble.
    listing_card = None

    for element in listing_links:
        for table in element.find_parents("table"):
            table_text = table.get_text(
                " ",
                strip=True,
            )

            if "€" in table_text:
                listing_card = table
                break

        if listing_card is not None:
            break

    if listing_card is None:
        return None, None, None

    listing_text = listing_card.get_text(
        " ",
        strip=True,
    )

    price = extract_price(
        listing_text
    )

    # La zona está en un párrafo propio. Buscar párrafo
    # por párrafo evita coger Goya del encabezado cuando
    # la tarjeta realmente pertenece, por ejemplo, a Ibiza.
    zone = None

    paragraphs = listing_card.find_all("p")

    for paragraph in paragraphs:
        zone = extract_zone(
            paragraph.get_text(
                " ",
                strip=True,
            )
        )

        if zone:
            break

    title = None

    # Pisos.com identifica los enlaces del título mediante
    # utm_term=titulo_*. Es más estable que depender de
    # estilos CSS inline del correo.
    for element in listing_links:
        if "utm_term=titulo_" not in element["href"].casefold():
            continue

        title_paragraph = element.find("p")

        if title_paragraph is not None:
            candidate = title_paragraph.get_text(
                " ",
                strip=True,
            )
        else:
            candidate = element.get_text(
                " ",
                strip=True,
            )

        if candidate:
            title = candidate
            break

    if not title and paragraphs:
        title = paragraphs[0].get_text(
            " ",
            strip=True,
        )

    if title:
    # Pisos.com puede enviar títulos como:
    # "Piso en venta en Calle de Oltra, 8"
    # o simplemente:
    # "Piso en Calle de Oltra, 8"
    #
    # Eliminamos primero "en venta" para evitar:
    # "Piso en venta en venta en ..."
        clean_title = re.sub(
            r"\s+en\s+venta\s+en\s+",
            " en ",
            title,
            count=1,
            flags=re.IGNORECASE,
        )

        match = re.match(
            r"(.+?)\s+en\s+(.+)$",
            clean_title,
            re.IGNORECASE,
        )

        if match:
            property_type = (
                match.group(1)
                .strip()
                .capitalize()
            )

            address = (
                match.group(2)
                .strip()
            )

            title = (
                f"{property_type} en venta "
                f"en {address}"
            )

            if (
                zone
                and normalize_text(zone)
                not in normalize_text(address)
            ):
                title += f", {zone}"

    return title, price, zone
def extract_pisos_advertiser(
    html: str,
) -> str | None:
    """
    Extrae el anunciante de una ficha individual
    de Pisos.com.

    Devuelve:
        - Nombre de la agencia si es profesional.
        - "Particular" si Pisos.com identifica el
          vendedor como particular.
        - None si no puede determinarse.
    """

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # =================================================
    # AGENCIA / PROFESIONAL
    # =================================================

    owner_name = soup.select_one(
        ".owner-info__name"
    )

    if owner_name is not None:
        advertiser = owner_name.get_text(
            " ",
            strip=True,
        )

        if advertiser:
            return advertiser

    # Como respaldo, Pisos.com también incluye
    # el nombre comercial en el alt del logo.
    owner_logo = soup.select_one(
        "img.owner-info__logo"
    )

    if owner_logo is not None:
        advertiser = (
            owner_logo.get("alt")
            or ""
        ).strip()

        if advertiser:
            return advertiser

    # =================================================
    # PARTICULAR
    # =================================================
    #
    # Pisos.com incluye información estructurada
    # sobre el tipo de vendedor en vtmVars.
    #
    # IMPORTANTE:
    # No usar "usuarioLogado", porque no representa
    # necesariamente el tipo de vendedor del anuncio.

    vtm_vars = soup.select_one(
        "#vtmVars"
    )

    if vtm_vars is not None:
        seller_data = (
            vtm_vars.get("data-var")
            or ""
        )

        seller_match = re.search(
            r'"tipoVendedor"\s*:\s*"([^"]+)"',
            seller_data,
            re.IGNORECASE,
        )

        if seller_match:
            seller_type = (
                seller_match.group(1)
                .strip()
                .casefold()
            )

            if seller_type == "particular":
                return "Particular"

            # Si sabemos que es profesional pero
            # no hemos podido obtener su nombre,
            # no lo confundimos con un particular.
            if seller_type == "profesional":
                return "Profesional"

    return None

def get_pisos_advertiser(
    url: str,
    *,
    raise_on_error: bool = False,
) -> str | None:
    """
    Descarga la ficha de Pisos.com y devuelve
    el anunciante.
    """

    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=10,
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

        response.raise_for_status()

        return extract_pisos_advertiser(
            response.text
        )

    except requests.RequestException:
        if raise_on_error:
            raise

        return None

def extract_habitaclia_advertiser(
    html: str,
) -> str | None:
    """
    Extrae el anunciante desde la ficha individual
    de un inmueble de Habitaclia.

    Ejemplo:
        Domus Now
        Getafe Now
    """

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # Habitaclia suele mostrar cerca del anunciante
    # textos como "Ver todos sus anuncios" o
    # "Contactar con el anunciante".
    advertiser_area = soup.find(
        string=re.compile(
            r"(ver\s+todos\s+sus\s+anuncios"
            r"|contactar\s+con\s+el\s+anunciante)",
            re.IGNORECASE,
        )
    )

    if advertiser_area:
        element = advertiser_area.parent

        # Recorremos contenedores cercanos para buscar
        # el nombre de la agencia.
        for container in element.parents:
            container_text = container.get_text(
                " ",
                strip=True,
            )

            if len(container_text) > 2500:
                break

            candidates = container.find_all(
                [
                    "strong",
                    "b",
                    "h2",
                    "h3",
                    "h4",
                    "a",
                    "span",
                    "div",
                ]
            )

            for candidate in candidates:
                text = candidate.get_text(
                    " ",
                    strip=True,
                )

                if not text:
                    continue

                normalized = normalize_text(
                    text
                )

                ignored = (
                    "ver todos sus anuncios",
                    "contactar con el anunciante",
                    "contacta con el anunciante",
                    "contactar",
                    "telefono",
                    "email",
                    "e-mail",
                    "quieres mas informacion",
                    "pregunta al anunciante",
                    "favorito",
                )

                if any(
                    ignored_text in normalized
                    for ignored_text in ignored
                ):
                    continue

                # Descartamos textos excesivamente largos.
                if not 2 <= len(text) <= 100:
                    continue

                # Descartamos teléfonos.
                compact = re.sub(
                    r"\s+",
                    "",
                    text,
                )

                if re.fullmatch(
                    r"[+\d()\-]+",
                    compact,
                ):
                    continue

                return text

    return None


def get_habitaclia_advertiser(
    url: str,
    *,
    raise_on_error: bool = False,
) -> str | None:
    """
    Accede a la ficha individual de Habitaclia
    y devuelve el nombre del anunciante.
    """

    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=10,
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

        response.raise_for_status()

        return extract_habitaclia_advertiser(
            response.text
        )

    except requests.RequestException:
        if raise_on_error:
            raise

        return None

def extract_fotocasa_advertiser(
    html: str,
) -> str | None:
    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    contact_heading = soup.find(
        string=re.compile(
            r"contacta\s+con\s+el\s+anunciante",
            re.IGNORECASE,
        )
    )

    if not contact_heading:
        return None

    heading_element = contact_heading.parent

    ignored = {
        "tu nombre",
        "tus datos",
        "contactar",
        "ver telefono",
        "ver teléfono",
        "telefono",
        "teléfono",
        "email",
        "e-mail",
        "referencia",
        "fotocasa",
        "sello de calidad fotocasa",
    }

    commercial_words = (
        "inmobiliaria",
        "inmobiliario",
        "realty",
        "properties",
        "property",
        "homes",
        "housing",
        "group",
        "grupo",
        "estate",
        "remax",
        "century",
        "lucas fox",
    )

    for container in heading_element.parents:
        container_text = container.get_text(
            " ",
            strip=True,
        )

        if len(container_text) > 4000:
            break

        # Nombre desde logo
        for image in container.find_all("img"):
            for attribute in (
                "alt",
                "title",
            ):
                candidate = image.get(
                    attribute
                )

                if not candidate:
                    continue

                candidate = candidate.strip()

                normalized = normalize_text(
                    candidate
                )

                if normalized in {
                    normalize_text(value)
                    for value in ignored
                }:
                    continue

                if (
                    2 <= len(candidate) <= 120
                    and "fotocasa"
                    not in normalized
                ):
                    return candidate

        # Nombre comercial en texto
        for element in container.find_all(
            [
                "strong",
                "b",
                "a",
                "span",
            ]
        ):
            candidate = element.get_text(
                " ",
                strip=True,
            )

            if not candidate:
                continue

            normalized = normalize_text(
                candidate
            )

            if normalized in {
                normalize_text(value)
                for value in ignored
            }:
                continue

            if any(
                word in normalized
                for word in commercial_words
            ):
                if 2 <= len(candidate) <= 120:
                    return candidate

    # Hemos podido localizar correctamente el bloque
    # de contacto, pero no existe ninguna señal de agencia.
    return "Particular"
def get_fotocasa_advertiser(
    url: str,
    *,
    raise_on_error: bool = False,
) -> str | None:
    """
    Accede a la ficha individual de Fotocasa
    y devuelve el anunciante.
    """

    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=10,
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

        response.raise_for_status()

        return extract_fotocasa_advertiser(
            response.text
        )

    except requests.RequestException:
        if raise_on_error:
            raise

        return None


def extract_idealista_listing_details(
    html: str,
    external_id: str,
) -> tuple[
    str | None,
    float | None,
    str | None,
]:
    """
    Extrae título, precio y zona de un inmueble
    incluido en un correo de Idealista.
    """

    if not html or not external_id:
        return None, None, None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    listing_pattern = re.compile(
        rf"/inmueble/{re.escape(external_id)}/?",
        re.IGNORECASE,
    )

    listing_links = [
        element
        for element in soup.find_all(
            "a",
            href=True,
        )
        if listing_pattern.search(
            element["href"]
        )
    ]

    if not listing_links:
        return None, None, None

    # ---------------------------------------------
    # TÍTULO
    # ---------------------------------------------
    title = None

    for element in listing_links:
        candidate = (
            element.get("title")
            or element.get_text(
                " ",
                strip=True,
            )
        )

        if not candidate:
            continue

        candidate = candidate.strip()

        if not re.search(
            r"\b("
            r"piso|chalet|ático|atico|dúplex|duplex|"
            r"estudio|casa|apartamento|loft"
            r")\b",
            candidate,
            re.IGNORECASE,
        ):
            continue

        title = candidate
        break

    # ---------------------------------------------
    # ZONA
    # ---------------------------------------------
    zone = extract_zone(
        title or ""
    )

    # ---------------------------------------------
    # PRECIO
    # ---------------------------------------------
    price = None

    for element in listing_links:
        for container in element.parents:
            if container.name not in {
                "td",
                "tr",
                "table",
                "div",
            }:
                continue

            container_text = container.get_text(
                " ",
                strip=True,
            )

            if "€" not in container_text:
                continue

            if len(container_text) > 3000:
                continue

            possible_price = extract_price(
                container_text
            )

            if possible_price is not None:
                price = possible_price
                break

        if price is not None:
            break

    # ---------------------------------------------
    # NORMALIZAR TÍTULO
    # ---------------------------------------------
    if title:
        title = re.sub(
            r",\s*Madrid\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

        if not re.search(
            r"\ben\s+venta\b",
            title,
            re.IGNORECASE,
        ):
            title = re.sub(
                r"^(.+?)\s+en\s+",
                r"\1 en venta en ",
                title,
                count=1,
                flags=re.IGNORECASE,
            )

    return title, price, zone

def extract_milanuncios_listing_details(
    html: str,
    external_id: str,
) -> tuple[
    str | None,
    float | None,
    str | None,
]:
    """
    Extrae los datos disponibles de una tarjeta
    de Milanuncios incluida en el email.

    La ficha individual devuelve actualmente HTTP 403,
    por lo que no dependemos de ella.
    """

    if not html or not external_id:
        return None, None, None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # Milanuncios usa URLs de tracking dentro del email,
    # por lo que el external_id normalmente no aparece
    # directamente en el href.
    #
    # Buscamos tarjetas con precio y datos inmobiliarios.
    candidate_cards = []

    for table in soup.find_all("table"):
        card_text = table.get_text(
            " ",
            strip=True,
        )

        if "€" not in card_text:
            continue

        if (
            "Madrid" not in card_text
            and "madrid" not in card_text.casefold()
        ):
            continue

        if len(card_text) > 2500:
            continue

        candidate_cards.append(table)

    # De momento no podemos relacionar de forma 100 %
    # fiable cada tarjeta con el external_id porque el
    # ID está oculto detrás del enlace de tracking.
    #
    # La asociación exacta se podrá mejorar guardando
    # tracking_url -> final_url durante el parser.
    if len(candidate_cards) != 1:
        return None, None, None

    listing_card = candidate_cards[0]

    listing_text = listing_card.get_text(
        " ",
        strip=True,
    )

    price = extract_price(
        listing_text
    )

    zone = extract_zone(
        listing_text
    )

    title = None

    return title, price, zone
