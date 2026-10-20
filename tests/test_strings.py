"""Tests for the localized texts module."""

import string

import pytest

from passgen.strings import (
    DEFAULT_LANGUAGE,
    KEY_PREFIX,
    SUPPORTED_LANGUAGES,
    TEXTS,
    UnsupportedLanguageError,
    detect_language,
    get_text,
)

REFERENCE_LANGUAGE = SUPPORTED_LANGUAGES[0]
COMMAND_KEYS = ("key_letters", "key_digits", "key_symbols", "key_copy")


def _placeholders(template: str) -> set[str]:
    """Return the ``{placeholder}`` names used in a template.

    Args:
        template: A ``str.format`` template.

    Returns:
        The set of field names.
    """
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_spanish_and_english_are_supported() -> None:
    """Both required languages are available."""
    assert {"es", "en"} <= set(SUPPORTED_LANGUAGES)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_all_languages_have_identical_keys(language: str) -> None:
    """Every language defines exactly the same text keys."""
    assert TEXTS[language].keys() == TEXTS[REFERENCE_LANGUAGE].keys()


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_no_empty_values(language: str) -> None:
    """No text is empty or whitespace only."""
    empty = [key for key, value in TEXTS[language].items() if not value.strip()]
    assert not empty


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_placeholders_match_across_languages(language: str) -> None:
    """Each text uses the same placeholders in every language."""
    for key, template in TEXTS[language].items():
        expected = _placeholders(TEXTS[REFERENCE_LANGUAGE][key])
        assert _placeholders(template) == expected, key


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_command_keys_are_distinct_single_letters(language: str) -> None:
    """Command keys are single lowercase letters and never collide."""
    keys = [TEXTS[language][name] for name in COMMAND_KEYS]
    assert all(len(key) == 1 and key.islower() for key in keys)
    assert len(set(keys)) == len(keys)


def test_language_specific_type_keys() -> None:
    """Spanish uses l/n/s, English l/d/s, and copy is c in both."""
    assert [TEXTS["es"][k] for k in COMMAND_KEYS] == ["l", "n", "s", "c"]
    assert [TEXTS["en"][k] for k in COMMAND_KEYS] == ["l", "d", "s", "c"]


def test_console_title_is_the_same_in_every_language() -> None:
    """The blue window title is not translated."""
    titles = {TEXTS[language]["console_title"] for language in SUPPORTED_LANGUAGES}
    assert titles == {"Password Console"}


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_every_text_formats_with_known_params(language: str) -> None:
    """All texts format cleanly given the session's parameters."""
    for key in TEXTS[language]:
        text = get_text(language, key, min=8, max=128, value="x")
        assert "{" not in text and "}" not in text, key


def test_get_text_fills_command_keys_automatically() -> None:
    """Command-key placeholders are filled from the language itself."""
    assert "n = números" in get_text("es", "ask_types")
    assert "d = digits" in get_text("en", "ask_types")


def test_get_text_rejects_unknown_language() -> None:
    """An unknown language raises a descriptive error."""
    with pytest.raises(UnsupportedLanguageError, match="fr"):
        get_text("fr", "welcome")


@pytest.mark.parametrize(
    ("locale_name", "expected"),
    [
        ("es_AR", "es"),
        ("es-ES", "es"),
        ("ES_mx", "es"),
        ("es", "es"),
        ("en_US", "en"),
        ("fr_FR", DEFAULT_LANGUAGE),
        ("", DEFAULT_LANGUAGE),
        (None, DEFAULT_LANGUAGE),
    ],
)
def test_detect_language(locale_name: str | None, expected: str) -> None:
    """Spanish locales map to Spanish; everything else to the default."""
    assert detect_language(locale_name) == expected


def test_key_prefix_matches_command_keys() -> None:
    """All command keys share the documented prefix."""
    assert all(name.startswith(KEY_PREFIX) for name in COMMAND_KEYS)
