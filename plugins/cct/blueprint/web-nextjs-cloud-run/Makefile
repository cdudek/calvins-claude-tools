# Development database: README.md, "Development database". The logic is in
# scripts/dev-db.sh; these targets only pass the settings through.

CLOUDSDK_ACTIVE_CONFIG_NAME ?= GCP_PROJECT_ID
DEV_DB_PORT ?= 5432
export CLOUDSDK_ACTIVE_CONFIG_NAME DEV_DB_PORT NAME TF_REF TF_REPO SECRETS_FILE

.DEFAULT_GOAL := help
.PHONY: help dev-env dev-db dev-db-proxy dev-db-stop dev-db-psql test-dev-db-name

help: ## List the targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-z-]+:.*## / { printf "  make %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

dev-env: ## Staging secrets (Google and GitHub OAuth) from terraform-infra into .env.local; TF_REF=<branch> until they reach main
	@sh scripts/dev-env.sh

dev-db: ## Your database <firstname_lastname>_dev: register (first run) or connect, write .env.local, migrate
	@sh scripts/dev-db.sh up

dev-db-proxy: ## Start the Cloud SQL Auth Proxy in the background (port DEV_DB_PORT, default 5432)
	@sh scripts/dev-db.sh proxy

dev-db-stop: ## Stop the proxy
	@sh scripts/dev-db.sh stop

dev-db-psql: ## Open psql on your database (starts the proxy if needed)
	@sh scripts/dev-db.sh psql

test-dev-db-name: ## Check the name derivation (also part of npm test)
	@npx vitest run tests/dev-db.test.ts
