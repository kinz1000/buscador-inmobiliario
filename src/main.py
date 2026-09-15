import logging
from src.scheduler import start_scheduler
from imap_tools import MailMessage

from src.config import settings
from src.connectors.email_connector import (
    fetch_unread_emails,
    mark_emails_as_read,
)
from src.database import create_database
from src.logging_config import setup_logging
from src.models import PropertyListing
from src.notifications.email_sender import (
    send_listing_summary,
    send_parser_health_alert,
)
from src.monitoring.parser_health import (
    should_alert_for_missing_data,
    should_send_parser_alert,
)
from src.parsers.listing_details import (
    extract_habitaclia_listing_details,
    extract_idealista_listing_details,
    extract_pisos_listing_details,
    extract_price,
    extract_price_for_listing,
    extract_title_for_listing,
    extract_zone,
    get_fotocasa_advertiser,
    get_habitaclia_advertiser,
    get_pisos_advertiser,
)

from src.parsers.milanuncios_parser import (
    extract_milanuncios_cards,
)

from src.services.listing_maintenance import (
    review_agency_listings,
)
from src.parsers.registry import get_portal_parser
from src.pipeline import (
    delete_expired_listings,
    listing_exists,
    normalize_url,
    save_listing,
)


logger = logging.getLogger(__name__)

def review_existing_agencies() -> None:
    try:
        changed_count = (
            review_agency_listings()
        )

        if changed_count > 0:
            logger.info(
                "Anuncios que han dejado de "
                "estar identificados como "
                "agencia: %s",
                changed_count,
            )
        else:
            logger.info(
                "Revisión de agencias completada: "
                "sin cambios relevantes"
            )

    except Exception:
        logger.exception(
            "Error durante la revisión "
            "de agencias"
        )
def mark_processed_emails(
    email_uids: set[str],
) -> None:
    if not email_uids:
        return

    marked_count = mark_emails_as_read(
        email_uids
    )

    logger.info(
        "Correos procesados y marcados como leídos: %s",
        marked_count,
    )


def process_email(
    email: MailMessage,
    new_listings: dict[str, PropertyListing],
) -> bool:
    """
    Procesa un único correo.

    Devuelve True cuando el correo se ha revisado
    correctamente y puede marcarse como leído, aunque
    no contenga anuncios procesables.

    Devuelve False si no pertenece a un portal o sucede
    algún error durante el análisis.
    """

    parser = get_portal_parser(
        email
    )

    if parser is None:
        return False

    try:
        milanuncios_cards = {}

        if parser.portal == "Milanuncios":
            milanuncios_cards = (
                extract_milanuncios_cards(
                    email
                )
            )

            links = sorted(
                milanuncios_cards.keys()
            )

        else:
            links = parser.extract_links(
                email
            )

        logger.info(
            "Alerta de %s encontrada con %s enlaces",
            parser.portal,
            len(links),
        )
#--------
        if not links:
            logger.warning(
                "Correo de %s reconocido pero "
                "sin enlaces detectados.",
                parser.portal,
            )

            issue_code = "no_links_found"

            details = (
                f"Se recibió un correo reconocido "
                f"como {parser.portal}, pero el parser "
                f"no encontró ningún enlace.\n\n"
                f"Asunto: "
                f"{email.subject or 'Sin asunto'}\n"
                f"Remitente: "
                f"{email.from_ or 'Desconocido'}"
            )

            if should_send_parser_alert(
                portal=parser.portal,
                issue_code=issue_code,
                message=details,
            ):
                try:
                    send_parser_health_alert(
                        portal=parser.portal,
                        issue="0 enlaces encontrados",
                        details=details,
                    )

                    logger.warning(
                        "Alerta de parser enviada "
                        "para %s.",
                        parser.portal,
                    )

                except Exception:
                    logger.exception(
                        "No se pudo enviar la alerta "
                        "del parser de %s.",
                        parser.portal,
                    )

            # No se marca como leído.
            #
            # Así podrá volver a procesarse cuando
            # arreglemos el parser.
            return False

            return True

        raw_content = (
            email.text
            or email.html
            or ""
        )

        # Guardamos temporalmente los anuncios de este
        # correo. Solo los añadimos al resumen cuando
        # todo el mensaje termina correctamente.
        email_listings: dict[
            str,
            PropertyListing,
        ] = {}
        
        total_new_items = 0
        missing_external_ids = 0
        missing_prices = 0

        for extracted_link in links:
          

            # Eliminamos parámetros de seguimiento,
            # fragmentos y diferencias como http/https.
            link = normalize_url(
                extracted_link
            )

            if not link:
                logger.warning(
                    "Se ha descartado una URL vacía "
                    "de %s.",
                    parser.portal,
                )
                continue

            external_id = parser.extract_id(
                link
            )

            # Comprueba si el mismo anuncio ya apareció
            # en otro correo de esta ejecución.
            if (
                link in new_listings
                or link in email_listings
            ):
                logger.info(
                    "Anuncio repetido durante esta "
                    "ejecución de %s: %s",
                    parser.portal,
                    link,
                )

                continue

            # Comprueba si ya está guardado en SQLite.
            if listing_exists(
                url=link,
                portal=parser.portal,
                external_id=external_id,
            ):
                logger.info(
                    "Anuncio duplicado de %s: %s",
                    parser.portal,
                    link,
                )

                continue
            total_new_items += 1

            if not external_id:
                missing_external_ids += 1 

            listing_title = None
            listing_price = None
            listing_zone = None
            listing_advertiser = None

            # =================================================
            # HABITACLIA
            # =================================================
            if parser.portal == "Habitaclia":
                (
                    listing_title,
                    listing_price,
                    listing_zone,
                ) = extract_habitaclia_listing_details(
                    email.html or "",
                    external_id or "",
                )

                # La alerta de Barrio de Salamanca también
                # puede incluir otras zonas.
                if not listing_zone:
                    logger.info(
                        "Anuncio de Habitaclia fuera de "
                        "las zonas configuradas: %s",
                        link,
                    )

                    continue

                listing_advertiser = (
                    get_habitaclia_advertiser(
                        link
                    )
                )

                logger.info(
                    "Anunciante de Habitaclia para %s: %s",
                    external_id,
                    listing_advertiser
                    or "no identificado",
                )

            # =================================================
            # PISOS.COM
            # =================================================
            elif parser.portal == "Pisos.com":
                (
                    listing_title,
                    listing_price,
                    listing_zone,
                ) = extract_pisos_listing_details(
                    email.html or "",
                    external_id or "",
                )

                if not listing_zone:
                    logger.info(
                        "Anuncio de Pisos.com fuera de "
                        "las zonas configuradas: %s",
                        link,
                    )

                    continue

                listing_advertiser = (
                    get_pisos_advertiser(
                        link
                    )
                )

                logger.info(
                    "Anunciante de Pisos.com para %s: %s",
                    external_id,
                    listing_advertiser
                    or "no identificado",
                )

            # =================================================
            # IDEALISTA
            # =================================================
            elif parser.portal == "Idealista":
                (
                    listing_title,
                    listing_price,
                    listing_zone,
                ) = extract_idealista_listing_details(
                    email.html or "",
                    external_id or "",
                )

                if not listing_zone:
                    logger.info(
                        "Anuncio de Idealista fuera de "
                        "las zonas configuradas: %s",
                        link,
                    )

                    continue

                # -------------------------------------------------
                # ANUNCIANTE IDEALISTA
                # -------------------------------------------------
                #
                # La identificación de profesional/particular se
                # integrará mediante la API oficial de Idealista.
                #
                # Hasta disponer de esa API, el anunciante queda
                # como no identificado.
                #
                listing_advertiser = None

                logger.info(
                    "Datos de Idealista %s | "
                    "titulo=%s | "
                    "precio=%s | "
                    "zona=%s | "
                    "anunciante=%s",
                    external_id,
                    listing_title
                    or "no identificado",
                    listing_price
                    or "no identificado",
                    listing_zone
                    or "no identificada",
                    listing_advertiser
                    or "no identificado",
                )


            # =================================================
            # MILANUNCIOS
            # =================================================
            elif parser.portal == "Milanuncios":
                card = milanuncios_cards.get(
                    extracted_link,
                    {}
                )

                listing_price = card.get(
                    "price"
                )

                location = card.get(
                    "location"
                )

                # Las alertas de Milanuncios están
                # configuradas exclusivamente con:
                #
                # Tipo de vendedor = Particular
                listing_advertiser = "Particular"

                # Intentamos localizar una de nuestras
                # cuatro zonas primero en el asunto de
                # la alerta y después en la ubicación
                # proporcionada por Milanuncios.
                listing_zone = extract_zone(
                    " ".join(
                        filter(
                            None,
                            [
                                email.subject,
                                location,
                            ],
                        )
                    )
                )

                # El email no proporciona actualmente
                # un título concreto del inmueble.
                #
                # Evitamos utilizar el asunto completo:
                # "6 novedades en Venta de pisos..."
                if location:
                    listing_title = (
                        f"Piso en venta en {location}"
                    )
                else:
                    listing_title = (
                        "Piso en venta en Milanuncios"
                    )

                logger.info(
                    "Datos de Milanuncios %s | "
                    "titulo=%s | "
                    "precio=%s | "
                    "ubicacion=%s | "
                    "zona=%s | "
                    "anunciante=%s",
                    external_id,
                    listing_title
                    or "no identificado",
                    listing_price
                    or "no identificado",
                    location
                    or "no identificada",
                    listing_zone
                    or "no identificada",
                    listing_advertiser,
                )
            # =================================================
            # FOTOCASA
            # =================================================
            elif parser.portal == "Fotocasa":
                listing_price = (
                    extract_price_for_listing(
                        raw_content,
                        external_id,
                    )
                )

                listing_advertiser = (
                    get_fotocasa_advertiser(
                        link
                    )
                )

                logger.info(
                    "Anunciante de Fotocasa para %s: %s",
                    external_id,
                    listing_advertiser
                    or "no identificado",
                )

            # =================================================
            # OTROS PORTALES
            # =================================================
            elif len(links) == 1:
                listing_price = extract_price(
                    raw_content
                )

            else:
                listing_price = None

            # =================================================
            # ZONA
            # =================================================
            #
            # Habitaclia, Pisos.com e Idealista ya obtienen
            # la zona de la tarjeta concreta del inmueble.
            #
            # Para Fotocasa y otros portales seguimos usando
            # el extractor general.
            if parser.portal not in {
                "Habitaclia",
                "Pisos.com",
                "Idealista",
                "Milanuncios",
            }:
                listing_zone = extract_zone(
                    f"{raw_content} {link}"
                )

            # =================================================
            # TÍTULO
            # =================================================
            #
            # Fotocasa obtiene el título mediante el ID.
            if parser.portal == "Fotocasa":
                listing_title = (
                    extract_title_for_listing(
                        raw_content,
                        external_id,
                        listing_zone,
                    )
                )

            # Habitaclia, Pisos.com e Idealista ya han
            # obtenido el título de su tarjeta.
            elif parser.portal not in {
                "Habitaclia",
                "Pisos.com",
                "Idealista",
                "Milanuncios",
            }:
                listing_title = None

            # Si no podemos extraer el título exacto,
            # utilizamos el asunto del correo.
            if not listing_title:
                listing_title = (
                    email.subject
                    or f"Anuncio de {parser.portal}"
                )

            # =================================================
            # CREAR INMUEBLE
            # =================================================
            listing = PropertyListing(
                portal=parser.portal,
                external_id=external_id,
                title=listing_title,
                price=listing_price,
                zone=listing_zone,
                advertiser=listing_advertiser,
                url=link,
                raw_data=raw_content[:5000],
            )

            email_listings[link] = listing



        # AQUÍ VA EL PASO 6
        if should_alert_for_missing_data(
            total_items=total_new_items,
            missing_items=missing_external_ids,
        ):
            details = (
                f"Portal: {parser.portal}\n"
                f"Anuncios evaluados: {total_new_items}\n"
                f"Sin external_id: {missing_external_ids}\n"
                f"Porcentaje de fallo: "
                f"{(
                    missing_external_ids
                    / total_new_items
                ) * 100:.0f}%"
            )

            if should_send_parser_alert(
                portal=parser.portal,
                issue_code="missing_external_id_ratio",
                message=details,
            ):
                try:
                    send_parser_health_alert(
                        portal=parser.portal,
                        issue=(
                            "Demasiados anuncios "
                            "sin external_id"
                        ),
                        details=details,
                    )

                except Exception:
                    logger.exception(
                        "No se pudo enviar la alerta "
                        "de external_id para %s.",
                        parser.portal,
                    )


        if should_alert_for_missing_data(
            total_items=total_new_items,
            missing_items=missing_prices,
        ):
            details = (
                f"Portal: {parser.portal}\n"
                f"Anuncios evaluados: {total_new_items}\n"
                f"Sin precio: {missing_prices}\n"
                f"Porcentaje de fallo: "
                f"{(
                    missing_prices
                    / total_new_items
                ) * 100:.0f}%"
            )

            if should_send_parser_alert(
                portal=parser.portal,
                issue_code="missing_price_ratio",
                message=details,
            ):
                try:
                    send_parser_health_alert(
                        portal=parser.portal,
                        issue=(
                            "Demasiados anuncios "
                            "sin precio"
                        ),
                        details=details,
                    )

                except Exception:
                    logger.exception(
                        "No se pudo enviar la alerta "
                        "de precios para %s.",
                        parser.portal,
                    )
        # Incorporamos los anuncios solamente después
        # de terminar correctamente todo el correo.
        for link, listing in email_listings.items():
            new_listings[link] = listing

            logger.info(
                "Anuncio nuevo de %s: %s",
                listing.portal,
                link,
            )

        return True

    except Exception:
        logger.exception(
            "Error procesando un correo de %s. "
            "El mensaje se mantiene sin leer.",
            parser.portal,
        )

        return False


def run_once() -> None:
    logger.info(
        "Comenzando búsqueda de anuncios"
    )

    try:
        emails = fetch_unread_emails(
            limit=100
        )

        logger.info(
            "Correos inmobiliarios no leídos "
            "recuperados: %s",
            len(emails),
        )

        new_listings: dict[
            str,
            PropertyListing,
        ] = {}

        processed_email_uids: set[str] = set()

        for email in emails:
            processed_correctly = process_email(
                email,
                new_listings,
            )

            if not processed_correctly:
                continue

            if email.uid:
                processed_email_uids.add(
                    email.uid
                )
            else:
                logger.warning(
                    "Un correo se procesó correctamente, "
                    "pero no tiene UID y no puede marcarse "
                    "como leído."
                )

        if not new_listings:
            # Los correos que solamente tenían anuncios
            # duplicados también se marcan como leídos.
            mark_processed_emails(
                processed_email_uids
            )

            logger.info(
                "No hay inmuebles nuevos. "
                "No se envía correo."
            )

            return

        # Si falla el envío, se producirá una excepción.
        # Los correos seguirán sin leer para reintentarlos.
        send_listing_summary(
            list(new_listings.values())
        )

        logger.info(
            "Correo enviado con %s anuncios",
            len(new_listings),
        )

        saved_count = 0

        for listing in new_listings.values():
            if save_listing(listing):
                saved_count += 1

        logger.info(
            "Anuncios guardados en SQLite: %s",
            saved_count,
        )

        # Se marcan después de enviar el resumen
        # y guardar los anuncios correctamente.
        mark_processed_emails(
            processed_email_uids
        )

    except Exception:
        logger.exception(
            "Ha ocurrido un error durante "
            "la ejecución"
        )


def clean_history() -> None:
    try:
        deleted_count = (
            delete_expired_listings()
        )

        if deleted_count > 0:
            logger.info(
                "Anuncios expirados eliminados: %s",
                deleted_count,
            )
        else:
            logger.info(
                "Limpieza completada: "
                "no hay anuncios expirados"
            )

    except Exception:
        logger.exception(
            "No se pudo limpiar el histórico"
        )
def run_cycle() -> None:
    review_existing_agencies()
    clean_history()
    run_once()

def main() -> None:
    setup_logging()

    logger.info(
        "Iniciando %s",
        settings.app_name,
    )

    create_database()

    logger.info(
        "Base de datos preparada"
    )

    # Primera ejecución inmediatamente al arrancar.
    run_cycle()

    logger.info(
        "Primera ejecución terminada. "
        "Iniciando scheduler cada %s minutos.",
        settings.check_interval_minutes,
    )

    # A partir de aquí run_cycle se ejecutará
    # automáticamente cada X minutos.
    start_scheduler(run_cycle)


if __name__ == "__main__":
    main()

