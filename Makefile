.PHONY: install run test clean

install:
	uv sync --all-extras

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	uv run pytest -v

clean:
	rm -rf data/ .pytest_cache __pycache__
