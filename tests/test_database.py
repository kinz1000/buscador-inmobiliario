from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src import pipeline
from src.models import Base, PropertyListing


@pytest.fixture
def temp_database(
    tmp_path,
    monkeypatch,
):
    """
    Crea una SQLite exclusiva para cada test.

    Nunca utiliza data/inmuebles.db.
    """

    database_path = (
        tmp_path
        / "test_inmuebles.db"
    )

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={
            "check_same_thread": False,
        },
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(
        bind=engine
    )

    # pipeline.py importa SessionLocal directamente:
    #
    # from src.database import SessionLocal
    #
    # Por tanto hay que sustituir exactamente
    # pipeline.SessionLocal durante los tests.
    monkeypatch.setattr(
        pipeline,
        "SessionLocal",
        TestingSessionLocal,
    )

    yield TestingSessionLocal

    engine.dispose()


def create_listing(
    *,
    portal: str = "Fotocasa",
    external_id: str = "123456789",
    url: str = (
        "https://www.fotocasa.es/"
        "es/comprar/vivienda/"
        "madrid/123456789/d"
    ),
    zone: str = "Guindalera",
    detected_at: datetime | None = None,
) -> PropertyListing:
    data = {
        "portal": portal,
        "external_id": external_id,
        "title": "Piso en venta en Guindalera",
        "price": 500000,
        "zone": zone,
        "advertiser": "Particular",
        "url": url,
        "raw_data": "correo de prueba",
    }

    if detected_at is not None:
        data["detected_at"] = detected_at

    return PropertyListing(
        **data
    )


def test_save_listing_guarda_anuncio(
    temp_database,
):
    listing = create_listing()

    result = pipeline.save_listing(
        listing
    )

    assert result is True

    with temp_database() as session:
        stored_listing = session.scalar(
            select(PropertyListing)
        )

        assert stored_listing is not None
        assert (
            stored_listing.portal
            == "Fotocasa"
        )
        assert (
            stored_listing.external_id
            == "123456789"
        )
        assert (
            stored_listing.price
            == 500000
        )


def test_save_listing_normaliza_url(
    temp_database,
):
    listing = create_listing(
        url=(
            "http://fotocasa.es/"
            "es/comprar/vivienda/"
            "madrid/123456789/d/"
            "?utm_source=email"
            "#contacto"
        )
    )

    assert (
        pipeline.save_listing(listing)
        is True
    )

    with temp_database() as session:
        stored_listing = session.scalar(
            select(PropertyListing)
        )

        assert stored_listing.url == (
            "https://www.fotocasa.es/"
            "es/comprar/vivienda/"
            "madrid/123456789/d"
        )


def test_listing_exists_por_url_normalizada(
    temp_database,
):
    listing = create_listing(
        url=(
            "https://www.fotocasa.es/"
            "es/comprar/vivienda/"
            "madrid/123456789/d"
        )
    )

    assert (
        pipeline.save_listing(listing)
        is True
    )

    exists = pipeline.listing_exists(
        url=(
            "http://fotocasa.es/"
            "es/comprar/vivienda/"
            "madrid/123456789/d/"
            "?utm_source=email"
        ),
        portal="Fotocasa",
        external_id=None,
    )

    assert exists is True


def test_listing_exists_por_portal_y_external_id(
    temp_database,
):
    listing = create_listing(
        portal="Fotocasa",
        external_id="999999999",
    )

    assert (
        pipeline.save_listing(listing)
        is True
    )

    exists = pipeline.listing_exists(
        url=(
            "https://www.fotocasa.es/"
            "otra-url-completamente-distinta"
        ),
        portal="Fotocasa",
        external_id="999999999",
    )

    assert exists is True


def test_external_id_igual_en_otro_portal_no_es_duplicado(
    temp_database,
):
    listing = create_listing(
        portal="Fotocasa",
        external_id="777777777",
    )

    assert (
        pipeline.save_listing(listing)
        is True
    )

    exists = pipeline.listing_exists(
        url=(
            "https://www.idealista.com/"
            "inmueble/777777777"
        ),
        portal="Idealista",
        external_id="777777777",
    )

    assert exists is False


def test_mismo_anuncio_no_puede_guardarse_dos_veces(
    temp_database,
):
    first_listing = create_listing(
        portal="Fotocasa",
        external_id="555555555",
        url=(
            "https://www.fotocasa.es/"
            "es/comprar/vivienda/"
            "madrid/555555555/d"
        ),
    )

    second_listing = create_listing(
        portal="Fotocasa",
        external_id="555555555",
        url=(
            "https://www.fotocasa.es/"
            "es/comprar/vivienda/"
            "madrid/otra-url/d"
        ),
    )

    first_result = pipeline.save_listing(
        first_listing
    )

    second_result = pipeline.save_listing(
        second_listing
    )

    assert first_result is True
    assert second_result is False

    with temp_database() as session:
        listings = session.scalars(
            select(PropertyListing)
        ).all()

        assert len(listings) == 1


def test_delete_expired_listings_elimina_particular_antiguo(
    temp_database,
):
    old_listing = create_listing(
        external_id="OLD001",
        url=(
            "https://www.fotocasa.es/"
            "old-listing"
        ),
        detected_at=(
            datetime.now(timezone.utc)
            - timedelta(days=31)
        ),
    )

    old_listing.advertiser = "Particular"

    old_listing.retention_started_at = (
        datetime.now(timezone.utc)
        - timedelta(days=31)
    )

    url = old_listing.url
    portal = old_listing.portal
    external_id = old_listing.external_id

    assert (
        pipeline.save_listing(
            old_listing
        )
        is True
    )

    deleted = (
        pipeline.delete_expired_listings()
    )

    assert deleted == 1

    assert (
        pipeline.listing_exists(
            url,
            portal,
            external_id,
        )
        is False
    )


def test_delete_expired_listings_conserva_particular_reciente(
    temp_database,
):
    recent_listing = create_listing(
        external_id="NEW001",
        url=(
            "https://www.fotocasa.es/"
            "recent-listing"
        ),
        detected_at=(
            datetime.now(timezone.utc)
            - timedelta(days=10)
        ),
    )

    recent_listing.advertiser = "Particular"

    recent_listing.retention_started_at = (
        datetime.now(timezone.utc)
        - timedelta(days=10)
    )

    url = recent_listing.url
    portal = recent_listing.portal
    external_id = recent_listing.external_id

    assert (
        pipeline.save_listing(
            recent_listing
        )
        is True
    )

    deleted = (
        pipeline.delete_expired_listings()
    )

    assert deleted == 0

    assert (
        pipeline.listing_exists(
            url,
            portal,
            external_id,
        )
        is True
    )


def test_delete_expired_listings_elimina_idealista_a_7_dias(
    temp_database,
):
    listing = create_listing(
        portal="Idealista",
        external_id="IDE001",
        url="https://www.idealista.com/inmueble/IDE001",
        detected_at=(
            datetime.now(timezone.utc)
            - timedelta(days=8)
        ),
    )

    assert pipeline.save_listing(listing) is True

    deleted = pipeline.delete_expired_listings()

    assert deleted == 1


def test_delete_expired_listings_no_elimina_agencia_antes_revision_final(
    temp_database,
):
    listing = create_listing(
        portal="Fotocasa",
        external_id="AGE001",
        url="https://www.fotocasa.es/AGE001",
        detected_at=(
            datetime.now(timezone.utc)
            - timedelta(days=91)
        ),
    )

    listing.advertiser = "Agencia Test"
    listing.advertiser_check_count = 4

    assert pipeline.save_listing(listing) is True

    deleted = pipeline.delete_expired_listings()

    assert deleted == 0


def test_delete_expired_listings_elimina_agencia_tras_revision_final(
    temp_database,
):
    listing = create_listing(
        portal="Fotocasa",
        external_id="AGE002",
        url="https://www.fotocasa.es/AGE002",
        detected_at=(
            datetime.now(timezone.utc)
            - timedelta(days=91)
        ),
    )

    listing.advertiser = "Agencia Test"
    listing.advertiser_check_count = 5

    assert pipeline.save_listing(listing) is True

    deleted = pipeline.delete_expired_listings()

    assert deleted == 1
@pytest.mark.parametrize(
    "zone",
    [
        "Guindalera",
        "Fuente del Berro",
        "Lista",
        "Goya",
    ],
)
def test_is_allowed_zone_acepta_zonas_configuradas(
    zone,
):
    assert (
        pipeline.is_allowed_zone(zone)
        is True
    )


@pytest.mark.parametrize(
    "zone",
    [
        "Chamberí",
        "Lavapiés",
        "Vallecas",
        "Madrid Capital",
        None,
        "",
    ],
)
def test_is_allowed_zone_rechaza_otras_zonas(
    zone,
):
    assert (
        pipeline.is_allowed_zone(zone)
        is False
    )


def test_process_listing_rechaza_zona_no_permitida(
    temp_database,
):
    listing = create_listing(
        external_id="ZONE001",
        url=(
            "https://www.fotocasa.es/"
            "zona-no-permitida"
        ),
        zone="Chamberí",
    )

    result = pipeline.process_listing(
        listing
    )

    assert result == "rejected_zone"

    with temp_database() as session:
        listings = session.scalars(
            select(PropertyListing)
        ).all()

        assert listings == []


def test_process_listing_guarda_zona_permitida(
    temp_database,
):
    listing = create_listing(
        external_id="ZONE002",
        url=(
            "https://www.fotocasa.es/"
            "guindalera-test"
        ),
        zone="Guindalera",
    )

    result = pipeline.process_listing(
        listing
    )

    assert result == "saved"

    with temp_database() as session:
        listings = session.scalars(
            select(PropertyListing)
        ).all()

        assert len(listings) == 1