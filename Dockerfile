# Development image: runs the test suite and the interactive CLI.
# The desktop GUI is packaged natively and is not part of this image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install dev dependencies first so this layer is cached across code changes.
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt \
    && useradd --create-home --uid 1000 app

COPY --chown=app:app pyproject.toml main.py ./
COPY --chown=app:app src ./src
COPY --chown=app:app tests ./tests

USER app

ENTRYPOINT ["python", "main.py"]
