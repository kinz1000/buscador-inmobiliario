from collections import defaultdict
from email.message import EmailMessage
from html import escape
from pathlib import Path
import smtplib
import ssl

from src.config import settings
from src.models import PropertyListing


PORTAL_COLORS = {
    "habitaclia": "#ff6600",
    "fotocasa": "#1976d2",
    "pisos.com": "#e50013",
    "idealista": "#a7c90f",
    "milanuncios": "#00a941",
}

DEFAULT_PORTAL_COLOR = "#1976d2"

HEADER_IMAGE_CID = "radar_inmobiliario_header"

HEADER_IMAGE_PATH = (
    Path(__file__).resolve().parent
    / "assets"
    / "cabecera-radar-inmobiliario-email.jpg"
)


def get_portal_color(
    portal: str,
) -> str:
    return PORTAL_COLORS.get(
        portal.casefold(),
        DEFAULT_PORTAL_COLOR,
    )


def format_price(
    price: int | float | None,
) -> str:
    if price is None:
        return "Precio no identificado"

    return f"{price:,.0f} €".replace(",", ".")


def validate_email_settings() -> None:
    if not settings.smtp_user:
        raise ValueError(
            "Falta SMTP_USER en el archivo .env"
        )

    if not settings.smtp_password:
        raise ValueError(
            "Falta SMTP_PASSWORD en el archivo .env"
        )

    if not settings.notification_email:
        raise ValueError(
            "Falta NOTIFICATION_EMAIL en el archivo .env"
        )

def send_parser_health_alert(
    portal: str,
    issue: str,
    details: str,
) -> None:
    """
    Envía una alerta técnica cuando parece que
    un parser ha dejado de funcionar correctamente.
    """

    validate_email_settings()

    message = EmailMessage()

    message["Subject"] = (
        f"⚠️ Alerta parser - {portal}"
    )

    message["From"] = settings.smtp_user
    message["To"] = settings.notification_email

    message.set_content(
        "\n".join([
            "Se ha detectado un posible problema "
            "en el buscador inmobiliario.",
            "",
            f"Portal: {portal}",
            f"Problema: {issue}",
            "",
            "Detalles:",
            details,
            "",
            "Es posible que el portal haya "
            "cambiado el formato de sus correos.",
            "",
            "Revisa el parser correspondiente.",
        ])
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
    ) as server:
        server.starttls(
            context=context
        )

        server.login(
            settings.smtp_user,
            settings.smtp_password,
        )

        server.send_message(
            message
        )

def get_advertiser_text(
    listing: PropertyListing,
) -> str:
    """
    Devuelve el anunciante que se mostrará
    en el resumen.
    """

    if listing.advertiser:
        return listing.advertiser

    return "No identificado"


def send_listing_summary(
    listings: list[PropertyListing],
) -> None:
    if not listings:
        return

    total_listings = len(listings)

    particular_count = sum(
        1
        for listing in listings
            if (
                listing.advertiser
                and listing.advertiser.casefold()
                == "particular"
            )
    )

    unknown_count = sum(
        1
        for listing in listings
        if not listing.advertiser
    )

    agency_count = (
        total_listings
        - particular_count
        - unknown_count
    )

    if particular_count == 0 and unknown_count == 0:
        return

    visible_listings = [
    listing
    for listing in listings
    if (
        not listing.advertiser
        or listing.advertiser.casefold()
        == "particular"
    )
]
    validate_email_settings()

    if not HEADER_IMAGE_PATH.is_file():
        raise FileNotFoundError(
            f"No se encuentra la cabecera: "
            f"{HEADER_IMAGE_PATH}"
        )

    # Primer nivel: portal.
    # Segundo nivel: zona.
    grouped_listings = defaultdict(
        lambda: defaultdict(list)
    )

    for listing in visible_listings:
        portal = (
            listing.portal
            or "Otro portal"
        )

        zone = (
            listing.zone
            or "Zona no identificada"
        )

        grouped_listings[portal][zone].append(
            listing
        )

    text_lines = [
        (
            f"Se han encontrado "
            f"{total_listings} pisos nuevos."
        ),
        f"Con agencia: {agency_count}",
        f"Particulares: {particular_count}",
        f"No identificados: {unknown_count}",
        "",
    ]
    text_lines.append(
    "DETALLE DE PARTICULARES Y NO IDENTIFICADOS"
    )
    text_lines.append(
        "=" * 40
    )
    text_lines.append("")
    html_portals = []

    for portal, zones in grouped_listings.items():
        html_zones = []

        portal_color = get_portal_color(
            portal
        )

        text_lines.append(
            portal.upper()
        )

        text_lines.append(
            "=" * 30
        )

        for zone, zone_listings in zones.items():
            number = len(zone_listings)

            text_lines.append(
                f"📍 {zone}: {number} anuncios"
            )

            html_properties = []

            for index, listing in enumerate(
                zone_listings,
                start=1,
            ):
                price = format_price(
                    listing.price
                )

                title = (
                    listing.title
                    or f"Inmueble {index}"
                )

                advertiser = (
                    get_advertiser_text(
                        listing
                    )
                )

                text_lines.extend([
                    title,
                    f"Precio: {price}",
                    f"Anunciante: {advertiser}",
                    listing.url,
                    "",
                ])

                html_properties.append(
                    f"""
                    <div style="
                        padding: 16px 0;
                        border-bottom: 1px solid #dddddd;
                    ">
                        <table
                            role="presentation"
                            width="100%"
                            cellspacing="0"
                            cellpadding="0"
                            border="0"
                            style="
                                width: 100%;
                                border-collapse: collapse;
                            "
                        >
                            <tr>
                                <td
                                    valign="top"
                                    style="
                                        width: 70%;
                                        padding-right: 20px;
                                    "
                                >
                                    <div style="
                                        font-size: 16px;
                                        margin-bottom: 6px;
                                    ">
                                        <strong>
                                            {escape(title)}
                                        </strong>
                                    </div>

                                    <div style="
                                        color: #777777;
                                        font-size: 14px;
                                        margin-bottom: 12px;
                                    ">
                                        {escape(price)}
                                    </div>

                                    <a
                                        href="{
                                            escape(
                                                listing.url,
                                                quote=True,
                                            )
                                        }"
                                        style="
                                            display: inline-block;
                                            background-color: {
                                                portal_color
                                            };
                                            color: #ffffff;
                                            padding: 9px 14px;
                                            text-decoration: none;
                                            border-radius: 5px;
                                            font-weight: bold;
                                        "
                                    >
                                        Ver anuncio
                                    </a>
                                </td>

                                <td
                                    valign="top"
                                    align="right"
                                    style="
                                        width: 30%;
                                        padding-left: 10px;
                                    "
                                >
                                    <div style="
                                        color: #888888;
                                        font-size: 11px;
                                        margin-bottom: 5px;
                                        text-transform: uppercase;
                                        letter-spacing: 0.5px;
                                    ">
                                        Anunciante
                                    </div>

                                    <div style="
                                        font-size: 14px;
                                        font-weight: bold;
                                    ">
                                        {
                                            escape(
                                                advertiser
                                            )
                                        }
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>
                    """
                )

            singular_or_plural = (
                "anuncio nuevo"
                if number == 1
                else "anuncios nuevos"
            )

            html_zones.append(
                f"""
                <div style="
                    border: 1px solid #dddddd;
                    border-radius: 8px;
                    padding: 18px;
                    margin-bottom: 18px;
                ">
                    <h3 style="
                        margin-top: 0;
                        margin-bottom: 8px;
                    ">
                        📍 {escape(zone)}
                    </h3>

                    <p style="
                        margin-top: 0;
                        color: #777777;
                    ">
                        {number} {singular_or_plural}
                    </p>

                    {''.join(html_properties)}
                </div>
                """
            )

        html_portals.append(
            f"""
            <h2 style="
                color: {portal_color};
                margin-top: 28px;
                margin-bottom: 14px;
            ">
                {escape(portal)}
            </h2>

            {''.join(html_zones)}
            """
        )

    message = EmailMessage()

    message["Subject"] = (
        f"{total_listings} pisos nuevos - "
        f"{particular_count} particulares"
    )

    message["From"] = settings.smtp_user
    message["To"] = settings.notification_email

    message.set_content(
        "\n".join(text_lines)
    )

    message.add_alternative(
        f"""
        <html>
            <body style="
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: auto;
                color: #222222;
            ">
                <div style="
                    margin-bottom: 24px;
                ">
                    <img
                        src="cid:{HEADER_IMAGE_CID}"
                        alt="Radar Inmobiliario"
                        width="700"
                        style="
                            display: block;
                            width: 100%;
                            max-width: 700px;
                            height: auto;
                            border: 0;
                            border-radius: 10px;
                        "
                    >
                </div>

                <div style="
                    margin-bottom: 28px;
                ">
                    <p style="
                        font-size: 17px;
                        margin-bottom: 14px;
                    ">
                        Se han encontrado
                        <strong>
                            {total_listings}
                        </strong>
                        pisos nuevos.
                    </p>

                    <table
                        role="presentation"
                        width="100%"
                        cellspacing="0"
                        cellpadding="0"
                        border="0"
                        style="
                            width: 100%;
                            border-collapse: separate;
                            border-spacing: 8px 0;
                        "
                    >
                        <tr>
                            <td
                                align="center"
                                style="
                                    width: 33%;
                                    padding: 14px;
                                    border: 1px solid #444444;
                                    border-radius: 8px;
                                "
                            >
                                <div style="
                                    font-size: 24px;
                                    font-weight: bold;
                                ">
                                    {agency_count}
                                </div>

                                <div style="
                                    font-size: 13px;
                                    color: #999999;
                                    margin-top: 4px;
                                ">
                                    Con agencia
                                </div>
                            </td>

                            <td
                                align="center"
                                style="
                                    width: 33%;
                                    padding: 14px;
                                    border: 1px solid #444444;
                                    border-radius: 8px;
                                "
                            >
                                <div style="
                                    font-size: 24px;
                                    font-weight: bold;
                                ">
                                    {particular_count}
                                </div>

                                <div style="
                                    font-size: 13px;
                                    color: #999999;
                                    margin-top: 4px;
                                ">
                                    Particulares
                                </div>
                            </td>

                            <td
                                align="center"
                                style="
                                    width: 33%;
                                    padding: 14px;
                                    border: 1px solid #444444;
                                    border-radius: 8px;
                                "
                            >
                                <div style="
                                    font-size: 24px;
                                    font-weight: bold;
                                ">
                                    {unknown_count}
                                </div>

                                <div style="
                                    font-size: 13px;
                                    color: #999999;
                                    margin-top: 4px;
                                ">
                                    No identificados
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>
                <h2 style="
                    margin-top: 30px;
                    margin-bottom: 18px;
                ">
                    Particulares y no identificados
                </h2>
                {''.join(html_portals)}

                <p style="
                    color: #777777;
                    margin-top: 30px;
                    font-size: 12px;
                ">
                    Mensaje generado automáticamente.
                </p>
            </body>
        </html>
        """,
        subtype="html",
    )

    html_part = message.get_payload()[-1]

    html_part.add_related(
        HEADER_IMAGE_PATH.read_bytes(),
        maintype="image",
        subtype="jpeg",
        cid=f"<{HEADER_IMAGE_CID}>",
        filename=HEADER_IMAGE_PATH.name,
        disposition="inline",
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
    ) as server:
        server.starttls(
            context=context
        )

        server.login(
            settings.smtp_user,
            settings.smtp_password,
        )

        server.send_message(
            message
        )