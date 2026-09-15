from types import SimpleNamespace
from unittest.mock import patch

from src import main as main_module
from src.models import PropertyListing
from src.parsers.habitaclia_parser import (
    extract_habitaclia_id,
    extract_habitaclia_links,
)
from src.parsers.listing_details import (
    extract_habitaclia_listing_details,
)


TEST_URL = (
    "https://www.fotocasa.es/es/comprar/"
    "vivienda/madrid/123456789/d"
)


class FakeParser:
    portal = "Fotocasa"

    def extract_links(
        self,
        email,
    ) -> list[str]:
        return [TEST_URL]

    def extract_id(
        self,
        url: str,
    ) -> str:
        return "123456789"


class BrokenParser:
    portal = "Idealista"

    def extract_links(
        self,
        email,
    ) -> list[str]:
        raise RuntimeError(
            "Error simulado del parser"
        )

    def extract_id(
        self,
        url: str,
    ) -> str:
        return "123"


class EmptyParser:
    portal = "Milanuncios"

    def extract_links(
        self,
        email,
    ) -> list[str]:
        return []

    def extract_id(
        self,
        url: str,
    ) -> str | None:
        return None


def create_fake_email(
    uid: str = "100",
):
    return SimpleNamespace(
        uid=uid,
        from_="alertas@fotocasa.es",
        subject="Nuevo inmueble en Fotocasa",
        text="Contenido del correo",
        html="",
    )


def create_test_listing() -> PropertyListing:
    return PropertyListing(
        portal="Fotocasa",
        external_id="123456789",
        title=(
            "Piso en venta en Guindalera"
        ),
        price=250000,
        zone="Guindalera",
        url=TEST_URL,
        raw_data="Contenido de prueba",
    )


def test_process_duplicate_email() -> None:
    email = create_fake_email()
    new_listings = {}

    with (
        patch.object(
            main_module,
            "get_portal_parser",
            return_value=FakeParser(),
        ),
        patch.object(
            main_module,
            "listing_exists",
            return_value=True,
        ),
    ):
        result = main_module.process_email(
            email,
            new_listings,
        )

    assert result is True
    assert new_listings == {}


def test_process_email_handles_parser_error() -> None:
    email = create_fake_email()
    new_listings = {}

    with patch.object(
        main_module,
        "get_portal_parser",
        return_value=BrokenParser(),
    ):
        result = main_module.process_email(
            email,
            new_listings,
        )

    assert result is False
    assert new_listings == {}


def test_portal_email_without_links_is_not_processed() -> None:
    email = create_fake_email()
    new_listings = {}

    with (
        patch.object(
            main_module,
            "get_portal_parser",
            return_value=EmptyParser(),
        ),
        patch.object(
            main_module,
            "should_send_parser_alert",
            return_value=False,
        ),
    ):
        result = main_module.process_email(
            email,
            new_listings,
        )

    assert result is False
    assert new_listings == {}


def test_parser_alert_is_sent_when_no_links() -> None:
    email = create_fake_email()
    new_listings = {}

    with (
        patch.object(
            main_module,
            "get_portal_parser",
            return_value=EmptyParser(),
        ),
        patch.object(
            main_module,
            "should_send_parser_alert",
            return_value=True,
        ),
        patch.object(
            main_module,
            "send_parser_health_alert",
        ) as send_alert,
    ):
        result = main_module.process_email(
            email,
            new_listings,
        )

    assert result is False
    assert new_listings == {}

    send_alert.assert_called_once()








    
def test_process_new_fotocasa_listing() -> None:
    email = create_fake_email()
    new_listings = {}

    with (
        patch.object(
            main_module,
            "get_portal_parser",
            return_value=FakeParser(),
        ),
        patch.object(
            main_module,
            "listing_exists",
            return_value=False,
        ),
        patch.object(
            main_module,
            "extract_price_for_listing",
            return_value=250000,
        ),
        patch.object(
            main_module,
            "extract_zone",
            return_value="Guindalera",
        ),
        patch.object(
            main_module,
            "extract_title_for_listing",
            return_value=(
                "Piso en venta en Guindalera"
            ),
        ),
    ):
        result = main_module.process_email(
            email,
            new_listings,
        )

    assert result is True
    assert TEST_URL in new_listings

    listing = new_listings[TEST_URL]

    assert listing.portal == "Fotocasa"
    assert listing.external_id == "123456789"
    assert listing.price == 250000
    assert listing.zone == "Guindalera"


def test_run_once_marks_duplicate_email() -> None:
    email = create_fake_email(
        uid="101"
    )

    with (
        patch.object(
            main_module,
            "fetch_unread_emails",
            return_value=[email],
        ),
        patch.object(
            main_module,
            "process_email",
            return_value=True,
        ),
        patch.object(
            main_module,
            "mark_processed_emails",
        ) as mark_processed,
        patch.object(
            main_module,
            "send_listing_summary",
        ) as send_summary,
    ):
        main_module.run_once()

    mark_processed.assert_called_once_with({
        "101"
    })

    send_summary.assert_not_called()


def test_run_once_continues_after_failed_email() -> None:
    failed_email = create_fake_email(
        uid="201"
    )

    correct_email = create_fake_email(
        uid="202"
    )

    with (
        patch.object(
            main_module,
            "fetch_unread_emails",
            return_value=[
                failed_email,
                correct_email,
            ],
        ),
        patch.object(
            main_module,
            "process_email",
            side_effect=[
                False,
                True,
            ],
        ) as process_email,
        patch.object(
            main_module,
            "mark_processed_emails",
        ) as mark_processed,
        patch.object(
            main_module,
            "send_listing_summary",
        ),
    ):
        main_module.run_once()

    assert process_email.call_count == 2

    mark_processed.assert_called_once_with({
        "202"
    })


def test_smtp_failure_keeps_email_unread() -> None:
    email = create_fake_email(
        uid="301"
    )

    def add_new_listing(
        received_email,
        new_listings,
    ) -> bool:
        listing = create_test_listing()

        new_listings[listing.url] = listing

        return True

    with (
        patch.object(
            main_module,
            "fetch_unread_emails",
            return_value=[email],
        ),
        patch.object(
            main_module,
            "process_email",
            side_effect=add_new_listing,
        ),
        patch.object(
            main_module,
            "send_listing_summary",
            side_effect=RuntimeError(
                "Error SMTP simulado"
            ),
        ),
        patch.object(
            main_module,
            "save_listing",
        ) as save_listing,
        patch.object(
            main_module,
            "mark_processed_emails",
        ) as mark_processed,
    ):
        main_module.run_once()

    save_listing.assert_not_called()
    mark_processed.assert_not_called()


def test_extract_habitaclia_real_alert_links() -> None:
    new_image_url = (
        "https://www.habitaclia.com/i58574000000052/"
        "28178429/express123/alertas/email/lo-34/"
        "20260904-e_nuevo_email_img.htm"
    )

    new_title_url = (
        "https://www.habitaclia.com/i58574000000052/"
        "28178429/express123/alertas/email/lo-34/"
        "20260904-e_nuevo_email_titulo.htm"
    )

    opportunity_url = (
        "https://www.habitaclia.com/i22332000000052/"
        "28178429/express123/alertas/email/lo-36/"
        "20260904-e_oportunidad_email_titulo.htm"
    )

    promoted_url = (
        "https://www.habitaclia.com/p54568004585652/"
        "28178429/express123/alertas/email/lo-38/"
        "20260904-e_ondestacada_email_titulo.htm"
    )

    email = SimpleNamespace(
        html=(
            f'<a href="{new_image_url}">Imagen</a>'
            f'<a href="{new_title_url}">Título</a>'
            f'<a href="{opportunity_url}">Oportunidad</a>'
            f'<a href="{promoted_url}">Destacado</a>'
        ),
        text="",
    )

    links = extract_habitaclia_links(email)

    assert links == [new_title_url]
    assert (
        extract_habitaclia_id(links[0])
        == "58574000000052"
    )


def test_extract_habitaclia_public_link() -> None:
    public_url = (
        "https://www.habitaclia.com/"
        "comprar-piso-en-madrid-i123456.htm"
    )

    email = SimpleNamespace(
        html="",
        text=public_url,
    )

    assert extract_habitaclia_links(email) == [
        public_url
    ]
    assert (
        extract_habitaclia_id(public_url)
        == "123456"
    )


def test_extract_habitaclia_listing_details() -> None:
    external_id = "15240003798576"
    listing_url = (
        "https://www.habitaclia.com/"
        f"i{external_id}/28178429/express123/"
        "alertas/email/lo-34/"
        "20260904-e_nuevo_email_titulo.htm"
    )

    html = f"""
        <a href="{listing_url}">
            <span>1.600.000 €</span>
        </a>
        <a href="{listing_url}">
            <p>
                Piso en Madrid - Goya
                (Barrio de Salamanca)
                <br>
                <font>C. del Duque de Sesto</font>
            </p>
        </a>
    """

    title, price, zone = (
        extract_habitaclia_listing_details(
            html,
            external_id,
        )
    )

    assert title == "Piso en venta en Goya"
    assert price == 1_600_000
    assert zone == "Goya"
