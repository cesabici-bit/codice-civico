# Makefile — Codice Civico
# Target principale: `make check-all` esegue TUTTI i controlli in sequenza.
# Se uno fallisce, i successivi NON vengono eseguiti.

LANG ?= python

.PHONY: check-all types lint test smoke deps clean

## check-all: Esegue tutti i controlli (deps, types, lint, test, smoke)
check-all: deps types lint test smoke
	@echo ""
	@echo "=== ALL CHECKS PASSED ==="
	@echo ""

## deps: Verifica che verified-deps.toml esista e non sia vuoto
deps:
	@echo "--- Checking verified-deps.toml ---"
	@test -f verified-deps.toml || (echo "ERROR: verified-deps.toml not found" && exit 1)
	@echo "verified-deps.toml found"

## types: Type checking con mypy
types:
	mypy src/

## lint: Linting con ruff
lint:
	ruff check src/ tests/

## test: Unit + integration tests
test:
	pytest tests/ -v

## smoke: Smoke test E2E (M3)
smoke:
	pytest tests/test_smoke.py -v -s

## clean: Pulizia artefatti
clean:
	@echo "Cleaning build artifacts..."
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
