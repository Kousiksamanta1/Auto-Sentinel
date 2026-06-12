.PHONY: install install-dev run test lint check

install:
	python -m pip install -e .

install-dev:
	python -m pip install -e ".[dev]"

run:
	python main.py

test:
	QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v

lint:
	ruff check .

check: lint test
