PY ?= python3
NAME ?=
OUTPUT ?=

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help
	@grep -E '^(## |[a-zA-Z_-]+:.*?## )' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} /^## / {printf "\n\033[1m%s\033[0m\n", substr($$0, 4); next} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## Releases

.PHONY: standalone
standalone:  ## Copy the template out of the monorepo (NAME=acme [OUTPUT=path])
	@test -n "$(NAME)" || { echo "usage: make standalone NAME=<project> [OUTPUT=<path>]" >&2; exit 2; }
	$(PY) scripts/standalone.py "$(NAME)" $(if $(OUTPUT),--output "$(OUTPUT)",)
