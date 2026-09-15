import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import requests
from sqlalchemy import select

from src.database import SessionLocal
from src.models import PropertyListing
from src.notifications.email_sender import (
    send_listing_summary,
)
from src.parsers.listing_details import (
    get_fotocasa_advertiser,
    get_habitaclia_advertiser,
    get_pisos_advertiser,
)


logger = logging.getLogger(__name__)


REVIEW_PORTALS = (
    "Fotocasa",
    "Habitaclia",
    "Pisos.com",
)


REVIEW_DAYS = (
    30,
    45,
    60,
    75,
    90,
)


def ensure_utc(
    value: datetime,
) -> datetime:
    """
    SQLite puede devolver datetimes sin timezone.
    Los normalizamos a UTC antes de compararlos.
    """

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def is_particular(
    advertiser: str | None,
) -> bool:
    if not advertiser:
        return False

    return (
        advertiser.strip().casefold()
        == "particular"
    )


def is_agency(
    advertiser: str | None,
) -> bool:
    """
    Consideramos agencia cualquier anunciante
    identificado que no sea Particular.
    """

    return bool(
        advertiser
        and not is_particular(advertiser)
    )


def get_due_review_stage(
    listing: PropertyListing,
    now: datetime,
) -> int | None:
    """
    Devuelve la revisión que corresponde según
    la edad original del anuncio.

    1 -> día 30
    2 -> día 45
    3 -> día 60
    4 -> día 75
    5 -> día 90

    Si el bot estuvo apagado, salta directamente
    a la revisión más reciente pendiente.
    """

    detected_at = ensure_utc(
        listing.detected_at
    )

    age = now - detected_at

    due_stage = None

    for stage, days in enumerate(
        REVIEW_DAYS,
        start=1,
    ):
        if age >= timedelta(days=days):
            due_stage = stage

    if due_stage is None:
        return None

    if (
        listing.advertiser_check_count
        >= due_stage
    ):
        return None

    return due_stage


def fetch_current_advertiser(
    listing: PropertyListing,
) -> str | None:
    if listing.portal == "Fotocasa":
        return get_fotocasa_advertiser(
            listing.url,
            raise_on_error=True,
        )

    if listing.portal == "Habitaclia":
        return get_habitaclia_advertiser(
            listing.url,
            raise_on_error=True,
        )

    if listing.portal == "Pisos.com":
        return get_pisos_advertiser(
            listing.url,
            raise_on_error=True,
        )

    raise ValueError(
        "Portal no válido para revisión: "
        f"{listing.portal}"
    )


def review_agency_listings() -> int:
    """
    Revisa anuncios actualmente guardados
    como agencia.

    Devuelve el número de anuncios que han
    cambiado a Particular o No identificado.
    """

    now = datetime.now(timezone.utc)

    changed_count = 0

    statement = (
        select(PropertyListing)
        .where(
            PropertyListing.portal.in_(
                REVIEW_PORTALS
            ),
            PropertyListing.advertiser
            .is_not(None),
            PropertyListing.advertiser
            .not_ilike("Particular"),
            PropertyListing.advertiser_check_count
            < 5,
        )
        .order_by(
            PropertyListing.detected_at
        )
    )

    with SessionLocal() as session:
        listings = list(
            session.scalars(statement)
        )

        for listing in listings:
            review_stage = (
                get_due_review_stage(
                    listing,
                    now,
                )
            )

            if review_stage is None:
                continue

            review_day = REVIEW_DAYS[
                review_stage - 1
            ]

            old_advertiser = (
                listing.advertiser
            )

            logger.info(
                "Revisando anunciante de %s "
                "| id=%s "
                "| revisión=%s "
                "| día=%s "
                "| anunciante_actual=%s",
                listing.portal,
                listing.external_id,
                review_stage,
                review_day,
                old_advertiser,
            )

            try:
                new_advertiser = (
                    fetch_current_advertiser(
                        listing
                    )
                )

            except requests.RequestException:
                logger.exception(
                    "No se pudo consultar el "
                    "anunciante de %s | id=%s. "
                    "La revisión no se consume.",
                    listing.portal,
                    listing.external_id,
                )

                continue

            # La petición ha funcionado.
            # Marcamos la revisión realizada.
            listing.advertiser_check_count = (
                review_stage
            )

            listing.last_advertiser_check_at = (
                now
            )

            # -----------------------------------------
            # SIGUE SIENDO AGENCIA
            # -----------------------------------------

            if is_agency(new_advertiser):
                logger.info(
                    "El anuncio %s de %s "
                    "sigue anunciado por agencia. "
                    "Anterior=%s | Actual=%s",
                    listing.external_id,
                    listing.portal,
                    old_advertiser,
                    new_advertiser,
                )

                # Si cambia Agencia A -> Agencia B,
                # NO modificamos advertiser.
                session.commit()

                continue

            # -----------------------------------------
            # AGENCIA -> PARTICULAR / NO IDENTIFICADO
            # -----------------------------------------

            listing.advertiser = (
                new_advertiser
            )

            listing.retention_started_at = (
                now
            )

            logger.info(
                "Cambio relevante detectado "
                "en %s | id=%s | %s -> %s",
                listing.portal,
                listing.external_id,
                old_advertiser,
                new_advertiser
                or "No identificado",
            )

            # Enviamos antes del commit.
            #
            # Si SMTP falla, hacemos rollback,
            # de forma que la siguiente ejecución
            # pueda volver a intentarlo.
            try:
                send_listing_summary([
                    listing
                ])

            except Exception:
                session.rollback()

                logger.exception(
                    "No se pudo enviar el anuncio "
                    "actualizado %s de %s. "
                    "Se reintentará posteriormente.",
                    listing.external_id,
                    listing.portal,
                )

                continue

            session.commit()

            changed_count += 1

    return changed_count