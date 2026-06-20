# Use python:3.14-slim-bookworm to satisfy the >=3.14 python requirement
FROM python:3.14-slim-bookworm

# Install uv using the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking
ENV UV_LINK_MODE=copy

# Copy project definition (pyproject.toml)
COPY pyproject.toml ./

# Install dependencies using uv sync (leverages cache mount)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# Copy the rest of the application code (server.py, README.md, mcpreadme.md)
COPY . .

# Sync the project itself (leverages cache mount)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Run the server.py directly using uv run
CMD ["uv", "run", "server.py"]
