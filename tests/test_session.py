"""Tests for the guided dialog state machine, in every supported language."""

import string

import pytest

from passgen import MAX_LENGTH, MIN_LENGTH, SYMBOLS
from passgen.session import Line, LineKind, Session, State, StepResult
from passgen.strings import SUPPORTED_LANGUAGES, TEXTS, get_text

LANGUAGES = pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
REPETITIONS = 50


def _keys(language: str) -> dict[str, str]:
    """Return the command keys of a language.

    Args:
        language: A supported language code.

    Returns:
        The ``key_*`` entries of that language.
    """
    return {name: value for name, value in TEXTS[language].items() if name.startswith("key_")}


def _texts(result: StepResult, kind: LineKind | None = None) -> list[str]:
    """Return the texts of a step's lines, optionally filtered by kind.

    Args:
        result: The step result.
        kind: Only keep lines of this kind, if given.

    Returns:
        The line texts in order.
    """
    return [line.text for line in result.lines if kind is None or line.kind == kind]


def _password(result: StepResult) -> str:
    """Return the single password shown in a step.

    Args:
        result: The step result.

    Returns:
        The password text.
    """
    (password,) = _texts(result, LineKind.PASSWORD)
    return password


def _session_at_types(language: str, length: int = 16) -> Session:
    """Return a session that already accepted a length.

    Args:
        language: A supported language code.
        length: The length to submit.

    Returns:
        A session waiting for the types answer.
    """
    session = Session(language)
    session.start()
    session.submit(str(length))
    return session


@LANGUAGES
def test_start_shows_welcome_and_length_question(language: str) -> None:
    """The flow opens with the welcome line and the length question."""
    result = Session(language).start()
    assert _texts(result) == [
        get_text(language, "welcome"),
        get_text(language, "ask_length", min=MIN_LENGTH, max=MAX_LENGTH),
    ]


@LANGUAGES
def test_valid_flow_produces_password(language: str) -> None:
    """Length, then Enter for all types, yields a password and next actions."""
    session = _session_at_types(language, 20)
    assert session.state is State.ASK_TYPES
    result = session.submit("")
    assert session.state is State.SHOW_RESULT
    assert len(_password(result)) == 20
    assert _texts(result)[-1] == get_text(language, "next_actions")


@LANGUAGES
def test_answers_are_echoed(language: str) -> None:
    """Every submitted answer is echoed first, stripped of whitespace."""
    session = Session(language)
    session.start()
    result = session.submit("  12 ")
    assert result.lines[0] == Line(LineKind.ECHO, "12")


@LANGUAGES
@pytest.mark.parametrize("answer", ["abc", "12.5", "doce", ""])
def test_non_numeric_length_asks_again(language: str, answer: str) -> None:
    """Non-numeric or empty lengths show an error and repeat the question."""
    session = Session(language)
    session.start()
    result = session.submit(answer)
    assert session.state is State.ASK_LENGTH
    assert _texts(result, LineKind.ERROR)
    assert _texts(result)[-1] == get_text(
        language, "ask_length", min=MIN_LENGTH, max=MAX_LENGTH
    )


@LANGUAGES
@pytest.mark.parametrize("length", [MIN_LENGTH - 1, 0, -3, MAX_LENGTH + 1, 999])
def test_out_of_range_length_asks_again(language: str, length: int) -> None:
    """Out-of-range lengths show a localized range error with the bounds."""
    session = Session(language)
    session.start()
    result = session.submit(str(length))
    assert session.state is State.ASK_LENGTH
    assert _texts(result, LineKind.ERROR) == [
        get_text(language, "error_length_range", min=MIN_LENGTH, max=MAX_LENGTH)
    ]


@LANGUAGES
@pytest.mark.parametrize("answer", ["x", "lx", "123", "c"])
def test_invalid_type_letters_ask_again(language: str, answer: str) -> None:
    """Answers with anything but the language's type keys are rejected."""
    session = _session_at_types(language)
    result = session.submit(answer)
    assert session.state is State.ASK_TYPES
    assert _texts(result, LineKind.ERROR) == [get_text(language, "error_types")]


def test_each_language_rejects_the_other_languages_keys() -> None:
    """Spanish rejects English "d" and English rejects Spanish "n"."""
    for language, foreign_key in (("es", "d"), ("en", "n")):
        session = _session_at_types(language)
        session.submit(foreign_key)
        assert session.state is State.ASK_TYPES


@LANGUAGES
def test_default_types_include_every_category(language: str) -> None:
    """Enter selects letters, digits and symbols."""
    password = set(_password(_session_at_types(language, MAX_LENGTH).submit("")))
    for category in (string.ascii_uppercase, string.ascii_lowercase, string.digits, SYMBOLS):
        assert password & set(category)


@LANGUAGES
@pytest.mark.parametrize(
    "selection",
    [("key_letters",), ("key_digits",), ("key_symbols",),
     ("key_letters", "key_digits"), ("key_digits", "key_symbols"),
     ("key_letters", "key_symbols")],
)
def test_generated_passwords_respect_options(
    language: str, selection: tuple[str, ...]
) -> None:
    """Every password contains only, and all of, the selected categories."""
    keys = _keys(language)
    answer = "".join(keys[name] for name in selection).upper()
    categories = {
        "key_letters": set(string.ascii_letters),
        "key_digits": set(string.digits),
        "key_symbols": set(SYMBOLS),
    }
    allowed = set().union(*(categories[name] for name in selection))
    session = _session_at_types(language, MIN_LENGTH)
    result = session.submit(answer)
    for _ in range(REPETITIONS):
        password = _password(result)
        assert len(password) == MIN_LENGTH and set(password) <= allowed
        for name in selection:
            assert set(password) & categories[name]
        result = session.submit("")


@LANGUAGES
def test_enter_generates_another_password(language: str) -> None:
    """Pressing Enter on the result generates a new, different password."""
    session = _session_at_types(language, 32)
    first = _password(session.submit(""))
    second = _password(session.submit(""))
    assert session.state is State.SHOW_RESULT
    assert len(second) == 32 and second != first


@LANGUAGES
def test_copy_command_returns_last_password(language: str) -> None:
    """The copy command hands the last password to the front end."""
    session = _session_at_types(language)
    password = _password(session.submit(""))
    result = session.submit(_keys(language)["key_copy"].upper())
    assert result.copy_text == password
    assert _texts(result, LineKind.OUTPUT) == [get_text(language, "copied")]
    assert session.state is State.SHOW_RESULT


@LANGUAGES
def test_unknown_next_action_shows_error(language: str) -> None:
    """Anything but Enter or the copy key is rejected on the result screen."""
    session = _session_at_types(language)
    session.submit("")
    result = session.submit("zzz")
    assert result.copy_text is None
    assert _texts(result, LineKind.ERROR) == [get_text(language, "error_next")]


@pytest.mark.parametrize(("old", "new"), [("es", "en"), ("en", "es")])
def test_switch_language_restarts_in_new_language(old: str, new: str) -> None:
    """Switching restarts the flow and no old-language text appears."""
    session = _session_at_types(old)
    session.submit("")
    result = session.switch_language(new)
    assert session.language == new and session.state is State.ASK_LENGTH
    assert _texts(result) == _texts(Session(new).start())
    old_only = set(TEXTS[old].values()) - set(TEXTS[new].values())
    assert not any(text in line for line in _texts(result) for text in old_only if len(text) > 1)
