from email import policy
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.parsers import milanuncios_parser


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "milanuncios_alert.eml"
)


@pytest.fixture
def milanuncios_email():
    """
    Carga el correo real de Milanuncios utilizado
    durante el desarrollo.
    """

    with FIXTURE_PATH.open("rb") as file:
        message = BytesParser(
            policy=policy.default,
        ).parse(file)

    html_part = message.get_body(
        preferencelist=("html",)
    )

    text_part = message.get_body(
        preferencelist=("plain",)
    )

    html = (
        html_part.get_content()
        if html_part
        else ""
    )

    text = (
        text_part.get_content()
        if text_part
        else ""
    )

    return SimpleNamespace(
        from_=message.get("From", ""),
        subject=message.get("Subject", ""),
        html=html,
        text=text,
    )


def test_detecta_correo_de_milanuncios(
    milanuncios_email,
):
    assert (
        milanuncios_parser.is_milanuncios_email(
            milanuncios_email
        )
        is True
    )


def test_extrae_id_de_url_milanuncios():
    url = (
        "https://www.milanuncios.com/ads/"
        "madrid-capital-613547547.htm"
    )

    external_id = (
        milanuncios_parser.extract_milanuncios_id(
            url
        )
    )

    assert external_id == "613547547"


def test_extrae_seis_tarjetas_del_correo_real(
    milanuncios_email,
    monkeypatch,
):
    counter = iter(
        [
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000001.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000002.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000003.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000004.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000005.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000006.htm",
        ]
    )

    monkeypatch.setattr(
        milanuncios_parser,
        "resolve_milanuncios_url",
        lambda _: next(counter),
    )

    cards = (
        milanuncios_parser.extract_milanuncios_cards(
            milanuncios_email
        )
    )

    assert len(cards) == 6


def test_extrae_precios_del_correo_real(
    milanuncios_email,
    monkeypatch,
):
    counter = iter(
        [
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000001.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000002.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000003.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000004.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000005.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000006.htm",
        ]
    )

    monkeypatch.setattr(
        milanuncios_parser,
        "resolve_milanuncios_url",
        lambda _: next(counter),
    )

    cards = (
        milanuncios_parser.extract_milanuncios_cards(
            milanuncios_email
        )
    )

    prices = sorted(
        card["price"]
        for card in cards.values()
    )

    assert prices == sorted(
        [
            730000,
            3290077,
            3290077,
            220000,
            513000,
            245000,
        ]
    )


def test_extrae_madrid_capital_como_ubicacion(
    milanuncios_email,
    monkeypatch,
):
    counter = iter(
        [
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000001.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000002.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000003.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000004.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000005.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000006.htm",
        ]
    )

    monkeypatch.setattr(
        milanuncios_parser,
        "resolve_milanuncios_url",
        lambda _: next(counter),
    )

    cards = (
        milanuncios_parser.extract_milanuncios_cards(
            milanuncios_email
        )
    )

    locations = {
        card["location"]
        for card in cards.values()
    }

    assert locations == {
        "Madrid Capital"
    }


def test_cada_tarjeta_tiene_external_id(
    milanuncios_email,
    monkeypatch,
):
    counter = iter(
        [
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000001.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000002.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000003.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000004.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000005.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000006.htm",
        ]
    )

    monkeypatch.setattr(
        milanuncios_parser,
        "resolve_milanuncios_url",
        lambda _: next(counter),
    )

    cards = (
        milanuncios_parser.extract_milanuncios_cards(
            milanuncios_email
        )
    )

    assert all(
        card["external_id"]
        for card in cards.values()
    )


def test_extract_links_devuelve_seis_urls_unicas(
    milanuncios_email,
    monkeypatch,
):
    counter = iter(
        [
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000001.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000002.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000003.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000004.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000005.htm",
            "https://www.milanuncios.com/ads/"
            "madrid-capital-600000006.htm",
        ]
    )

    monkeypatch.setattr(
        milanuncios_parser,
        "resolve_milanuncios_url",
        lambda _: next(counter),
    )

    links = (
        milanuncios_parser.extract_milanuncios_links(
            milanuncios_email
        )
    )

    assert len(links) == 6
    assert len(set(links)) == 6