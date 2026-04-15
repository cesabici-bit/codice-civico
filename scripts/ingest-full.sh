#!/usr/bin/env bash
# ==============================================================================
# Codice Civico — Full Ingest Pipeline
#
# Usage (from host):
#   docker compose -f docker-compose.prod.yml exec backend bash scripts/ingest-full.sh
#
# Usage (inside container):
#   bash scripts/ingest-full.sh
# ==============================================================================
set -euo pipefail

LOG_DIR="/app/data/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/ingest_${TIMESTAMP}.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

FAILURES=()

run_step() {
    local step_name="$1"; shift
    log "START: $step_name"
    if "$@" >> "$LOG_FILE" 2>&1; then
        log "OK: $step_name"
    else
        local exit_code=$?
        log "FAIL: $step_name (exit $exit_code) — continuing"
        FAILURES+=("$step_name")
    fi
}

log "=== Codice Civico Full Ingest — $TIMESTAMP ==="

# 1. Camera dei Deputati (SPARQL)
run_step "Camera SPARQL ingest" codicecivico ingest --source camera

# 2. Senato della Repubblica (SPARQL)
run_step "Senato SPARQL ingest" codicecivico ingest --source senato

# 3. Entity resolution (cross-chamber dedup)
run_step "Entity resolution" codicecivico entity-resolve

# 4. ANAC procurement
# First run: ingest historical data if ANAC_FROM_YEAR is set (e.g., ANAC_FROM_YEAR=2024)
# Recurring: ingest last 6 months (broader window to catch late publications)
if [ -n "${ANAC_FROM_YEAR:-}" ]; then
    log "ANAC: historical ingest from $ANAC_FROM_YEAR"
    CURRENT_YEAR=$(date +%Y)
    CURRENT_MONTH=$(date +%-m)
    for y in $(seq "$ANAC_FROM_YEAR" "$CURRENT_YEAR"); do
        END_MONTH=12
        if [ "$y" -eq "$CURRENT_YEAR" ]; then
            END_MONTH=$((CURRENT_MONTH - 1))
            [ "$END_MONTH" -lt 1 ] && continue
        fi
        for m in $(seq 1 "$END_MONTH"); do
            run_step "ANAC $y-$m" codicecivico ingest --source anac --year "$y" --month "$m"
        done
    done
else
    for offset in 6 5 4 3 2 1; do
        YEAR=$(date -d "-${offset} months" +%Y 2>/dev/null || date -v-${offset}m +%Y)
        MONTH=$(date -d "-${offset} months" +%-m 2>/dev/null || date -v-${offset}m +%-m)
        run_step "ANAC $YEAR-$MONTH" codicecivico ingest --source anac --year "$YEAR" --month "$MONTH"
    done
fi

# 5. Giustizia (Min. Giustizia Excel)
run_step "Giustizia Excel ingest" codicecivico ingest --source giustizia

# 6. NLP promise extraction
run_step "NLP promise pipeline" codicecivico nlp --pipeline promises

log "=== Ingest pipeline complete ==="
log "Total failures: ${#FAILURES[@]}"

if [ ${#FAILURES[@]} -gt 0 ]; then
    log "Failed steps: ${FAILURES[*]}"
    exit 1
fi

log "All steps succeeded."
