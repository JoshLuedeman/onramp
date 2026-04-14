#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# OnRamp — Enterprise Landing Zone Demo Script
#
# Drives the full OnRamp application flow end-to-end via the API:
#   1. Create a project
#   2. Answer all 24 questionnaire questions (enterprise-max complexity)
#   3. Generate enterprise landing zone architecture
#   4. Score against 5 compliance frameworks
#   5. Generate Bicep templates
#   6. Create a deployment plan
#
# Usage: ./demo.sh [--name "Project Name"] [API_BASE_URL]
#   Default project name: "Enterprise Landing Zone — <timestamp>"
#   Default API_BASE_URL: http://localhost:8000
#
# Requirements: curl, jq
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Parse arguments ─────────────────────────────────────────────
PROJECT_NAME=""
API="http://localhost:8000"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name|-n)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./demo.sh [--name \"Project Name\"] [API_BASE_URL]"
            echo "  --name, -n    Project name (default: auto-generated)"
            echo "  API_BASE_URL  Backend API URL (default: http://localhost:8000)"
            exit 0
            ;;
        *)
            API="$1"
            shift
            ;;
    esac
done

if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="Enterprise Landing Zone — $(date '+%Y-%m-%d %H:%M')"
fi

OUTPUT_DIR=$(mktemp -d -t onramp-demo-XXXXXX)

# ── Colors ──────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
RESET='\033[0m'

banner() { echo -e "\n${BOLD}${BLUE}═══════════════════════════════════════════════════${RESET}"; echo -e "${BOLD}${BLUE}  $1${RESET}"; echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════${RESET}"; }
step()   { echo -e "  ${GREEN}✓${RESET} $1"; }
info()   { echo -e "  ${DIM}$1${RESET}"; }
warn()   { echo -e "  ${YELLOW}⚠ $1${RESET}"; }
fail()   { echo -e "  ${RED}✗ $1${RESET}"; exit 1; }

# Update project status in the database
update_status() {
    local status="$1"
    curl -sf "${API}/api/projects/${PROJECT_ID}" \
        -X PUT \
        -H 'Content-Type: application/json' \
        -d "{\"status\": \"${status}\"}" > /dev/null 2>&1 \
        && info "Project status → ${status}" \
        || true
}

# ── Preflight ───────────────────────────────────────────────────
for cmd in curl jq; do
    command -v "$cmd" &>/dev/null || fail "$cmd is required but not installed"
done

banner "OnRamp Enterprise Landing Zone Demo"
echo -e "  ${DIM}API:     ${API}${RESET}"
echo -e "  ${DIM}Output:  ${OUTPUT_DIR}${RESET}"
echo ""

# Check API health
HEALTH=$(curl -sf "${API}/health" 2>/dev/null) || fail "API not reachable at ${API}/health — is the dev environment running?"
MODE=$(echo "$HEALTH" | jq -r '.mode')
DB=$(echo "$HEALTH" | jq -r '.database')
step "API healthy (mode: ${MODE}, database: ${DB})"

# ═══════════════════════════════════════════════════════════════
# STEP 1: Create Project
# ═══════════════════════════════════════════════════════════════
banner "Step 1 — Create Project"

PROJECT=$(curl -sf "${API}/api/projects/" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg name "$PROJECT_NAME" --arg desc "Full CAF enterprise-scale landing zone for a global financial services organization. 50+ subscriptions, hybrid identity, multi-region, maximum security and compliance." \
        '{name: $name, description: $desc}')") || fail "Failed to create project"

PROJECT_ID=$(echo "$PROJECT" | jq -r '.id')
step "Project created: ${PROJECT_ID}"
info "Name: $(echo "$PROJECT" | jq -r '.name')"
echo "$PROJECT" | jq '.' > "${OUTPUT_DIR}/01-project.json"

# ═══════════════════════════════════════════════════════════════
# STEP 2: Answer Questionnaire (24 questions)
# ═══════════════════════════════════════════════════════════════
banner "Step 2 — Enterprise Questionnaire"

# All answers — maximum complexity enterprise configuration
ANSWERS='{
    "org_name": "Contoso Global Financial",
    "org_size": "enterprise",
    "azure_experience": "none",
    "subscription_count": "50+",
    "primary_region": "eastus",
    "identity_provider": "hybrid",
    "pim_required": "yes",
    "mfa_requirement": "all_users",
    "management_group_strategy": "caf_recommended",
    "naming_convention": "caf_standard",
    "network_topology": "hub_spoke",
    "hybrid_connectivity": "both",
    "dns_strategy": "hybrid_dns",
    "security_level": "high",
    "siem_integration": "both",
    "monitoring_strategy": "hybrid",
    "backup_dr": "comprehensive",
    "tagging_strategy": ["environment", "cost_center", "owner", "application", "data_classification", "business_unit", "project"],
    "cost_management": "critical",
    "iac_tool": "bicep",
    "cicd_platform": "github_actions",
    "industry": "financial_services",
    "compliance_frameworks": ["soc2", "pci_dss", "nist_800_53", "iso_27001", "gdpr"],
    "data_residency": "us_only"
}'

# Walk through each question one at a time to show the adaptive flow
CURRENT_ANSWERS='{}'
QUESTION_NUM=0

while true; do
    RESPONSE=$(curl -sf "${API}/api/questionnaire/next" \
        -X POST \
        -H 'Content-Type: application/json' \
        -d "{\"answers\": ${CURRENT_ANSWERS}}") || fail "Questionnaire next failed"

    COMPLETE=$(echo "$RESPONSE" | jq -r '.complete')
    if [ "$COMPLETE" = "true" ]; then
        break
    fi

    QUESTION_NUM=$((QUESTION_NUM + 1))
    QID=$(echo "$RESPONSE" | jq -r '.question.id')
    QTEXT=$(echo "$RESPONSE" | jq -r '.question.text')
    QTYPE=$(echo "$RESPONSE" | jq -r '.question.type')
    CATEGORY=$(echo "$RESPONSE" | jq -r '.question.category')
    PROGRESS=$(echo "$RESPONSE" | jq -r '.progress.percent_complete')

    # Get the answer for this question from our answer map
    ANSWER=$(echo "$ANSWERS" | jq -c --arg qid "$QID" '.[$qid]')

    if [ "$ANSWER" = "null" ]; then
        warn "No answer defined for question: ${QID} — skipping"
        continue
    fi

    # Add this answer to current_answers
    CURRENT_ANSWERS=$(echo "$CURRENT_ANSWERS" | jq -c --arg qid "$QID" --argjson ans "$ANSWER" '. + {($qid): $ans}')

    # Display answer value nicely
    if echo "$ANSWER" | jq -e 'type == "array"' &>/dev/null; then
        DISPLAY_ANS=$(echo "$ANSWER" | jq -r 'join(", ")')
    else
        DISPLAY_ANS=$(echo "$ANSWER" | jq -r '.')
    fi

    step "[${QUESTION_NUM}/24] ${CYAN}${CATEGORY}${RESET} → ${QTEXT}"
    info "Answer: ${DISPLAY_ANS}  (${PROGRESS}% complete)"
done

step "Questionnaire complete — all ${QUESTION_NUM} questions answered"
echo "$CURRENT_ANSWERS" | jq '.' > "${OUTPUT_DIR}/02-answers.json"
update_status "questionnaire_complete"

# Save questionnaire state to project
curl -sf "${API}/api/questionnaire/state/save" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "{\"project_id\": \"${PROJECT_ID}\", \"answers\": ${CURRENT_ANSWERS}}" > /dev/null 2>&1 \
    && step "Answers saved to project ${PROJECT_ID}" \
    || info "State save skipped (endpoint may not persist in dev mode)"

# ═══════════════════════════════════════════════════════════════
# STEP 3: Generate Architecture
# ═══════════════════════════════════════════════════════════════
banner "Step 3 — Generate Enterprise Architecture"

ARCH_RESPONSE=$(curl -sf "${API}/api/architecture/generate" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "{
        \"answers\": ${CURRENT_ANSWERS},
        \"use_archetype\": true,
        \"project_id\": \"${PROJECT_ID}\"
    }") || fail "Architecture generation failed"

ARCHITECTURE=$(echo "$ARCH_RESPONSE" | jq '.architecture')
ARCH_NAME=$(echo "$ARCHITECTURE" | jq -r '.name')
ARCH_DESC=$(echo "$ARCHITECTURE" | jq -r '.description')
NUM_SUBS=$(echo "$ARCHITECTURE" | jq '.subscriptions | length')
NUM_MG=$(echo "$ARCHITECTURE" | jq '[.management_groups | .. | objects | select(.display_name)] | length')
ESTIMATED_COST=$(echo "$ARCHITECTURE" | jq -r '.estimated_monthly_cost_usd // "N/A"')

step "Architecture: ${BOLD}${ARCH_NAME}${RESET}"
info "Description: ${ARCH_DESC}"
info "Management Groups: ${NUM_MG}"
info "Subscriptions: ${NUM_SUBS}"
info "Estimated Monthly Cost: \$${ESTIMATED_COST}"

# Show management group hierarchy
echo -e "\n  ${BOLD}Management Group Hierarchy:${RESET}"
echo "$ARCHITECTURE" | jq -r '
  def show(prefix):
    to_entries[] |
    "  \(prefix)├── \(.value.display_name)" ,
    (.value.children | if . then show("  \(prefix)│   ") else empty end);
  .management_groups.root |
  "  └── \(.display_name)",
  (.children | show("    "))
' 2>/dev/null || info "(hierarchy display not available)"

# Show subscriptions
echo -e "\n  ${BOLD}Subscriptions:${RESET}"
echo "$ARCHITECTURE" | jq -r '.subscriptions[] | "  │ \(.name) — \(.purpose) [$\(.budget_usd // "N/A")/mo]"' 2>/dev/null || true

echo "$ARCHITECTURE" | jq '.' > "${OUTPUT_DIR}/03-architecture.json"
step "Architecture saved to ${OUTPUT_DIR}/03-architecture.json"
update_status "architecture_generated"

# ═══════════════════════════════════════════════════════════════
# STEP 4: Compliance Scoring
# ═══════════════════════════════════════════════════════════════
banner "Step 4 — Compliance Scoring (5 Frameworks)"

FRAMEWORKS='["soc2", "pci_dss", "nist_800_53", "iso_27001", "gdpr"]'

SCORING=$(curl -sf "${API}/api/scoring/evaluate" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "{
        \"architecture\": ${ARCHITECTURE},
        \"frameworks\": ${FRAMEWORKS},
        \"project_id\": \"${PROJECT_ID}\"
    }") || fail "Compliance scoring failed"

OVERALL=$(echo "$SCORING" | jq -r '.overall_score')
TOTAL_CONTROLS=$(echo "$SCORING" | jq -r '.total_controls')
CONTROLS_MET=$(echo "$SCORING" | jq -r '.controls_met')
CONTROLS_PARTIAL=$(echo "$SCORING" | jq -r '.controls_partial')
CONTROLS_GAP=$(echo "$SCORING" | jq -r '.controls_gap')

step "Overall Compliance Score: ${BOLD}${OVERALL}%${RESET}"
info "Total Controls: ${TOTAL_CONTROLS} | Met: ${CONTROLS_MET} | Partial: ${CONTROLS_PARTIAL} | Gaps: ${CONTROLS_GAP}"

echo -e "\n  ${BOLD}Framework Scores:${RESET}"
echo "$SCORING" | jq -r '.frameworks[] | "  │ \(.name) (\(.full_name)): \(.score)% — \(.status) [met: \(.controls_met), partial: \(.controls_partial), gap: \(.controls_gap)]"'

# Show top gaps
GAP_COUNT=$(echo "$SCORING" | jq '[.frameworks[].gaps[]] | length')
if [ "$GAP_COUNT" -gt 0 ]; then
    echo -e "\n  ${BOLD}${YELLOW}Top Compliance Gaps:${RESET}"
    echo "$SCORING" | jq -r '
        [.frameworks[] | .name as $fw | .gaps[] | {fw: $fw, control: .control_id, name: .control_name, severity: .severity}]
        | sort_by(.severity)
        | reverse
        | .[0:10][]
        | "  │ [\(.severity | ascii_upcase)] \(.fw)/\(.control) — \(.name)"
    '
fi

echo "$SCORING" | jq '.' > "${OUTPUT_DIR}/04-compliance.json"
step "Compliance report saved to ${OUTPUT_DIR}/04-compliance.json"
update_status "compliance_scored"

# ═══════════════════════════════════════════════════════════════
# STEP 5: Generate Bicep Templates
# ═══════════════════════════════════════════════════════════════
banner "Step 5 — Generate Bicep Templates"

BICEP=$(curl -sf "${API}/api/bicep/generate" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "{\"architecture\": ${ARCHITECTURE}, \"project_id\": \"${PROJECT_ID}\"}") || fail "Bicep generation failed"

NUM_FILES=$(echo "$BICEP" | jq '.files | length')
TOTAL_BYTES=$(echo "$BICEP" | jq '[.files[].size_bytes] | add')

step "Generated ${NUM_FILES} Bicep template files (${TOTAL_BYTES} bytes total)"

echo -e "\n  ${BOLD}Generated Templates:${RESET}"
mkdir -p "${OUTPUT_DIR}/bicep"
echo "$BICEP" | jq -r '.files[] | "\(.name) \(.size_bytes)"' | while read -r FNAME SIZE; do
    echo -e "  │ ${FNAME} (${SIZE} bytes)"
    # Create subdirectories if the template path contains them
    FDIR=$(dirname "${OUTPUT_DIR}/bicep/${FNAME}")
    mkdir -p "$FDIR"
    echo "$BICEP" | jq -r --arg f "$FNAME" '.files[] | select(.name == $f) | .content' > "${OUTPUT_DIR}/bicep/${FNAME}"
done

echo "$BICEP" | jq '.' > "${OUTPUT_DIR}/05-bicep.json"
step "Bicep templates saved to ${OUTPUT_DIR}/bicep/"
update_status "bicep_ready"

# ═══════════════════════════════════════════════════════════════
# STEP 6: Create Deployment Plan
# ═══════════════════════════════════════════════════════════════
banner "Step 6 — Create Deployment Plan"

# Generate realistic subscription IDs for the enterprise
SUB_IDS=$(echo "$ARCHITECTURE" | jq -c '[.subscriptions[].name]')

DEPLOYMENT=$(curl -sf "${API}/api/deployment/create" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "{
        \"architecture\": ${ARCHITECTURE},
        \"project_id\": \"${PROJECT_ID}\",
        \"subscription_ids\": ${SUB_IDS}
    }") || fail "Deployment creation failed"

DEPLOY_ID=$(echo "$DEPLOYMENT" | jq -r '.id')
DEPLOY_STATUS=$(echo "$DEPLOYMENT" | jq -r '.status')
NUM_STEPS=$(echo "$DEPLOYMENT" | jq '.steps | length')
DEPLOY_PROGRESS=$(echo "$DEPLOYMENT" | jq -r '.progress')

step "Deployment plan created: ${DEPLOY_ID}"
info "Status: ${DEPLOY_STATUS} | Steps: ${NUM_STEPS} | Progress: ${DEPLOY_PROGRESS}%"

echo -e "\n  ${BOLD}Deployment Steps:${RESET}"
echo "$DEPLOYMENT" | jq -r '.steps[] | "  │ [\(.status)] \(.name) — \(.resource_type)"'

echo -e "\n  ${BOLD}Target Subscriptions:${RESET}"
echo "$DEPLOYMENT" | jq -r '.subscription_ids[] | "  │ \(.)"'

echo "$DEPLOYMENT" | jq '.' > "${OUTPUT_DIR}/06-deployment.json"
step "Deployment plan saved to ${OUTPUT_DIR}/06-deployment.json"

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════
banner "Demo Complete — Summary"

echo -e "  ${BOLD}Project:${RESET}           ${PROJECT_NAME}"
echo -e "  ${BOLD}Project ID:${RESET}        ${PROJECT_ID}"
echo -e "  ${BOLD}Archetype:${RESET}         ${ARCH_NAME}"
echo -e "  ${BOLD}Subscriptions:${RESET}     ${NUM_SUBS}"
echo -e "  ${BOLD}Management Groups:${RESET} ${NUM_MG}"
echo -e "  ${BOLD}Compliance Score:${RESET}  ${OVERALL}% across ${FRAMEWORKS}"
echo -e "  ${BOLD}Bicep Templates:${RESET}   ${NUM_FILES} files"
echo -e "  ${BOLD}Deployment Steps:${RESET}  ${NUM_STEPS} steps (${DEPLOY_STATUS})"
echo -e "  ${BOLD}Est. Monthly Cost:${RESET} \$${ESTIMATED_COST}"
echo ""
echo -e "  ${BOLD}Output Directory:${RESET}  ${OUTPUT_DIR}"
echo -e "  ${DIM}├── 01-project.json        Project metadata${RESET}"
echo -e "  ${DIM}├── 02-answers.json        Questionnaire answers${RESET}"
echo -e "  ${DIM}├── 03-architecture.json   Full architecture${RESET}"
echo -e "  ${DIM}├── 04-compliance.json     Compliance scoring${RESET}"
echo -e "  ${DIM}├── 05-bicep.json          Bicep generation response${RESET}"
echo -e "  ${DIM}├── 06-deployment.json     Deployment plan${RESET}"
echo -e "  ${DIM}└── bicep/                 Individual Bicep files${RESET}"
echo ""
echo -e "  ${GREEN}${BOLD}✓ Full enterprise landing zone generated successfully${RESET}"
echo ""
