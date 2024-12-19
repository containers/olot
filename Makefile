
.PHONY: install
install:
	poetry install

.PHONY: build
build: install
	poetry build

.PHONY: test
test:
	poetry run pytest -s -x -rA

.PHONY: test-e2e-skopeo
test-e2e-skopeo:
	poetry run pytest --e2e-skopeo -s -x -rA

.PHONY: test-e2e-oras
test-e2e-oras:
	poetry run pytest --e2e-oras -s -x -rA

.PHONY: lint
lint: install
	poetry run ruff check --fix

.PHONY: mypy
mypy: install
	poetry run mypy .