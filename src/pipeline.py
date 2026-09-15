import re
import unicodedata
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from sqlalchemy import (
    and_,
    delete,
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.database import SessionLocal
from src.models import PropertyListing


def normalize_text(
    text: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        text,
    )

    return (
        normalized
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
        .strip()
    )


def normalize_url(
    url: str,
) -> str:
    """
    Convierte diferentes versiones de una URL
    en una única dirección canónica.
    """

    clean_url = url.strip()

    if not clean_url:
        return ""

    parsed_url = urlsplit(
        clean_url
    )

    hostname = (
        parsed_url.hostname
        or ""
    ).casefold()

    if not hostname:
        return clean_url

    # Los cinco portales admiten direcciones
    # con y sin www. Guardaremos siempre www.
    if not hostname.startswith("www."):
        hostname = f"www.{hostname}"

    # Evita barras duplicadas dentro de la ruta.
    normalized_path = re.sub(
        r"/+",
        "/",
        parsed_url.path,
    )

    # Guardamos las URL sin barra final.
    normalized_path = (
        normalized_path.rstrip("/")
    )

    return urlunsplit((
        "https",
        hostname,
        normalized_path,
        "",
        "",
    ))


def is_allowed_zone(
    zone: str | None,
) -> bool:
    if not zone:
        return False

    normalized_zone = normalize_text(
        zone
    )

    return any(
        normalize_text(allowed_zone)
        in normalized_zone
        for allowed_zone in settings.zone_list
    )


def listing_exists(
    url: str,
    portal: str,
    external_id: str | None,
) -> bool:
    normalized_url = normalize_url(
        url
    )

    conditions = [
        PropertyListing.url
        == normalized_url,
    ]

    if external_id:
        conditions.append(
            and_(
                PropertyListing.portal
                == portal,
                PropertyListing.external_id
                == external_id,
            )
        )

    statement = (
        select(PropertyListing.id)
        .where(or_(*conditions))
        .limit(1)
    )

    with SessionLocal() as session:
        return (
            session.scalar(statement)
            is not None
        )


def save_listing(
    listing: PropertyListing,
) -> bool:
    listing.url = normalize_url(
        listing.url
    )

    with SessionLocal() as session:
        try:
            session.add(listing)
            session.commit()

            return True

        except IntegrityError:
            session.rollback()

            return False


def delete_expired_listings() -> int:
    now = datetime.now(timezone.utc)

    seven_days_ago = (
        now - timedelta(days=7)
    )

    thirty_days_ago = (
        now - timedelta(days=30)
    )

    ninety_days_ago = (
        now - timedelta(days=90)
    )

    quick_expiry_portals = (
        "Idealista",
        "Milanuncios",
    )

    reviewable_portals = (
        "Fotocasa",
        "Habitaclia",
        "Pisos.com",
    )

    statement = delete(
        PropertyListing
    ).where(
        or_(
            # Idealista y Milanuncios:
            # se eliminan a los 7 días.
            and_(
                PropertyListing.portal.in_(
                    quick_expiry_portals
                ),
                PropertyListing.detected_at
                < seven_days_ago,
            ),

            # Particular o no identificado:
            # se eliminan 30 días después.
            and_(
                PropertyListing.portal.in_(
                    reviewable_portals
                ),
                or_(
                    PropertyListing.advertiser
                    .is_(None),

                    PropertyListing.advertiser
                    .ilike("Particular"),
                ),
                PropertyListing.retention_started_at
                < thirty_days_ago,
            ),

            # Agencia:
            # se elimina tras la revisión final.
            and_(
                PropertyListing.portal.in_(
                    reviewable_portals
                ),
                PropertyListing.advertiser
                .is_not(None),

                ~PropertyListing.advertiser
                .ilike("Particular"),

                PropertyListing.detected_at
                < ninety_days_ago,

                PropertyListing.advertiser_check_count
                >= 5,
            ),
        )
    )

    with SessionLocal() as session:
        result = session.execute(
            statement
        )

        session.commit()

        return result.rowcount or 0
def process_listing(
    listing: PropertyListing,
) -> str:
    if not is_allowed_zone(
        listing.zone
    ):
        return "rejected_zone"

    if save_listing(listing):
        return "saved"

    return "duplicate"