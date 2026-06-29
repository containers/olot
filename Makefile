
.PHONY: install
install:
	uv sync

.PHONY: build
build: install
	uv build

.PHONY: deploy-kind-cluster
deploy-kind-cluster:
	LOCAL=1 ./e2e/deploy_kind_cluster.sh

.PHONY: deploy-local-registry
deploy-local-registry:
	./e2e/deploy_distribution_registry.sh

.PHONY: test
test:
	uv run pytest -s -x -rA

.PHONY: test-e2e-skopeo
test-e2e-skopeo: deploy-kind-cluster deploy-local-registry
	uv run pytest --e2e-skopeo -s -x -rA

.PHONY: test-e2e-oras
test-e2e-oras: deploy-kind-cluster deploy-local-registry
	uv run pytest --e2e-oras -s -x -rA

.PHONY: test-e2e-oras-py
test-e2e-oras-py: deploy-kind-cluster deploy-local-registry
	uv run pytest --e2e-oras-py -s -x -rA

.PHONY: lint
lint: install
	uv run ruff check --fix

.PHONY: mypy
mypy: install
	uv run mypy .
