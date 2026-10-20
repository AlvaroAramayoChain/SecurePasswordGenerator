"""Language-aware state machine for the guided password dialog.

The session is pure Python (no Qt): it receives the user's text and returns the
lines to display, so any front end can drive it and it can be unit-tested.
The generated password lives only in memory for the copy command; it is never
written to disk or logged.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from passgen.exceptions import InvalidLengthError, PasswordGeneratorError
from passgen.generator import MAX_LENGTH, MIN_LENGTH, generate_password
from passgen.strings import get_text, key_params, require_language


class State(Enum):
    """The question the session is currently waiting an answer for."""

    ASK_LENGTH = auto()
    ASK_TYPES = auto()
    SHOW_RESULT = auto()


class LineKind(Enum):
    """How a terminal line should be presented."""

    OUTPUT = auto()
    ECHO = auto()
    ERROR = auto()
    PASSWORD = auto()


@dataclass(frozen=True)
class Line:
    """One line of terminal output.

    Attributes:
        kind: The presentation category of the line.
        text: The plain text to display.
    """

    kind: LineKind
    text: str


@dataclass(frozen=True)
class StepResult:
    """What a front end must do after a session step.

    Attributes:
        lines: Lines to append to the terminal, in order.
        copy_text: Text to place on the clipboard, or ``None``.
    """

    lines: tuple[Line, ...]
    copy_text: str | None = None


@dataclass(frozen=True)
class CharacterOptions:
    """Which character categories the user selected.

    Attributes:
        use_letters: Include letters.
        use_digits: Include digits.
        use_symbols: Include symbols.
    """

    use_letters: bool = True
    use_digits: bool = True
    use_symbols: bool = True


@dataclass
class _Answers:
    """Answers collected so far in the current flow.

    Attributes:
        length: The accepted password length.
        options: The accepted character options.
        password: The last generated password, kept only for copying.
    """

    length: int = MIN_LENGTH
    options: CharacterOptions = field(default_factory=CharacterOptions)
    password: str = ""


class Session:
    """Drive the guided dialog: length, then character types, then result.

    Args:
        language: A supported language code, e.g. ``"es"`` or ``"en"``.

    Raises:
        UnsupportedLanguageError: If ``language`` is not supported.
    """

    def __init__(self, language: str) -> None:
        """Create a session in the given language, ready to ``start()``.

        Args:
            language: A supported language code.
        """
        self._language = require_language(language)
        self._state = State.ASK_LENGTH
        self._answers = _Answers()

    @property
    def language(self) -> str:
        """The session's language code."""
        return self._language

    @property
    def state(self) -> State:
        """The question the session is waiting an answer for."""
        return self._state

    def start(self) -> StepResult:
        """Reset the flow and return the welcome and first question.

        Returns:
            The opening lines.
        """
        self._state = State.ASK_LENGTH
        self._answers = _Answers()
        return StepResult((self._output("welcome"), self._ask_length_line()))

    def switch_language(self, language: str) -> StepResult:
        """Change the language and restart the flow from the beginning.

        Args:
            language: A supported language code.

        Returns:
            The opening lines in the new language.

        Raises:
            UnsupportedLanguageError: If ``language`` is not supported.
        """
        self._language = require_language(language)
        return self.start()

    def submit(self, text: str) -> StepResult:
        """Process one answer typed by the user.

        Args:
            text: The raw text the user entered (may be empty).

        Returns:
            The echoed answer followed by the session's response.
        """
        answer = text.strip()
        echo = Line(LineKind.ECHO, answer)
        handlers = {
            State.ASK_LENGTH: self._handle_length,
            State.ASK_TYPES: self._handle_types,
            State.SHOW_RESULT: self._handle_next_action,
        }
        result = handlers[self._state](answer)
        return StepResult((echo, *result.lines), result.copy_text)

    def _handle_length(self, answer: str) -> StepResult:
        """Validate the length answer and move on to the types question.

        Args:
            answer: The stripped user input.

        Returns:
            The next question, or an error plus the same question again.
        """
        if not answer:
            return self._retry_length("error_empty_length")
        try:
            length = int(answer)
        except ValueError:
            return self._retry_length("error_not_number", value=answer)
        # Let the backend validate the range so its rules live in one place;
        # the throwaway password is discarded immediately.
        try:
            generate_password(length)
        except InvalidLengthError as error:
            return self._length_range_error(error)
        self._answers.length = length
        self._state = State.ASK_TYPES
        return StepResult((self._output("ask_types"),))

    def _handle_types(self, answer: str) -> StepResult:
        """Parse the character types answer and show the first password.

        Args:
            answer: The stripped user input.

        Returns:
            The generated password and the next actions, or an error.
        """
        options = self._parse_options(answer)
        if options is None:
            return StepResult((self._error("error_types"), self._output("ask_types")))
        self._answers.options = options
        self._state = State.SHOW_RESULT
        return self._generate_result()

    def _handle_next_action(self, answer: str) -> StepResult:
        """Handle "generate another" (Enter) or the copy command.

        Args:
            answer: The stripped user input.

        Returns:
            A new password, a copy confirmation, or an error.
        """
        if not answer:
            return self._generate_result()
        if answer.lower() == key_params(self._language)["key_copy"]:
            return StepResult((self._output("copied"),), self._answers.password)
        return StepResult((self._error("error_next"), self._output("next_actions")))

    def _parse_options(self, answer: str) -> CharacterOptions | None:
        """Convert a types answer into character options.

        Args:
            answer: The stripped user input; empty means every type.

        Returns:
            The selected options, or ``None`` if the answer contains anything
            other than this language's type keys.
        """
        if not answer:
            return CharacterOptions()
        keys = key_params(self._language)
        typed = set(answer.lower().replace(" ", ""))
        allowed = {keys["key_letters"], keys["key_digits"], keys["key_symbols"]}
        if not typed <= allowed:
            return None
        return CharacterOptions(
            use_letters=keys["key_letters"] in typed,
            use_digits=keys["key_digits"] in typed,
            use_symbols=keys["key_symbols"] in typed,
        )

    def _generate_result(self) -> StepResult:
        """Generate a password with the stored answers.

        Returns:
            The result label, the password and the next actions.
        """
        options = self._answers.options
        try:
            password = generate_password(
                self._answers.length,
                use_letters=options.use_letters,
                use_digits=options.use_digits,
                use_symbols=options.use_symbols,
            )
        except PasswordGeneratorError:
            # Unreachable with validated answers; restart instead of crashing.
            return self.start()
        self._answers.password = password
        return StepResult(
            (
                self._output("result_label"),
                Line(LineKind.PASSWORD, password),
                self._output("next_actions"),
            )
        )

    def _retry_length(self, key: str, **params: object) -> StepResult:
        """Return an error message followed by the length question.

        Args:
            key: The error text identifier.
            **params: Placeholder values for the error text.

        Returns:
            The error and the repeated question.
        """
        error = self._error(key, min=MIN_LENGTH, max=MAX_LENGTH, **params)
        return StepResult((error, self._ask_length_line()))

    def _length_range_error(self, error: InvalidLengthError) -> StepResult:
        """Build a localized range error from the exception's data.

        Args:
            error: The exception raised by the backend.

        Returns:
            The localized error and the repeated question.
        """
        message = get_text(
            self._language,
            "error_length_range",
            min=error.min_length,
            max=error.max_length,
        )
        return StepResult((Line(LineKind.ERROR, message), self._ask_length_line()))

    def _ask_length_line(self) -> Line:
        """Return the length question as an output line."""
        return self._output("ask_length", min=MIN_LENGTH, max=MAX_LENGTH)

    def _output(self, key: str, **params: object) -> Line:
        """Build an output line from a text key.

        Args:
            key: The text identifier.
            **params: Placeholder values.

        Returns:
            The localized output line.
        """
        return Line(LineKind.OUTPUT, get_text(self._language, key, **params))

    def _error(self, key: str, **params: object) -> Line:
        """Build an error line from a text key.

        Args:
            key: The text identifier.
            **params: Placeholder values.

        Returns:
            The localized error line.
        """
        return Line(LineKind.ERROR, get_text(self._language, key, **params))
