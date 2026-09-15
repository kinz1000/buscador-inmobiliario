from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


class PropertyListing(Base):
    __tablename__ = "property_listings"

    __table_args__ = (
        UniqueConstraint(
            "portal",
            "external_id",
            name="uq_portal_external_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    portal: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    price: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    zone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    advertiser: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
    )

    published_at: Mapped[datetime | None] = (
        mapped_column(
            DateTime,
            nullable=True,
        )
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )
    retention_started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    advertiser_check_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_advertiser_check_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )
    raw_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class ParserHealthAlert(Base):
    __tablename__ = "parser_health_alerts"

    __table_args__ = (
        UniqueConstraint(
            "portal",
            "issue_code",
            name="uq_parser_health_portal_issue",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    portal: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    issue_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )

    last_alerted_at: Mapped[datetime | None] = (
        mapped_column(
            DateTime,
            nullable=True,
        )
    )