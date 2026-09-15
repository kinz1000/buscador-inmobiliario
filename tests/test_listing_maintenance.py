from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.models import Base, PropertyListing
from src.services import listing_maintenance


# =========================================================
# BASE DE DATOS DE TEST
# =========================================================


@pytest.fixture
def test_session_local(
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path / "maintenance_test.db"
    )

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    Base.metadata.create_all(
        bind=engine
    )

    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "SessionLocal",
        TestSessionLocal,
    )

    yield TestSessionLocal

    engine.dispose()


# =========================================================
# HELPERS
# =========================================================


def create_listing(
    session_local,
    *,
    portal="Fotocasa",
    advertiser="Agencia Test",
    days_old=30,
    check_count=0,
    external_id="123",
):
    now = datetime.now(timezone.utc)

    listing = PropertyListing(
        portal=portal,
        external_id=external_id,
        title="Piso de prueba",
        price=500_000,
        zone="Goya",
        advertiser=advertiser,
        url=(
            "https://example.com/"
            f"{portal}/{external_id}"
        ),
        detected_at=(
            now - timedelta(days=days_old)
        ),
        retention_started_at=(
            now - timedelta(days=days_old)
        ),
        advertiser_check_count=check_count,
    )

    with session_local() as session:
        session.add(listing)
        session.commit()

        listing_id = listing.id

    return listing_id


def get_listing(
    session_local,
    listing_id,
):
    with session_local() as session:
        return session.scalar(
            select(PropertyListing).where(
                PropertyListing.id
                == listing_id
            )
        )


# =========================================================
# DÍAS DE REVISIÓN
# =========================================================


@pytest.mark.parametrize(
    (
        "days_old",
        "check_count",
        "expected_stage",
    ),
    [
        (29, 0, None),
        (30, 0, 1),
        (44, 0, 1),
        (45, 1, 2),
        (59, 2, None),
        (60, 2, 3),
        (74, 3, None),
        (75, 3, 4),
        (89, 4, None),
        (90, 4, 5),
    ],
)
def test_get_due_review_stage(
    days_old,
    check_count,
    expected_stage,
):
    now = datetime.now(timezone.utc)

    listing = PropertyListing(
        portal="Fotocasa",
        external_id="123",
        title="Piso",
        price=500_000,
        zone="Goya",
        advertiser="Agencia",
        url="https://example.com/123",
        detected_at=(
            now - timedelta(days=days_old)
        ),
        retention_started_at=now,
        advertiser_check_count=check_count,
    )

    result = (
        listing_maintenance
        .get_due_review_stage(
            listing,
            now,
        )
    )

    assert result == expected_stage


# =========================================================
# BOT APAGADO VARIOS DÍAS
# =========================================================


def test_review_salta_directamente_a_etapa_actual():
    now = datetime.now(timezone.utc)

    listing = PropertyListing(
        portal="Fotocasa",
        external_id="123",
        title="Piso",
        price=500_000,
        zone="Goya",
        advertiser="Agencia",
        url="https://example.com/123",
        detected_at=(
            now - timedelta(days=62)
        ),
        retention_started_at=now,
        advertiser_check_count=0,
    )

    result = (
        listing_maintenance
        .get_due_review_stage(
            listing,
            now,
        )
    )

    # Día 62:
    # salta directamente a la revisión
    # correspondiente al día 60.
    assert result == 3


# =========================================================
# AGENCIA -> MISMA AGENCIA
# =========================================================


def test_agencia_sigue_siendo_agencia(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        days_old=31,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: "Agencia Test",
    )

    send_mock = []

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        lambda listings: send_mock.append(
            listings
        ),
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0

    assert (
        listing.advertiser
        == "Agencia Test"
    )

    assert (
        listing.advertiser_check_count
        == 1
    )

    assert (
        listing.last_advertiser_check_at
        is not None
    )

    assert send_mock == []


# =========================================================
# AGENCIA A -> AGENCIA B
# =========================================================


def test_cambio_de_agencia_no_es_relevante(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Agencia A",
        days_old=46,
        check_count=1,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: "Agencia B",
    )

    send_mock = []

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        lambda listings: send_mock.append(
            listings
        ),
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0

    # Conservamos la agencia original.
    assert (
        listing.advertiser
        == "Agencia A"
    )

    # Pero sí registramos que se hizo
    # la revisión del día 45.
    assert (
        listing.advertiser_check_count
        == 2
    )

    assert send_mock == []


# =========================================================
# AGENCIA -> PARTICULAR
# =========================================================


def test_agencia_pasa_a_particular(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Agencia Test",
        days_old=31,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: "Particular",
    )

    emails_sent = []

    def fake_send_listing_summary(
        listings,
    ):
        emails_sent.extend(
            listing.external_id
            for listing in listings
        )

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        fake_send_listing_summary,
    )

    before = datetime.now(timezone.utc)

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    after = datetime.now(timezone.utc)

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 1

    assert (
        listing.advertiser
        == "Particular"
    )

    assert (
        listing.advertiser_check_count
        == 1
    )

    retention_started_at = (
        listing.retention_started_at
    )

    if retention_started_at.tzinfo is None:
        retention_started_at = (
            retention_started_at.replace(
                tzinfo=timezone.utc
            )
        )

    assert (
        before
        <= retention_started_at
        <= after
    )

    assert emails_sent == ["123"]


# =========================================================
# AGENCIA -> NO IDENTIFICADO
# =========================================================


def test_agencia_pasa_a_no_identificado(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Agencia Test",
        days_old=61,
        check_count=2,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: None,
    )

    emails_sent = []

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        lambda listings: emails_sent.extend(
            listings
        ),
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 1

    assert listing.advertiser is None

    assert (
        listing.advertiser_check_count
        == 3
    )

    assert len(emails_sent) == 1


# =========================================================
# FALLO HTTP
# =========================================================


def test_fallo_http_no_consume_revision(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Agencia Test",
        days_old=31,
        check_count=0,
    )

    def raise_error(listing):
        raise requests.RequestException(
            "Error de red"
        )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        raise_error,
    )

    send_mock = []

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        lambda listings: send_mock.append(
            listings
        ),
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0

    assert (
        listing.advertiser
        == "Agencia Test"
    )

    # MUY importante:
    # el fallo técnico no consume
    # la revisión.
    assert (
        listing.advertiser_check_count
        == 0
    )

    assert (
        listing.last_advertiser_check_at
        is None
    )

    assert send_mock == []


# =========================================================
# FALLO SMTP
# =========================================================


def test_fallo_smtp_hace_rollback(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Agencia Test",
        days_old=31,
        check_count=0,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: "Particular",
    )

    def smtp_error(listings):
        raise RuntimeError(
            "SMTP no disponible"
        )

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        smtp_error,
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0

    # El rollback debe dejar el anuncio
    # exactamente como estaba.
    assert (
        listing.advertiser
        == "Agencia Test"
    )

    assert (
        listing.advertiser_check_count
        == 0
    )

    assert (
        listing.last_advertiser_check_at
        is None
    )


# =========================================================
# PARTICULAR NO SE REVISA
# =========================================================


def test_particular_no_se_revisa(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Particular",
        days_old=70,
    )

    calls = []

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: calls.append(
            listing
        ),
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0
    assert calls == []

    assert (
        listing.advertiser_check_count
        == 0
    )


# =========================================================
# IDEALISTA / MILANUNCIOS NO SE REVISAN
# =========================================================


@pytest.mark.parametrize(
    "portal",
    [
        "Idealista",
        "Milanuncios",
    ],
)
def test_portales_sin_revision(
    portal,
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        portal=portal,
        advertiser="Agencia Test",
        days_old=80,
        external_id=portal,
    )

    calls = []

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: calls.append(
            listing
        ),
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0
    assert calls == []

    assert (
        listing.advertiser_check_count
        == 0
    )


# =========================================================
# DÍA 90
# =========================================================


def test_revision_final_dia_90(
    test_session_local,
    monkeypatch,
):
    listing_id = create_listing(
        test_session_local,
        advertiser="Agencia Test",
        days_old=91,
        check_count=4,
    )

    monkeypatch.setattr(
        listing_maintenance,
        "fetch_current_advertiser",
        lambda listing: "Agencia Test",
    )

    monkeypatch.setattr(
        listing_maintenance,
        "send_listing_summary",
        lambda listings: None,
    )

    changed = (
        listing_maintenance
        .review_agency_listings()
    )

    listing = get_listing(
        test_session_local,
        listing_id,
    )

    assert changed == 0

    assert (
        listing.advertiser
        == "Agencia Test"
    )

    assert (
        listing.advertiser_check_count
        == 5
    )