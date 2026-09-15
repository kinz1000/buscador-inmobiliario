from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.models import (
    Base,
    ParserHealthAlert,
)
from src.monitoring import parser_health


@pytest.fixture
def temp_health_database(
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path
        / "test_parser_health.db"
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

    monkeypatch.setattr(
        parser_health,
        "SessionLocal",
        TestingSessionLocal,
    )

    yield TestingSessionLocal

    engine.dispose()


def test_first_parser_issue_sends_alert(
    temp_health_database,
):
    result = (
        parser_health.should_send_parser_alert(
            portal="Fotocasa",
            issue_code="no_links_found",
            message="0 enlaces encontrados",
        )
    )

    assert result is True

    with temp_health_database() as session:
        alert = session.scalar(
            select(ParserHealthAlert)
        )

        assert alert is not None
        assert alert.portal == "Fotocasa"
        assert (
            alert.issue_code
            == "no_links_found"
        )
        assert alert.last_alerted_at is not None


def test_repeated_issue_inside_cooldown_does_not_send(
    temp_health_database,
):
    first = (
        parser_health.should_send_parser_alert(
            portal="Habitaclia",
            issue_code="no_links_found",
            message="Primer fallo",
        )
    )

    second = (
        parser_health.should_send_parser_alert(
            portal="Habitaclia",
            issue_code="no_links_found",
            message="Segundo fallo",
        )
    )

    assert first is True
    assert second is False

    with temp_health_database() as session:
        alerts = session.scalars(
            select(ParserHealthAlert)
        ).all()

        assert len(alerts) == 1


def test_issue_after_cooldown_sends_again(
    temp_health_database,
):
    first = (
        parser_health.should_send_parser_alert(
            portal="Pisos.com",
            issue_code="no_links_found",
            message="Primer fallo",
        )
    )

    assert first is True

    with temp_health_database() as session:
        alert = session.scalar(
            select(ParserHealthAlert)
        )

        alert.last_alerted_at = (
            datetime.now(timezone.utc)
            - timedelta(hours=13)
        )

        session.commit()

    second = (
        parser_health.should_send_parser_alert(
            portal="Pisos.com",
            issue_code="no_links_found",
            message="Sigue fallando",
        )
    )

    assert second is True


def test_same_issue_different_portals_are_independent(
    temp_health_database,
):
    fotocasa = (
        parser_health.should_send_parser_alert(
            portal="Fotocasa",
            issue_code="no_links_found",
            message="Fallo Fotocasa",
        )
    )

    idealista = (
        parser_health.should_send_parser_alert(
            portal="Idealista",
            issue_code="no_links_found",
            message="Fallo Idealista",
        )
    )

    assert fotocasa is True
    assert idealista is True

    with temp_health_database() as session:
        alerts = session.scalars(
            select(ParserHealthAlert)
        ).all()

        assert len(alerts) == 2

def test_partial_alert_requires_minimum_items():
    assert (
        parser_health.should_alert_for_missing_data(
            total_items=1,
            missing_items=1,
        )
        is False
    )

    assert (
        parser_health.should_alert_for_missing_data(
            total_items=2,
            missing_items=2,
        )
        is False
    )


def test_partial_alert_triggers_at_eighty_percent():
    assert (
        parser_health.should_alert_for_missing_data(
            total_items=5,
            missing_items=4,
        )
        is True
    )


def test_partial_alert_does_not_trigger_below_eighty_percent():
    assert (
        parser_health.should_alert_for_missing_data(
            total_items=10,
            missing_items=7,
        )
        is False
    )


def test_partial_alert_triggers_for_total_failure():
    assert (
        parser_health.should_alert_for_missing_data(
            total_items=3,
            missing_items=3,
        )
        is True
    )