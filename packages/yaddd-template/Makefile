PY ?= uv run python
TAG ?= latest

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help
	@grep -E '^(## |[a-zA-Z_-]+:.*?## )' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} /^## / {printf "\n\033[1m%s\033[0m\n", substr($$0, 4); next} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## General (codebase)

.PHONY: install
install:  ## Create the environment and install every dependency group
	uv sync --all-groups

.PHONY: lock
lock:  ## Re-resolve uv.lock after changing dependencies
	uv lock

.PHONY: fmt
fmt:  ## Format the code
	uv run ruff format app tests
	uv run ruff check --fix app tests

.PHONY: lint
lint:  ## Check formatting, lint rules and architecture
	uv run ruff format --check app tests
	uv run ruff check app tests
	yaddd-linter app tests

.PHONY: types
types:  ## Run ty and pyright in strict mode
	uv run ty check app tests
	uv run pyright

.PHONY: clean
clean:  ## Remove caches and local SQLite databases
	rm -rf .pytest_cache .ty .ruff_cache dist build *.egg-info
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -f ./*.db

## Tests

.PHONY: test
test:  ## Run the test suite
	uv run pytest

.PHONY: check
check: lint types test  ## Run every quality gate

## Database

.PHONY: migrate
migrate:  ## Create missing tables
	uv run worker migrate

.PHONY: drop-all
drop-all:  ## Drop all tables (development only)
	uv run worker drop-all

## Dataseed

.PHONY: place-order
place-order:  ## Place an order without HTTP (REFERENCE=ORD-1A2B3C4D TOTAL=1999)
	uv run worker place-order --reference $(or $(REFERENCE),ORD-1A2B3C4D) --total $(or $(TOTAL),1999)

## Services

.PHONY: api
api:  ## Serve the API with reload
	uv run api

.PHONY: broker
broker:  ## Serve the broker process
	uv run broker

.PHONY: consume
consume:  ## Consume domain events in the foreground
	uv run worker consume

.PHONY: health
health:  ## Print the health report; exits 1 when not ready
	uv run worker health

.PHONY: drain
drain:  ## Print events seen on the channel (SECONDS=5)
	uv run worker drain --seconds $(or $(SECONDS),5)

## Releases

.PHONY: docker-build
docker-build:  ## Build the container image (TAG=latest)
	docker build -t yaddd-template:$(TAG) .

.PHONY: docker-release
docker-release: docker-build  ## Tag and push the image (IMAGE=<name> required, REGISTRY=docker.io, TAG=latest)
	@test -n "$(IMAGE)" || { echo "usage: make docker-release IMAGE=<name> [REGISTRY=docker.io] [TAG=latest]" >&2; exit 2; }
	docker tag yaddd-template:$(TAG) $(or $(REGISTRY),docker.io)/$(IMAGE):$(TAG)
	docker push $(or $(REGISTRY),docker.io)/$(IMAGE):$(TAG)
