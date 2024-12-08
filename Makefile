
.PHONY: install
install:
	poetry install

.PHONY: build
build: install
	poetry build

.PHONY: test
test:
	poetry run pytest -s -x -rA

.PHONY: lint
lint: install
	poetry run ruff check --fix

.PHONY: mypy
mypy: install
	poetry run mypy .