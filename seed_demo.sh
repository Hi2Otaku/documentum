#!/bin/bash
# Seed comprehensive demo data for Documentum Workflow Clone
# Covers demo tests 2-7: Browse, Relationships, Search, Smart Folders, Permissions, ACL
set -e

BASE="http://localhost:8000/api/v1"

# Helper: extract ID from JSON response
id_of() { grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4; }

echo "=========================================="
echo "  SEEDING DEMO DATA"
echo "=========================================="

# ── Auth ──────────────────────────────────────────────
TOKEN=$(curl -s "$BASE/auth/login" -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
AUTH="Authorization: Bearer $TOKEN"
echo "✓ Authenticated as admin"

# ── Users ─────────────────────────────────────────────
echo ""
echo "=== Creating Users ==="
JOHN_ID=$(curl -s "$BASE/users/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"username":"john.legal","password":"demo1234","email":"john@example.com"}' | id_of)
SARAH_ID=$(curl -s "$BASE/users/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"username":"sarah.finance","password":"demo1234","email":"sarah@example.com"}' | id_of)
MIKE_ID=$(curl -s "$BASE/users/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"username":"mike.director","password":"demo1234","email":"mike@example.com"}' | id_of)
echo "  john.legal=$JOHN_ID"
echo "  sarah.finance=$SARAH_ID"
echo "  mike.director=$MIKE_ID"

# ── Cabinets & Folders ────────────────────────────────
echo ""
echo "=== Creating Cabinets & Folders ==="

# Legal Department cabinet with subfolders
LEGAL_CAB=$(curl -s "$BASE/folders/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Legal Department","description":"All legal documents, contracts, and agreements"}' | id_of)
ACTIVE_CONTRACTS=$(curl -s "$BASE/folders/$LEGAL_CAB/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Active Contracts","description":"Currently active contracts and agreements"}' | id_of)
PENDING_REVIEW=$(curl -s "$BASE/folders/$LEGAL_CAB/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Pending Review","description":"Contracts awaiting legal review"}' | id_of)
TEMPLATES_FOLDER=$(curl -s "$BASE/folders/$LEGAL_CAB/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Contract Templates","description":"Standard contract templates"}' | id_of)
echo "  Legal Department: Active Contracts, Pending Review, Contract Templates"

# Finance Department cabinet with subfolders
FINANCE_CAB=$(curl -s "$BASE/folders/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Finance Department","description":"Financial reports, analyses, and budgets"}' | id_of)
DEAL_ANALYSES=$(curl -s "$BASE/folders/$FINANCE_CAB/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Deal Analyses","description":"Financial analyses for business deals"}' | id_of)
BUDGETS=$(curl -s "$BASE/folders/$FINANCE_CAB/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Budgets","description":"Annual and quarterly budgets"}' | id_of)
echo "  Finance Department: Deal Analyses, Budgets"

# HR Department cabinet
HR_CAB=$(curl -s "$BASE/folders/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"HR Department","description":"Human resources policies and employee documents"}' | id_of)
POLICIES=$(curl -s "$BASE/folders/$HR_CAB/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Policies","description":"Company policies and handbooks"}' | id_of)
echo "  HR Department: Policies"

# ── Documents ─────────────────────────────────────────
echo ""
echo "=== Uploading Documents ==="

# Legal docs
cat > /tmp/contract_acme.txt << 'DOCEOF'
PARTNERSHIP AGREEMENT

Between Acme Corporation ("Acme") and Widget Industries ("Widget")

TERMS: This agreement establishes a 3-year exclusive distribution partnership
for the Asia-Pacific region. Acme grants Widget exclusive rights to distribute
all Acme products in the designated territory.

KEY PROVISIONS:
1. Annual minimum order quantity: 500 units
2. Revenue sharing: 70/30 split (Acme/Widget)
3. Marketing support: Acme provides $50,000 annual co-marketing fund
4. Quarterly business reviews required
5. Non-compete clause for competing product lines

EFFECTIVE DATE: January 1, 2026
EXPIRY DATE: December 31, 2028

Signed by authorized representatives of both parties.
DOCEOF
DOC_CONTRACT=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Acme Partnership Agreement" -F "author=Legal Team" \
  -F "file=@/tmp/contract_acme.txt;type=text/plain" | id_of)
echo "  Acme Partnership Agreement=$DOC_CONTRACT"

cat > /tmp/financials_acme.txt << 'DOCEOF'
FINANCIAL ANALYSIS: ACME PARTNERSHIP DEAL

Prepared by: Finance Department
Date: March 2026

EXECUTIVE SUMMARY:
The proposed Acme partnership represents a significant revenue opportunity
with projected annual revenue of $1.2M and an ROI of 340%.

REVENUE PROJECTIONS:
- Year 1: $1,200,000 (conservative estimate)
- Year 2: $1,500,000 (15% growth)
- Year 3: $1,800,000 (20% growth)

COST ANALYSIS:
- Setup costs: $150,000 (one-time)
- Annual operations: $200,000
- Marketing co-investment: $50,000/year

RISK ASSESSMENT: LOW
- Acme has 15-year track record
- Asia-Pacific market growing 12% annually
- Break-even expected within 8 months

RECOMMENDATION: PROCEED with partnership execution.
DOCEOF
DOC_FINANCIAL=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Acme Deal Financial Analysis" -F "author=Sarah Chen" \
  -F "file=@/tmp/financials_acme.txt;type=text/plain" | id_of)
echo "  Acme Deal Financial Analysis=$DOC_FINANCIAL"

cat > /tmp/nda_template.txt << 'DOCEOF'
NON-DISCLOSURE AGREEMENT TEMPLATE

This Non-Disclosure Agreement ("NDA") is entered into by and between:
Party A: [COMPANY NAME] ("Disclosing Party")
Party B: [COUNTERPARTY] ("Receiving Party")

PURPOSE: To protect confidential information shared during business discussions.

CONFIDENTIAL INFORMATION includes but is not limited to:
- Trade secrets, proprietary technology
- Financial data, business plans
- Customer lists, supplier agreements
- Product roadmaps and development plans

TERM: This NDA shall remain in effect for 2 years from the date of execution.

OBLIGATIONS: The Receiving Party agrees to maintain strict confidentiality.
DOCEOF
DOC_NDA=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=NDA Template v3.2" -F "author=Legal Team" \
  -F "file=@/tmp/nda_template.txt;type=text/plain" | id_of)
echo "  NDA Template=$DOC_NDA"

cat > /tmp/amendment.txt << 'DOCEOF'
AMENDMENT TO PARTNERSHIP AGREEMENT

Reference: Acme Partnership Agreement dated January 1, 2026

This amendment modifies Section 1 (Minimum Order Quantity):
- Previous: 500 units per annum
- Amended: 400 units per annum for Year 1, increasing to 500 in Year 2

All other terms remain unchanged.

Effective Date: April 1, 2026
DOCEOF
DOC_AMENDMENT=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Acme Agreement Amendment #1" -F "author=John Smith" \
  -F "file=@/tmp/amendment.txt;type=text/plain" | id_of)
echo "  Acme Amendment=$DOC_AMENDMENT"

# Finance docs
cat > /tmp/budget_q2.txt << 'DOCEOF'
Q2 2026 BUDGET - FINANCE DEPARTMENT

OPERATING BUDGET: $450,000

BREAKDOWN:
- Salaries & Benefits: $280,000
- Software Licenses: $45,000
- Travel & Entertainment: $25,000
- Professional Services: $60,000
- Office Supplies: $10,000
- Contingency: $30,000

CAPITAL EXPENDITURE:
- New ERP module: $120,000
- Hardware refresh: $35,000

TOTAL: $605,000

Approved by: Mike Director, VP Operations
DOCEOF
DOC_BUDGET=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Q2 2026 Budget - Finance" -F "author=Sarah Chen" \
  -F "file=@/tmp/budget_q2.txt;type=text/plain" | id_of)
echo "  Q2 Budget=$DOC_BUDGET"

# HR docs
cat > /tmp/employee_handbook.txt << 'DOCEOF'
EMPLOYEE HANDBOOK 2026

Chapter 1: Welcome and Company Overview
Our company values: Innovation, Integrity, Collaboration, Excellence.

Chapter 2: Employment Policies
- Working hours: 9:00 AM - 5:30 PM
- Remote work: Hybrid model (3 days office, 2 days remote)
- Vacation: 20 days per year
- Sick leave: 10 days per year

Chapter 3: Code of Conduct
All employees are expected to maintain professional conduct.
Harassment, discrimination, and retaliation are strictly prohibited.

Chapter 4: Benefits
- Health insurance (medical, dental, vision)
- 401(k) with 5% company match
- Professional development budget: $2,000/year
DOCEOF
DOC_HANDBOOK=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Employee Handbook 2026" -F "author=HR Department" \
  -F "file=@/tmp/employee_handbook.txt;type=text/plain" | id_of)
echo "  Employee Handbook=$DOC_HANDBOOK"

# ── File Documents into Folders ───────────────────────
echo ""
echo "=== Filing Documents into Folders ==="
curl -s "$BASE/folders/$ACTIVE_CONTRACTS/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_CONTRACT\"}" > /dev/null && echo "  ✓ Contract → Active Contracts"
curl -s "$BASE/folders/$ACTIVE_CONTRACTS/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_AMENDMENT\"}" > /dev/null && echo "  ✓ Amendment → Active Contracts"
curl -s "$BASE/folders/$PENDING_REVIEW/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_NDA\"}" > /dev/null && echo "  ✓ NDA Template → Pending Review"
curl -s "$BASE/folders/$TEMPLATES_FOLDER/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_NDA\"}" > /dev/null && echo "  ✓ NDA Template → Contract Templates"
curl -s "$BASE/folders/$DEAL_ANALYSES/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_FINANCIAL\"}" > /dev/null && echo "  ✓ Financial Analysis → Deal Analyses"
curl -s "$BASE/folders/$BUDGETS/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_BUDGET\"}" > /dev/null && echo "  ✓ Q2 Budget → Budgets"
curl -s "$BASE/folders/$POLICIES/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_HANDBOOK\"}" > /dev/null && echo "  ✓ Employee Handbook → Policies"

# ── Folder Permissions (ACL) ──────────────────────────
echo ""
echo "=== Setting Folder Permissions ==="
# john.legal: READ on Legal Department (inherits to all subfolders)
curl -s "$BASE/folders/$LEGAL_CAB/acl" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"principal_id\":\"$JOHN_ID\",\"principal_type\":\"user\",\"permission_level\":\"read\"}" > /dev/null
echo "  ✓ john.legal → READ on Legal Department"

# sarah.finance: READ on Finance Department
curl -s "$BASE/folders/$FINANCE_CAB/acl" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"principal_id\":\"$SARAH_ID\",\"principal_type\":\"user\",\"permission_level\":\"read\"}" > /dev/null
echo "  ✓ sarah.finance → READ on Finance Department"

# mike.director: READ on both Legal and Finance
curl -s "$BASE/folders/$LEGAL_CAB/acl" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"principal_id\":\"$MIKE_ID\",\"principal_type\":\"user\",\"permission_level\":\"read\"}" > /dev/null
curl -s "$BASE/folders/$FINANCE_CAB/acl" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"principal_id\":\"$MIKE_ID\",\"principal_type\":\"user\",\"permission_level\":\"read\"}" > /dev/null
echo "  ✓ mike.director → READ on Legal + Finance"

# HR is open access (no ACL entries = everyone can see)

# ── Document Relationships ────────────────────────────
echo ""
echo "=== Creating Document Relationships ==="
curl -s "$BASE/documents/$DOC_CONTRACT/relationships" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"target_document_id\":\"$DOC_FINANCIAL\",\"relationship_type\":\"references\",\"description\":\"Financial analysis supporting this contract\"}" > /dev/null
echo "  ✓ Contract references Financial Analysis"

curl -s "$BASE/documents/$DOC_AMENDMENT/relationships" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"target_document_id\":\"$DOC_CONTRACT\",\"relationship_type\":\"supersedes\",\"description\":\"Amends the original partnership agreement\"}" > /dev/null
echo "  ✓ Amendment supersedes Contract"

curl -s "$BASE/documents/$DOC_CONTRACT/relationships" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"target_document_id\":\"$DOC_NDA\",\"relationship_type\":\"related_to\",\"description\":\"NDA signed before partnership discussions\"}" > /dev/null
echo "  ✓ Contract related_to NDA Template"

# ── Workflow Template with Lifecycle Actions ──────────
echo ""
echo "=== Creating Workflow Template ==="
TMPL_ID=$(curl -s "$BASE/templates/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Contract Approval Workflow","description":"Sequential: Legal Review (→review) → Financial Review → Director Approval (→approved)"}' | id_of)

START_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Start","activity_type":"start","position_x":100,"position_y":250}' | id_of)

LEGAL_ACT=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"Legal Review\",\"activity_type\":\"manual\",\"performer_type\":\"user\",\"performer_id\":\"$JOHN_ID\",\"lifecycle_action\":\"transition_to:review\",\"position_x\":350,\"position_y\":250}" | id_of)

FINANCE_ACT=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"Financial Review\",\"activity_type\":\"manual\",\"performer_type\":\"user\",\"performer_id\":\"$SARAH_ID\",\"position_x\":600,\"position_y\":250}" | id_of)

DIRECTOR_ACT=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"Director Approval\",\"activity_type\":\"manual\",\"performer_type\":\"user\",\"performer_id\":\"$MIKE_ID\",\"lifecycle_action\":\"transition_to:approved\",\"position_x\":850,\"position_y\":250}" | id_of)

END_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"End","activity_type":"end","position_x":1100,"position_y":250}' | id_of)

# Flows
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$START_ID\",\"target_activity_id\":\"$LEGAL_ACT\"}" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$LEGAL_ACT\",\"target_activity_id\":\"$FINANCE_ACT\"}" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$FINANCE_ACT\",\"target_activity_id\":\"$DIRECTOR_ACT\"}" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$DIRECTOR_ACT\",\"target_activity_id\":\"$END_ID\"}" > /dev/null

# Validate & install
curl -s "$BASE/templates/$TMPL_ID/validate" -X POST -H "$AUTH" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/install" -X POST -H "$AUTH" > /dev/null
echo "  ✓ Template: Contract Approval Workflow (installed)"
echo "    Lifecycle: Legal Review → review, Director Approval → approved"

# ── Start Workflow with Document ──────────────────────
echo ""
echo "=== Starting Workflow ==="
WF_ID=$(curl -s "$BASE/workflows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"template_id\":\"$TMPL_ID\",\"name\":\"Acme Partnership Approval\",\"description\":\"Review and approve the Acme Corp partnership agreement\",\"document_ids\":[\"$DOC_CONTRACT\"]}" | id_of)
echo "  ✓ Workflow: Acme Partnership Approval (running)"
echo "    Document attached: Acme Partnership Agreement (state: draft)"
echo "    First step: Legal Review → john.legal's inbox"

# ── Backfill search vectors ───────────────────────────
echo ""
echo "=== Initializing Search Indexes ==="
docker-compose exec -T db psql -U docuser -d documentum -c "
  UPDATE documents SET search_vector =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(author, '')), 'B')
  WHERE search_vector IS NULL;
" > /dev/null 2>&1
echo "  ✓ Search vectors initialized for all documents"

# ── Summary ───────────────────────────────────────────
echo ""
echo "=========================================="
echo "  DEMO DATA SEEDED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "ACCOUNTS:"
echo "  admin/admin          — Superuser (sees everything)"
echo "  john.legal/demo1234  — Legal reviewer (sees Legal Dept + HR)"
echo "  sarah.finance/demo1234 — Finance reviewer (sees Finance Dept + HR)"
echo "  mike.director/demo1234 — Director (sees Legal + Finance + HR)"
echo ""
echo "FOLDER STRUCTURE:"
echo "  Legal Department (ACL: john.legal=READ, mike.director=READ)"
echo "    ├── Active Contracts (2 docs)"
echo "    ├── Pending Review (1 doc)"
echo "    └── Contract Templates (1 doc)"
echo "  Finance Department (ACL: sarah.finance=READ, mike.director=READ)"
echo "    ├── Deal Analyses (1 doc)"
echo "    └── Budgets (1 doc)"
echo "  HR Department (open access — no ACL, everyone can see)"
echo "    └── Policies (1 doc)"
echo ""
echo "DOCUMENTS (7 total):"
echo "  Acme Partnership Agreement    → Active Contracts"
echo "  Acme Agreement Amendment #1   → Active Contracts"
echo "  NDA Template v3.2             → Pending Review + Contract Templates"
echo "  Acme Deal Financial Analysis  → Deal Analyses"
echo "  Q2 2026 Budget - Finance      → Budgets"
echo "  Employee Handbook 2026        → Policies"
echo ""
echo "RELATIONSHIPS:"
echo "  Contract references Financial Analysis"
echo "  Amendment supersedes Contract"
echo "  Contract related_to NDA Template"
echo ""
echo "WORKFLOW:"
echo "  Acme Partnership Approval (running)"
echo "  Document: Acme Partnership Agreement (draft)"
echo "  Flow: Legal Review (→review) → Financial Review → Director Approval (→approved)"
echo "  john.legal has work item in inbox"
echo ""
echo "SEARCH: Try 'acme', 'partnership', 'budget', 'handbook', 'NDA'"
echo ""
echo "Open http://localhost:5173 to start the demo"
