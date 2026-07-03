# adguardctl task runner. Run `just` or `just help` to list recipes.
set shell := ["bash", "-uc"]

# Show available recipes.
default: help

help:
    @just --list

# Sync the virtual environment from the lockfile.
sync:
    uv sync

# Alias for sync (create/refresh the dev environment).
install: sync

# Update the lockfile.
lock:
    uv lock

# Run the CLI, forwarding arguments (e.g. `just run status --json`).
run *ARGS:
    uv run adguardctl {{ARGS}}

# Run the CLI against a live compose instance (admin/test1234).
dev *ARGS:
    AGH_HOST=localhost AGH_PORT=3000 AGH_USERNAME=admin AGH_PASSWORD=test1234 \
        uv run adguardctl {{ARGS}}

# Run unit tests (with coverage).
test:
    uv run pytest -m "not slow"

# Alias for the unit test suite.
test-unit: test

# Run integration tests against the compose instance.
test-integration:
    uv run pytest -m integration --slow

# Show a coverage report.
cov:
    uv run pytest -m "not slow" --cov-report=term-missing

# Lint.
lint:
    uv run ruff check .

# Format the code.
format:
    uv run ruff format .

# Check formatting without modifying files.
format-check:
    uv run ruff format --check .

# Type-check.
type:
    uv run ty check

# Spell-check.
spell:
    uv run codespell src tests

# Full CI gate: format check, lint, type, unit tests.
check: format-check lint type test
ci: check

# Build the wheel/sdist.
build:
    uv build

# Start the AdGuard Home + Unbound test stack (builds the Unbound image).
compose-up:
    docker compose up -d --build --wait

# Stop and remove the test container and its volume.
compose-down:
    docker compose down -v

# Remove build artifacts and caches.
clean:
    rm -rf dist build .pytest_cache .ruff_cache .coverage htmlcov
    find . -type d -name __pycache__ -prune -exec rm -rf {} +

# Print the package version.
version:
    @uv run python -c "import adguardctl; print(adguardctl.__version__)"
