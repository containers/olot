
.PHONY: install
install:
	poetry install

.PHONY: build
build: clean install olot/embedded_oci_layout/oci-layout
	poetry build

.PHONY: deploy-kind-cluster
deploy-kind-cluster:
	LOCAL=1 ./e2e/deploy_kind_cluster.sh

.PHONY: deploy-local-registry
deploy-local-registry:
	./e2e/deploy_distribution_registry.sh

.PHONY: test
test:
	poetry run pytest -s -x -rA

.PHONY: test-e2e-skopeo
test-e2e-skopeo: deploy-kind-cluster deploy-local-registry
	poetry run pytest --e2e-skopeo -s -x -rA

.PHONY: test-e2e-oras
test-e2e-oras: deploy-kind-cluster deploy-local-registry
	poetry run pytest --e2e-oras -s -x -rA

.PHONY: lint
lint: install
	poetry run ruff check --fix

.PHONY: mypy
mypy: install
	poetry run mypy .

olot/embedded_oci_layout/oci-layout:
	poetry run python olot/embedded_oci_layout.py

.PHONY: clean
clean:
	rm -rf olot/embedded_oci_layout/
