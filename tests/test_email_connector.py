from unittest.mock import MagicMock, patch

from imap_tools import MailMessageFlags

from src.connectors import email_connector


def test_portal_filter_contains_all_portals() -> None:
    criteria = (
        email_connector
        .PORTAL_EMAIL_CRITERIA
        .casefold()
    )

    assert "is:unread" in criteria
    assert "idealista" in criteria
    assert "fotocasa" in criteria
    assert "habitaclia" in criteria
    assert "pisos.com" in criteria
    assert "milanuncios" in criteria


def test_fetch_unread_emails_uses_filter() -> None:
    mailbox = MagicMock()
    fake_email = MagicMock()

    mailbox.fetch.return_value = [
        fake_email
    ]

    with (
        patch.object(
            email_connector,
            "connect_to_mailbox",
            return_value=mailbox,
        ),
        patch.object(
            email_connector,
            "close_mailbox",
        ) as close_mailbox,
    ):
        result = (
            email_connector
            .fetch_unread_emails(limit=50)
        )

    assert result == [fake_email]

    mailbox.fetch.assert_called_once_with(
        email_connector.PORTAL_EMAIL_CRITERIA,
        mark_seen=False,
        reverse=True,
        limit=50,
    )

    close_mailbox.assert_called_once_with(
        mailbox
    )


def test_mark_emails_as_read() -> None:
    mailbox = MagicMock()

    with (
        patch.object(
            email_connector,
            "connect_to_mailbox",
            return_value=mailbox,
        ),
        patch.object(
            email_connector,
            "close_mailbox",
        ) as close_mailbox,
    ):
        result = (
            email_connector
            .mark_emails_as_read([
                "101",
                "102",
                "101",
            ])
        )

    assert result == 2

    mailbox.flag.assert_called_once()

    call_arguments = (
        mailbox.flag.call_args.args
    )

    marked_uids = call_arguments[0]
    used_flag = call_arguments[1]
    flag_value = call_arguments[2]

    assert set(marked_uids) == {
        "101",
        "102",
    }

    assert (
        used_flag
        == MailMessageFlags.SEEN
    )

    assert flag_value is True

    close_mailbox.assert_called_once_with(
        mailbox
    )


def test_mark_emails_does_nothing_when_empty() -> None:
    with patch.object(
        email_connector,
        "connect_to_mailbox",
    ) as connect_to_mailbox:
        result = (
            email_connector
            .mark_emails_as_read(set())
        )

    assert result == 0

    connect_to_mailbox.assert_not_called()