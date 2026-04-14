#!/bin/bash
# Seed demo data for Documentum Workflow Clone
set -e

BASE="http://localhost:8000/api/v1"
TOKEN=$(curl -s "$BASE/auth/login" -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin&password=admin" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
AUTH="Authorization: Bearer $TOKEN"

echo "=== Creating Users ==="
JOHN_ID=$(curl -s "$BASE/users/" -X POST -H "$AUTH" -H "Content-Type: application/json" -d '{"username":"john.legal","password":"demo1234","email":"john@example.com"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
SARAH_ID=$(curl -s "$BASE/users/" -X POST -H "$AUTH" -H "Content-Type: application/json" -d '{"username":"sarah.finance","password":"demo1234","email":"sarah@example.com"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
MIKE_ID=$(curl -s "$BASE/users/" -X POST -H "$AUTH" -H "Content-Type: application/json" -d '{"username":"mike.director","password":"demo1234","email":"mike@example.com"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "john=$JOHN_ID sarah=$SARAH_ID mike=$MIKE_ID"

echo "=== Creating Template ==="
TMPL_ID=$(curl -s "$BASE/templates/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Contract Approval Workflow","description":"Sequential: Legal Review → Financial Review → Director Approval"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "template=$TMPL_ID"

echo "=== Adding Activities ==="
START_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Start","activity_type":"start","position_x":100,"position_y":250}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

LEGAL_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"Legal Review\",\"activity_type\":\"manual\",\"performer_type\":\"user\",\"performer_id\":\"$JOHN_ID\",\"position_x\":350,\"position_y\":250}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

FINANCE_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"Financial Review\",\"activity_type\":\"manual\",\"performer_type\":\"user\",\"performer_id\":\"$SARAH_ID\",\"position_x\":600,\"position_y\":250}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

DIRECTOR_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"Director Approval\",\"activity_type\":\"manual\",\"performer_type\":\"user\",\"performer_id\":\"$MIKE_ID\",\"position_x\":850,\"position_y\":250}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

END_ID=$(curl -s "$BASE/templates/$TMPL_ID/activities" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"End","activity_type":"end","position_x":1100,"position_y":250}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "start=$START_ID legal=$LEGAL_ID finance=$FINANCE_ID director=$DIRECTOR_ID end=$END_ID"

echo "=== Adding Flows ==="
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$START_ID\",\"target_activity_id\":\"$LEGAL_ID\"}" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$LEGAL_ID\",\"target_activity_id\":\"$FINANCE_ID\"}" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$FINANCE_ID\",\"target_activity_id\":\"$DIRECTOR_ID\"}" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/flows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"source_activity_id\":\"$DIRECTOR_ID\",\"target_activity_id\":\"$END_ID\"}" > /dev/null
echo "4 flows created"

echo "=== Validating & Installing Template ==="
curl -s "$BASE/templates/$TMPL_ID/validate" -X POST -H "$AUTH" > /dev/null
curl -s "$BASE/templates/$TMPL_ID/install" -X POST -H "$AUTH" | grep -o '"state":"[^"]*"'

echo "=== Uploading Documents ==="
echo "Partnership Agreement between Acme Corp and Widget Inc. Terms: 3-year exclusive distribution." > D:/Python/documentum_clone/contract.txt
DOC1_ID=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Acme Partnership Agreement" \
  -F "file=@D:/Python/documentum_clone/contract.txt;type=text/plain" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

echo "Financial analysis for Acme deal. Projected revenue: 1.2M/year. ROI: 340%." > D:/Python/documentum_clone/financials.txt
DOC2_ID=$(curl -s "$BASE/documents/" -X POST -H "$AUTH" \
  -F "title=Acme Deal Financial Analysis" \
  -F "file=@D:/Python/documentum_clone/financials.txt;type=text/plain" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "doc1=$DOC1_ID doc2=$DOC2_ID"

echo "=== Creating Cabinets & Folders ==="
LEGAL_CAB_ID=$(curl -s "$BASE/folders/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Legal Department","description":"Legal documents and contracts"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "legal_cabinet=$LEGAL_CAB_ID"

ACTIVE_FOLDER_ID=$(curl -s "$BASE/folders/$LEGAL_CAB_ID/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Active Contracts","description":"Currently active contracts"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "active_contracts=$ACTIVE_FOLDER_ID"

PENDING_FOLDER_ID=$(curl -s "$BASE/folders/$LEGAL_CAB_ID/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Pending Review","description":"Contracts awaiting review"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "pending_review=$PENDING_FOLDER_ID"

FINANCE_CAB_ID=$(curl -s "$BASE/folders/" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Finance Department","description":"Financial documents and analyses"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "finance_cabinet=$FINANCE_CAB_ID"

REPORTS_FOLDER_ID=$(curl -s "$BASE/folders/$FINANCE_CAB_ID/children" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Deal Analyses","description":"Financial analyses for deals"}' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "deal_analyses=$REPORTS_FOLDER_ID"

echo "=== Filing Documents into Folders ==="
curl -s "$BASE/folders/$ACTIVE_FOLDER_ID/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC1_ID\"}" > /dev/null
echo "Filed contract into Active Contracts"

curl -s "$BASE/folders/$REPORTS_FOLDER_ID/documents" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC2_ID\"}" > /dev/null
echo "Filed financials into Deal Analyses"

echo "=== Setting Folder Permissions ==="
curl -s "$BASE/folders/$LEGAL_CAB_ID/acl" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"principal_id\":\"$JOHN_ID\",\"principal_type\":\"user\",\"permission_level\":\"read\"}" > /dev/null
echo "Granted john.legal READ on Legal Department"

curl -s "$BASE/folders/$FINANCE_CAB_ID/acl" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"principal_id\":\"$SARAH_ID\",\"principal_type\":\"user\",\"permission_level\":\"read\"}" > /dev/null
echo "Granted sarah.finance READ on Finance Department"

echo "=== Creating Document Relationship ==="
curl -s "$BASE/documents/$DOC1_ID/relationships" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"target_document_id\":\"$DOC2_ID\",\"relationship_type\":\"references\",\"description\":\"Financial analysis for this contract\"}" > /dev/null
echo "Created relationship: contract references financials"

echo "=== Starting Workflow ==="
WF_ID=$(curl -s "$BASE/workflows" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"template_id\":\"$TMPL_ID\",\"name\":\"Acme Partnership Approval\",\"description\":\"Review and approve the Acme Corp partnership agreement\"}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "workflow=$WF_ID"

echo ""
echo "=========================================="
echo "  DEMO DATA SEEDED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "Users: admin/admin, john.legal/demo1234, sarah.finance/demo1234, mike.director/demo1234"
echo "Cabinets: Legal Department (Active Contracts, Pending Review), Finance Department (Deal Analyses)"
echo "Documents: Acme Partnership Agreement (in Active Contracts), Acme Deal Financial Analysis (in Deal Analyses)"
echo "Permissions: john.legal=READ on Legal, sarah.finance=READ on Finance"
echo "Relationship: contract references financials"
echo "Template: Contract Approval Workflow (installed)"
echo "Workflow: Acme Partnership Approval (running)"
echo ""
echo "Open http://localhost:5173 to start the demo"
