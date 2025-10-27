FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen --no-cache

# Copy the script and data files
COPY populate_test_data.py .
COPY rates.xlsx .

# Set the default command - allow overriding with --fast or --realistic flags
ENTRYPOINT [".venv/bin/python", "populate_test_data.py"]