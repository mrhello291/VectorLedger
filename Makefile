.PHONY: install test lint demo up down

install:
	python -m pip install -e '.[dev]'

test:
	pytest --cov=vectorledger --cov-report=term-missing

lint:
	ruff check .
	mypy src

up:
	docker compose up --build -d

demo:
	docker compose --profile demo run --rm demo

down:
	docker compose down
