import pytest
from backend.app.services.utils.parsers import detect_language_german, PLATFORM_PATTERNS


def test_detect_language_german():
    german_text = "Hallo! Heute lernen wir dax trading auf Deutsch. Aktien kaufen leicht gemacht."
    english_text = "Welcome guys! Today we are trading AAPL and TSLA options. Highly profitable setup."

    german_confidence = detect_language_confidence(german_text)
    english_confidence = detect_language_confidence(english_text)

    assert german_confidence > english_confidence


def test_extract_community_links():
    from backend.app.services.utils.parsers import extract_community_links
    sample_desc = "Join our Discord: https://discord.gg/abcd123 and Telegram: t.me/trading_de. Patreon support: patreon.com/mytrade"

    links = extract_community_links(sample_desc)

    platforms = [link["platform"] for link in links]
    assert "discord" in platforms
    assert "telegram" in platforms
    assert "patreon" in platforms


def detect_language_confidence(text: str) -> float:
    return detect_language_german(text)
