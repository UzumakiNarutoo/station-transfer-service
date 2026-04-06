.PHONY: install run test clean setup

setup:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv sync --all-extras

install: setup

run: setup
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test: setup
	uv run pytest -v

clean:
	rm -rf data/ .pytest_cache __pycache__ .venv
