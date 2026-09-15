from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy import select

from src.database import SessionLocal
from src.models import ParserHealthAlert


ALERT_COOLDOWN_HOURS = 12
MIN_ITEMS_FOR_PARTIAL_ALERT = 3
FAILURE_RATIO_THRESHOLD = 0.8

def should_send_parser_alert(
    portal: str,
    issue_code: str,
    message: str,
) -> bool:
    """
    Registra un problema detectado en un parser
    y decide si corresponde enviar una alerta.

    El cooldown evita recibir el mismo aviso
    cada 5 minutos.
    """

    now = datetime.now(
        timezone.utc
    )

    statement = select(
        ParserHealthAlert
    ).where(
        ParserHealthAlert.portal
        == portal,
        ParserHealthAlert.issue_code
        == issue_code,
    )

    with SessionLocal() as session:
        alert = session.scalar(
            statement
        )

        if alert is None:
            alert = ParserHealthAlert(
                portal=portal,
                issue_code=issue_code,
                message=message,
                first_seen_at=now,
                last_seen_at=now,
                last_alerted_at=now,
            )

            session.add(alert)
            session.commit()

            return True

        alert.last_seen_at = now
        alert.message = message

        last_alerted_at = (
            alert.last_alerted_at
        )

        if last_alerted_at is None:
            alert.last_alerted_at = now
            session.commit()

            return True

        if last_alerted_at.tzinfo is None:
            last_alerted_at = (
                last_alerted_at.replace(
                    tzinfo=timezone.utc
                )
            )

        cooldown = timedelta(
            hours=ALERT_COOLDOWN_HOURS
        )

        if (
            now - last_alerted_at
            >= cooldown
        ):
            alert.last_alerted_at = now
            session.commit()

            return True

        session.commit()

        return False


def should_alert_for_missing_data(
    total_items: int,
    missing_items: int,
) -> bool:
    """
    Decide si una pérdida parcial de datos
    es suficientemente grave como para alertar.
    """

    if total_items < MIN_ITEMS_FOR_PARTIAL_ALERT:
        return False

    if total_items <= 0:
        return False

    failure_ratio = (
        missing_items / total_items
    )

    return (
        failure_ratio
        >= FAILURE_RATIO_THRESHOLD
    )