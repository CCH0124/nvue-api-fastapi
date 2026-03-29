# Makefile 範例
.PHONY: format lint run

lint:
	poetry run ruff check .

sort:
	poetry run ruff check --fix .

format:
	poetry run ruff format .