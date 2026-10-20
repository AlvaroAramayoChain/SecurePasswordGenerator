"""User-facing texts for the interactive (GUI) flow, one dictionary per language.

This module has no Qt dependency, so the dialog state machine and its tests can
use it without PySide6. To add a language, add one more dictionary to
``TEXTS`` with exactly the same keys; nothing else needs to change.

Keys starting with ``key_`` are the single-letter commands the user types
(character types and copy). They are language-specific and are automatically
available as ``{key_...}`` placeholders inside every text.
"""

from typing import Final

DEFAULT_LANGUAGE: Final[str] = "en"
KEY_PREFIX: Final[str] = "key_"

TEXTS: Final[dict[str, dict[str, str]]] = {
    "es": {
        "window_title": "Generador de Contraseñas Seguras",
        "console_title": "Password Console",
        "welcome": "¡Bienvenido al generador de contraseñas seguras!",
        "ask_length": "¿Cuántos caracteres querés? ({min}-{max})",
        "ask_types": (
            "¿Qué tipos incluir? Enter = todos, o combiná: "
            "{key_letters} = letras, {key_digits} = números, "
            "{key_symbols} = símbolos"
        ),
        "result_label": "Tu contraseña:",
        "next_actions": "Enter = generar otra, {key_copy} = copiar al portapapeles",
        "copied": "¡Copiada al portapapeles!",
        "error_empty_length": "Escribí un número entre {min} y {max}.",
        "error_not_number": "«{value}» no es un número. Probá de nuevo.",
        "error_length_range": "La longitud debe estar entre {min} y {max}.",
        "error_types": (
            "Opción no válida. Usá solo {key_letters}, {key_digits} "
            "o {key_symbols}, o Enter para todos."
        ),
        "error_next": "Opción no válida. Presioná Enter o escribí {key_copy}.",
        "placeholder": "Escribí tu respuesta...",
        "run_button": "Ejecutar",
        "tooltip_run": "Enviar respuesta (Enter)",
        "tooltip_minimize": "Minimizar",
        "tooltip_maximize": "Maximizar (no disponible)",
        "tooltip_close": "Cerrar",
        "tooltip_language": "Idioma: Español / English",
        "key_letters": "l",
        "key_digits": "n",
        "key_symbols": "s",
        "key_copy": "c",
    },
    "en": {
        "window_title": "Secure Password Generator",
        "console_title": "Password Console",
        "welcome": "Welcome to the secure password generator!",
        "ask_length": "How many characters do you want? ({min}-{max})",
        "ask_types": (
            "Which types to include? Enter = all, or combine: "
            "{key_letters} = letters, {key_digits} = digits, "
            "{key_symbols} = symbols"
        ),
        "result_label": "Your password:",
        "next_actions": "Enter = generate another, {key_copy} = copy to clipboard",
        "copied": "Copied to clipboard!",
        "error_empty_length": "Type a number between {min} and {max}.",
        "error_not_number": "\"{value}\" is not a number. Please try again.",
        "error_length_range": "The length must be between {min} and {max}.",
        "error_types": (
            "Invalid option. Use only {key_letters}, {key_digits} "
            "or {key_symbols}, or Enter for all."
        ),
        "error_next": "Invalid option. Press Enter or type {key_copy}.",
        "placeholder": "Type your answer...",
        "run_button": "Run",
        "tooltip_run": "Submit answer (Enter)",
        "tooltip_minimize": "Minimize",
        "tooltip_maximize": "Maximize (not available)",
        "tooltip_close": "Close",
        "tooltip_language": "Language: Español / English",
        "key_letters": "l",
        "key_digits": "d",
        "key_symbols": "s",
        "key_copy": "c",
    },
}

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = tuple(TEXTS)


class UnsupportedLanguageError(ValueError):
    """Raised when a language code is not one of ``SUPPORTED_LANGUAGES``.

    Args:
        language: The rejected language code.
    """

    def __init__(self, language: object) -> None:
        """Store the rejected code and build a descriptive message.

        Args:
            language: The rejected language code.
        """
        self.language = language
        supported = ", ".join(SUPPORTED_LANGUAGES)
        super().__init__(
            f"Unsupported language {language!r}; expected one of: {supported}."
        )


def is_supported(language: object) -> bool:
    """Tell whether ``language`` is a supported language code.

    Args:
        language: The value to check.

    Returns:
        ``True`` if it is a key of ``TEXTS``.
    """
    return isinstance(language, str) and language in TEXTS


def require_language(language: str) -> str:
    """Validate a language code.

    Args:
        language: The code to validate.

    Returns:
        The same code, if supported.

    Raises:
        UnsupportedLanguageError: If the code is not supported.
    """
    if not is_supported(language):
        raise UnsupportedLanguageError(language)
    return language


def key_params(language: str) -> dict[str, str]:
    """Return the command keys of a language, ready to use as placeholders.

    Args:
        language: A supported language code.

    Returns:
        A mapping such as ``{"key_letters": "l", "key_digits": "d", ...}``.
    """
    texts = TEXTS[require_language(language)]
    return {name: value for name, value in texts.items() if name.startswith(KEY_PREFIX)}


def get_text(language: str, key: str, **params: object) -> str:
    """Return a localized text with its placeholders filled in.

    The language's ``key_*`` command letters are always available as
    placeholders; explicit ``params`` take precedence over them.

    Args:
        language: A supported language code.
        key: The text identifier, e.g. ``"ask_length"``.
        **params: Values for the text's ``{placeholders}``.

    Returns:
        The formatted text.

    Raises:
        UnsupportedLanguageError: If ``language`` is not supported.
        KeyError: If ``key`` or a required placeholder is missing.
    """
    template = TEXTS[require_language(language)][key]
    return template.format(**{**key_params(language), **params})


def detect_language(locale_name: str | None) -> str:
    """Pick the interface language from a locale name.

    Args:
        locale_name: A locale such as ``"es_AR"``, ``"es-ES"`` or ``"en_US"``.
            ``None`` or an empty string selects the default language.

    Returns:
        The matching supported language code, or ``DEFAULT_LANGUAGE``.
    """
    if not locale_name:
        return DEFAULT_LANGUAGE
    prefix = locale_name.replace("-", "_").split("_")[0].lower()
    return prefix if is_supported(prefix) else DEFAULT_LANGUAGE
