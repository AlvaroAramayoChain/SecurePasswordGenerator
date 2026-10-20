# Secure Password Generator

[![CI](https://github.com/AlvaroAramayoChain/SecurePasswordGenerator/actions/workflows/ci.yml/badge.svg)](https://github.com/AlvaroAramayoChain/SecurePasswordGenerator/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small, dependency-free Python library and command-line tool that generates
cryptographically secure random passwords. The backend is UI-free and exposes
a single function, so a desktop GUI (coming soon) or any other program can
reuse it directly.

## Features

- **Cryptographically secure**: built on Python's `secrets` module, never `random`.
- **Configurable length**: from 8 to 128 characters.
- **Selectable character sets**: letters (upper and lower case), digits and
  symbols (`!@#$%^&*()-_=+[]{};:,.<>?`). Any combination works, as long as at
  least one set is enabled.
- **Guaranteed coverage**: every selected category appears at least once, at
  a random position.
- **Clear errors**: descriptive custom exceptions for invalid input.
- **Reusable API**: `from passgen import generate_password`.
- **Cross-platform**: tested on Linux, Windows and macOS with Python 3.10-3.13,
  plus a Docker image for a reproducible environment.

## Run from source

Requires Python 3.10 or newer. The generator itself has no third-party
dependencies.

```bash
git clone https://github.com/AlvaroAramayoChain/SecurePasswordGenerator.git
cd SecurePasswordGenerator
python main.py
```

Optionally, install it as a package to get a `passgen` command:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
passgen --length 20
```

## CLI usage

```text
usage: passgen [-h] [-l LENGTH] [--no-letters] [--no-digits] [--no-symbols]

Generate a cryptographically secure random password.

options:
  -h, --help           show this help message and exit
  -l, --length LENGTH  password length (8-128); asked interactively if omitted
  --no-letters         exclude letters (A-Z, a-z)
  --no-digits          exclude digits (0-9)
  --no-symbols         exclude special characters

Example: passgen --length 20 --no-symbols
```

### Examples

```console
$ python main.py
Password length (8-128): 16
q7}V;Rm2!xLc@9Tz

$ python main.py --length 24 --no-symbols
b8KxQ2mVt7RzL4hNwP9cYs3D

$ python main.py -l 10 --no-letters --no-symbols
4817305926

$ python main.py --length 4
Error: Password length must be between 8 and 128 characters, got 4.
```

The CLI exits with code `0` on success, `2` on invalid input and `130` when
cancelled (Ctrl+C or end of input).

## Use as a library

```python
from passgen import InvalidLengthError, PasswordGeneratorError, generate_password

password = generate_password(16)                         # all character sets
pin_like = generate_password(12, use_letters=False, use_symbols=False)

try:
    generate_password(200)
except InvalidLengthError as error:
    print(error.min_length, error.max_length)            # 8 128
except PasswordGeneratorError as error:                  # base class for all errors
    print(error)
```

| Exception                     | Raised when                                   |
| ----------------------------- | --------------------------------------------- |
| `InvalidLengthError`          | The length is outside 8-128 (`ValueError`).   |
| `InvalidLengthTypeError`      | The length is not an `int` (`TypeError`).     |
| `NoCharacterSetSelectedError` | Letters, digits and symbols are all disabled. |

## Docker

Docker provides an identical environment on every machine, for development,
tests and the CLI only. The desktop GUI will be packaged natively.

```bash
# Run the test suite inside the container
docker compose run --rm test

# Run the interactive CLI
docker compose run --rm cli

# Pass flags to the CLI
docker compose run --rm cli --length 20 --no-symbols
```

The image is based on `python:3.12-slim`, runs as a non-root user and contains
no secrets.

## Running tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Continuous integration runs the suite on Linux, Windows and macOS with Python
3.10, 3.11, 3.12 and 3.13, and again inside the Docker image.

## Security

- Every character is chosen with `secrets.choice`, and the final order is
  shuffled with `secrets.SystemRandom`. Both draw from the operating system's
  cryptographically secure random number generator.
- One character is drawn from each selected category, the rest come from the
  combined pool, and the result is then securely shuffled. Required characters
  therefore never sit at predictable positions.
- **Nothing is stored, logged or sent anywhere.** Passwords exist only in
  memory and on your screen. The tool makes no network connections.
- Keep generated passwords in a reputable password manager.

## Roadmap

- [x] Secure generation backend with a reusable API
- [x] Command-line interface
- [x] Docker image and cross-platform CI
- [ ] **Desktop GUI**, built on the same `generate_password` API and packaged
      natively for each operating system

## License

Released under the [MIT License](LICENSE).
