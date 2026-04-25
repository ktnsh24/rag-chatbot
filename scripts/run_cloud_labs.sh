#!/usr/bin/env bash
# =============================================================================
# 🚀 Cloud Lab Runner — rag-chatbot
# =============================================================================
# terraform apply → run all labs → terraform destroy
#
# Usage:
#   ./scripts/run_cloud_labs.sh --provider aws --email you@email.com
#   ./scripts/run_cloud_labs.sh --provider azure --email you@email.com
#   ./scripts/run_cloud_labs.sh --provider aws --email you@email.com --cost-limit 15
#   ./scripts/run_cloud_labs.sh --provider aws --test-config scripts/config/test-data/my-doc.yaml
#   ./scripts/run_cloud_labs.sh --dry-run --provider aws
#
# Author: Ketan (private — personal use only)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Credential isolation — prevents leaking work SSO creds into personal runs
# ---------------------------------------------------------------------------
if [[ "${AWS_CREDS_ISOLATED:-}" != "1" ]]; then
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN \
          AWS_SECURITY_TOKEN AWS_CREDENTIAL_EXPIRATION AWS_ROLE_ARN \
          AWS_ROLE_SESSION_NAME AWS_WEB_IDENTITY_TOKEN_FILE 2>/dev/null || true
    export AWS_PROFILE="${AWS_PROFILE:-personal}"
    export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-central-1}"
    export PYTHONDONTWRITEBYTECODE=1
    find "$(dirname "$0")/../src" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>&1 || true)
    if [[ "$ACCOUNT_ID" == "$EXPECTED_PERSONAL_ACCOUNT_ID" ]]; then
        echo "✅ Account verified: $ACCOUNT_ID (personal)"
    else
        echo "⚠️  AWS account: $ACCOUNT_ID (verify this is correct)"
    fi
    export AWS_CREDS_ISOLATED=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REPO_NAME="rag-chatbot"
PORT=8000
EXPECTED_LABS=31  # Individual run experiments across Phase 1-5

# Defaults
PROVIDER=""
EMAIL=""
BUDGET=5
TIMEOUT_MINUTES=120
DRY_RUN=false
SKIP_DESTROY=false
TEST_CONFIG=""

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GREEN}[✅ $(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[⚠️  $(date +%H:%M:%S)]${NC} $*"; }
fail() { echo -e "${RED}[❌ $(date +%H:%M:%S)]${NC} $*"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --provider)     PROVIDER="$2";        shift 2 ;;
        --email)        EMAIL="$2";           shift 2 ;;
        --budget)       BUDGET="$2";          shift 2 ;;
        --cost-limit)   BUDGET="$2";          shift 2 ;;
        --timeout)      TIMEOUT_MINUTES="$2"; shift 2 ;;
        --dry-run)      DRY_RUN=true;         shift ;;
        --skip-destroy) SKIP_DESTROY=true;    shift ;;
        --test-config)  TEST_CONFIG="$2";      shift 2 ;;
        *) fail "Unknown flag: $1"; exit 1 ;;
    esac
done

if [[ -z "$PROVIDER" ]]; then
    fail "Usage: $0 --provider <aws|azure> --email <you@email.com>"
    exit 1
fi
if [[ "$PROVIDER" != "aws" && "$PROVIDER" != "azure" ]]; then
    fail "Provider must be 'aws' or 'azure'"; exit 1
fi
[[ -z "$EMAIL" ]] && warn "No --email provided. Budget alerts won't be sent."

INFRA_DIR="$REPO_DIR/infra/$PROVIDER"
RESULTS_DIR="$SCRIPT_DIR/lab_results/$PROVIDER"
REPORT_FILE="$RESULTS_DIR/cloud-lab-report.txt"

# ---------------------------------------------------------------------------
# Cost checker
# ---------------------------------------------------------------------------
check_cost() {
    local cost="0"
    if [[ "$PROVIDER" == "aws" ]]; then
        cost=$(aws ce get-cost-and-usage \
            --time-period "Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d)" \
            --granularity MONTHLY --metrics BlendedCost \
            --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
            --output text 2>/dev/null || echo "0")
    else
        cost=$(az consumption usage list \
            --start-date "$(date +%Y-%m-01)" --end-date "$(date +%Y-%m-%d)" \
            --query "sum([].pretaxCost)" --output tsv 2>/dev/null || echo "0")
    fi

    local exceeded
    exceeded=$(awk "BEGIN { print ($cost >= $BUDGET) ? 1 : 0 }")
    if [[ "$exceeded" == "1" ]]; then
        fail "💰 BUDGET EXCEEDED! €$cost >= €$BUDGET — triggering cleanup"
        return 1
    fi
    local pct
    pct=$(awk "BEGIN { printf \"%.0f\", ($cost / $BUDGET) * 100 }")
    log "💰 Budget: €$cost / €$BUDGET (${pct}%)"
}

# ---------------------------------------------------------------------------
# Terraform
# ---------------------------------------------------------------------------
tf_apply() {
    log "🏗️  Terraform init + apply ($PROVIDER)..."
    if $DRY_RUN; then log "[DRY RUN] terraform apply"; return 0; fi
    terraform -chdir="$INFRA_DIR" init -input=false -no-color
    terraform -chdir="$INFRA_DIR" apply -auto-approve -input=false -no-color \
        -var="alert_email=${EMAIL:-noop@example.com}" \
        -var="cost_limit_eur=$BUDGET"
    ok "Infrastructure deployed"

    # Inject Terraform outputs into .env for the app server
    if [[ "$PROVIDER" == "azure" ]]; then
        log "Injecting Azure Terraform outputs into .env..."
        local cosmos_endpoint cosmos_key storage_name storage_key
        cosmos_endpoint=$(terraform -chdir="$INFRA_DIR" output -raw cosmos_db_endpoint)
        cosmos_key=$(terraform -chdir="$INFRA_DIR" output -raw cosmos_db_primary_key)
        storage_name=$(terraform -chdir="$INFRA_DIR" output -raw storage_account_name)
        storage_key=$(terraform -chdir="$INFRA_DIR" output -raw storage_account_primary_key)

        # Update .env in-place (backup first)
        local envfile="$REPO_DIR/.env"
        cp "$envfile" "$envfile.bak"
        sed -i "s|^AZURE_COSMOS_ENDPOINT=.*|AZURE_COSMOS_ENDPOINT=$cosmos_endpoint|" "$envfile"
        sed -i "s|^AZURE_COSMOS_KEY=.*|AZURE_COSMOS_KEY=$cosmos_key|" "$envfile"
        sed -i "s|^AZURE_STORAGE_ACCOUNT_NAME=.*|AZURE_STORAGE_ACCOUNT_NAME=$storage_name|" "$envfile"
        sed -i "s|^AZURE_STORAGE_ACCOUNT_KEY=.*|AZURE_STORAGE_ACCOUNT_KEY=$storage_key|" "$envfile"
        ok "Azure credentials injected into .env"
    fi
}

tf_destroy() {
    if $SKIP_DESTROY; then
        warn "⚠️ --skip-destroy: resources STILL RUNNING and COSTING MONEY!"
        return
    fi
    log "💣 Terraform destroy ($PROVIDER)..."
    if $DRY_RUN; then log "[DRY RUN] terraform destroy"; return 0; fi
    terraform -chdir="$INFRA_DIR" destroy -auto-approve -input=false -no-color \
        -var="alert_email=${EMAIL:-noop@example.com}" \
        -var="cost_limit_eur=$BUDGET" || true
    ok "Infrastructure destroyed"
}

# ---------------------------------------------------------------------------
# App server management
# ---------------------------------------------------------------------------
APP_PID=""

start_server() {
    log "🖥️  Starting rag-chatbot server on port $PORT..."
    if $DRY_RUN; then log "[DRY RUN] poetry run start"; return 0; fi
    (
        cd "$REPO_DIR"
        poetry run uvicorn src.main:app --host 0.0.0.0 --port "$PORT" \
            > "$RESULTS_DIR/server.log" 2>&1
    ) &
    APP_PID=$!

    # Wait for health
    local retries=30
    while (( retries > 0 )); do
        if curl -s "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
            ok "Server is up (PID=$APP_PID)"
            return 0
        fi
        # Check if process died
        if ! kill -0 "$APP_PID" 2>/dev/null; then
            fail "Server process died. Check $RESULTS_DIR/server.log"
            cat "$RESULTS_DIR/server.log" | tail -20
            return 1
        fi
        sleep 2
        retries=$((retries - 1))
    done
    fail "Server did not start within 60s"
    return 1
}

stop_server() {
    if [[ -n "$APP_PID" ]] && kill -0 "$APP_PID" 2>/dev/null; then
        log "Stopping server (PID=$APP_PID)..."
        kill "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
        APP_PID=""
    fi
}

# Cleanup on ANY exit (Ctrl+C, error, normal)
cleanup() {
    stop_server
    # Restore original .env
    [[ -f "$REPO_DIR/.env.bak" ]] && mv "$REPO_DIR/.env.bak" "$REPO_DIR/.env"
    tf_destroy
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Lab result scanner
# ---------------------------------------------------------------------------
scan_results() {
    local results_dir="$1"
    local total=0 passed=0 failed=0 missing=0

    echo ""
    echo "=========================================="
    echo "  📋 Lab Completion Report — $REPO_NAME"
    echo "  Provider: $PROVIDER"
    echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""

    # Try raw-results.json from latest timestamped subdir first
    local latest_raw=""
    if [[ -L "$results_dir/latest" ]]; then
        latest_raw="$results_dir/$(readlink "$results_dir/latest")/raw-results.json"
    fi
    if [[ -z "$latest_raw" || ! -f "$latest_raw" ]]; then
        # Fallback: find most recent timestamped subdir
        latest_raw=$(find "$results_dir" -name raw-results.json -type f 2>/dev/null | sort -r | head -1)
    fi

    if [[ -n "$latest_raw" && -f "$latest_raw" ]]; then
        # Parse raw-results.json for run experiments
        while IFS='|' read -r eid status exp_passed; do
            total=$((total + 1))
            if [[ "$exp_passed" == "true" || ("$exp_passed" == "null" && "$status" == "success") ]]; then
                passed=$((passed + 1))
                echo "  ✅ lab-$eid"
            else
                failed=$((failed + 1))
                echo "  ❌ lab-$eid"
            fi
        done < <(python3 -c "
import json, sys
d = json.load(open('$latest_raw'))
for r in d.get('results', []):
    if r.get('experiment_type') != 'run': continue
    eid = r.get('experiment_id', '?')
    st = r.get('status', 'not_run')
    p = r.get('passed')
    print(f'{eid}|{st}|{str(p).lower()}')
" 2>/dev/null)
    else
        # Fallback: scan individual lab-*.json files
        for json_file in "$results_dir"/lab-*.json; do
            [[ -f "$json_file" ]] || continue
            total=$((total + 1))
            local lab_name
            lab_name=$(basename "$json_file" .json)
            local lab_passed
            lab_passed=$(python3 -c "import json; d=json.load(open('$json_file')); print('PASS' if d.get('passed', False) else 'FAIL')" 2>/dev/null || echo "ERROR")
            if [[ "$lab_passed" == "PASS" ]]; then
                passed=$((passed + 1))
                echo "  ✅ $lab_name"
            else
                failed=$((failed + 1))
                echo "  ❌ $lab_name"
            fi
        done
    fi

    missing=$((EXPECTED_LABS - total))

    echo ""
    echo "  ─────────────────────────────────"
    echo "  Total expected:  $EXPECTED_LABS"
    echo "  Ran:             $total"
    echo "  Passed:          $passed"
    echo "  Failed:          $failed"
    echo "  Not run:         $missing"
    echo "  ─────────────────────────────────"

    if [[ $missing -gt 0 ]]; then
        echo ""
        warn "⚠️ $missing labs did NOT run. Possible causes:"
        echo "     - Budget limit reached mid-run"
        echo "     - Timeout exceeded (${TIMEOUT_MINUTES} min)"
        echo "     - Server crashed or endpoint not available"
        echo "     - Phase skipped (e.g. --skip-phase3)"
    fi

    if [[ $failed -gt 0 ]]; then
        echo ""
        warn "⚠️ $failed labs FAILED. Check individual JSON files in:"
        echo "     $results_dir/"
    fi

    if [[ $total -eq $EXPECTED_LABS && $passed -eq $EXPECTED_LABS ]]; then
        echo ""
        ok "🎉 ALL $EXPECTED_LABS labs passed on $PROVIDER!"
    fi

    echo ""
    echo "=========================================="
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo "=========================================="
    echo "  🚀 Cloud Lab Runner — $REPO_NAME"
    echo "=========================================="
    echo "  Provider:   $PROVIDER"
    echo "  Budget:     €$BUDGET"
    echo "  Timeout:    ${TIMEOUT_MINUTES} min"
    echo "  Email:      ${EMAIL:-<none>}"
    echo "  Dry run:    $DRY_RUN"
    echo "  Test config: ${TEST_CONFIG:-<default: test-policy.yaml>}"
    echo "  Labs:       $EXPECTED_LABS expected"
    echo "=========================================="
    echo ""

    local start_time=$SECONDS

    # Phase 1: Deploy
    log "━━━ Phase 1: Deploy infrastructure ━━━"
    tf_apply

    # Budget check before labs
    if ! $DRY_RUN; then check_cost || exit 1; fi

    # Start the application server
    log "━━━ Starting application server ━━━"
    mkdir -p "$RESULTS_DIR"
    start_server || exit 1

    # Phase 2: Run labs
    log "━━━ Phase 2: Run hands-on labs ━━━"
    local lab_exit=0
    local test_config_flag=""
    [[ -n "$TEST_CONFIG" ]] && test_config_flag="--test-config $TEST_CONFIG"
    if $DRY_RUN; then
        log "[DRY RUN] poetry run python scripts/run_all_labs.py --env $PROVIDER $test_config_flag"
    else
        mkdir -p "$RESULTS_DIR"
        (
            cd "$REPO_DIR"
            timeout $((TIMEOUT_MINUTES * 60)) poetry run python scripts/run_all_labs.py \
                --env "$PROVIDER" $test_config_flag 2>&1 | tee "$RESULTS_DIR/run_output.log"
        ) || lab_exit=$?

        if [[ $lab_exit -eq 124 ]]; then
            warn "⏰ Labs timed out after ${TIMEOUT_MINUTES} minutes"
        elif [[ $lab_exit -ne 0 ]]; then
            warn "Labs exited with code $lab_exit"
        fi

        # Budget check after labs
        check_cost || true
    fi

    # Phase 3: Destroy (handled by trap)
    log "━━━ Phase 3: Cleanup (terraform destroy) ━━━"

    # Phase 4: Completion report
    if ! $DRY_RUN; then
        scan_results "$RESULTS_DIR" | tee "$REPORT_FILE"
    fi

    local elapsed=$(( (SECONDS - start_time) / 60 ))
    log "Total time: ${elapsed} minutes"
}

main
