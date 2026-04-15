# Technology Stack Additions for v1.4

**Project:** Documentum Workflow Clone - Enterprise Completeness
**Researched:** 2026-04-15
**Scope:** NEW dependencies only. Existing stack (FastAPI, SQLAlchemy, PostgreSQL, Redis, MinIO, Celery, React 19, etc.) is locked and validated.

## New Python Dependencies

### Authentication & SSO

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| authlib | 1.6.x | OAuth2/OIDC client & server | The definitive Python OAuth2/OIDC library. Supports FastAPI natively, handles JWT/JWS/JWE/JWK, and can act as both OAuth2 client (for SSO with external IdPs) and OAuth2 server (for issuing tokens). Replaces python-jose for new OAuth2 flows while existing JWT auth continues working. HIGH confidence. |
| python3-saml | 1.16.x | SAML 2.0 SP implementation | The only maintained SAML toolkit for Python 3. Handles SP-initiated and IdP-initiated SSO, assertion encryption, metadata publishing. Session-less design fits FastAPI well. Requires xmlsec1 system dependency. HIGH confidence. |
| ldap3 | 2.9.x | LDAP directory integration | Pure Python, no C dependencies. RFC 4510 compliant. Supports ASYNC connection strategy for non-blocking queries. The main package hasn't had a release since 2021 (2.9.1), but it's stable and widely deployed. The protocol itself is stable. MEDIUM confidence -- consider ldap3-dev (2.10.5) if bugs surface. |

**Why authlib over keeping python-jose:** python-jose handles JWT only. authlib handles the full OAuth2/OIDC flow -- authorization code grant, token exchange, PKCE, discovery endpoints, JWKS rotation. For SSO integration with enterprise IdPs (Azure AD, Okta, Keycloak), you need the full protocol, not just token verification. The existing JWT auth (PyJWT) continues unchanged for internal token issuance; authlib handles external IdP federation.

**Why NOT python-social-auth:** Over-abstracted for this use case. We need direct control over the SAML/OIDC flow to integrate with our existing user/role model, not a generic social login framework.

### Email Archiving

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| mail-parser | 4.1.x | Parse EML/MSG email files | Extracts headers, bodies (text + HTML), attachments, routing info from raw email files. Apache 2 licensed. Handles RFC non-compliant emails gracefully. Builds on Python's email stdlib. HIGH confidence. |
| extract-msg | 0.51.x | Parse Outlook .msg files | Dedicated parser for Microsoft's OLE2-based .msg format. mail-parser handles EML; extract-msg handles proprietary Outlook format. Both output to a common structure we define. MEDIUM confidence. |
| aiosmtpd | 1.4.x | SMTP server for email capture | Async SMTP server that receives emails directly. Runs as a separate service (or Celery worker) listening on port 25/587. Emails received get parsed and stored as documents in the repository. Better than IMAP polling because it's real-time and doesn't require an external mailbox. MEDIUM confidence. |

**Why NOT aioimaplib:** IMAP polling adds latency and requires an external mail server. aiosmtpd lets the system receive emails directly -- simpler architecture for an email archiving endpoint. IMAP can be added later as an optional connector if needed.

### Process Analytics & Mining

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pm4py | 2.7.x | Process mining algorithms | The standard Python process mining library. Provides process discovery (Alpha Miner, Inductive Miner, Heuristic Miner), conformance checking, and performance analysis. **Heavy dependency** -- pulls in pandas, numpy, scipy, networkx, graphviz. Install as optional dependency. HIGH confidence. |

**Architecture decision:** pm4py is heavy (~200MB+ with dependencies). Install it in a separate Celery worker or dedicated analytics service, NOT in the main FastAPI process. The main app exports event logs in XES/CSV format; pm4py consumes them. This keeps the core API lean.

**Why NOT build from scratch:** Process mining algorithms (Alpha Miner, Inductive Miner) are research-grade complexity. pm4py is maintained by Fraunhofer Institute researchers. Reimplementing is not justified.

### System Monitoring

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| psutil | 7.2.x | System metrics collection | Cross-platform CPU, memory, disk, network monitoring. Used by the health dashboard endpoint to report system state. Lightweight, no heavy dependencies. HIGH confidence. |
| prometheus-client | 0.25.x | Metrics exposition | Standard Prometheus metrics format. Expose /metrics endpoint for external monitoring (Grafana/Prometheus stack). Counters for workflow completions, histograms for task latency, gauges for queue depth. HIGH confidence. |

**Why NOT a full APM (DataDog, New Relic):** This is an internal tool. prometheus-client + psutil gives us everything needed: custom metrics, system health, and Prometheus/Grafana compatibility. No SaaS dependency.

### WebDAV Server

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| wsgidav | 4.3.x | WebDAV protocol implementation | The most mature Python WebDAV server. Extensive protocol compliance (Class 1, 2, 3), lock support, property management. WSGI-based but can be mounted alongside FastAPI via a2wsgi or run as a separate service. HIGH confidence. |

**Why wsgidav over asgi-webdav:** asgi-webdav (1.4.2) is a smaller project with limited protocol compliance and no lock support. wsgidav has 10+ years of battle-testing, extensive WebDAV protocol coverage, and a well-documented provider interface for custom backends. The WSGI/ASGI mismatch is trivially solved: run wsgidav as a separate Uvicorn worker on a different port (e.g., :8081/webdav) behind the same reverse proxy, or use a2wsgi adapter. Protocol compliance matters more than async purity for WebDAV.

### Tamper-Proof Audit

No new dependencies needed. The existing `cryptography` library (already installed) provides everything required:
- SHA-256 hash chaining (each audit entry includes hash of previous entry)
- RSA/ECDSA signing of audit log entries
- Periodic checkpoint signing with server's private key

This is a schema + application logic feature, not a library problem.

### Import/Export

No new dependencies needed. Use stdlib `zipfile` for package format, existing `jsonschema` for manifest validation, existing SQLAlchemy for data serialization. Define a custom JSON-based manifest format (or adopt a simple convention like Alfresco ACP structure).

### Bulk Operations & Job Tracking

No new dependencies needed. Celery already provides Canvas workflows (groups, chains, chords) for batch execution, and Redis for progress tracking. Add a `batch_jobs` table and use Celery's `group()` for parallel document operations with progress callbacks.

### Workflow Error Handling, Versioning, Advanced Joins

No new dependencies needed. These are pure application logic features built on existing SQLAlchemy models and Celery task infrastructure. Schema additions (error handler definitions, version tracking columns, join weight columns) and engine logic changes.

### Tiered Storage

No new dependencies needed. MinIO already supports multiple buckets and storage classes. Tiered storage = policy engine (Python code) + Celery Beat periodic task that moves objects between MinIO buckets (hot/warm) or to cheaper storage. If cold storage goes to filesystem, Python's `shutil` handles it.

## New Frontend Dependencies

### Digital Signatures UI

No new npm dependencies needed. The existing stack (React 19, shadcn/ui, TanStack Query) provides everything for building certificate viewer, signature trigger buttons, and verification status displays. The `cryptography` backend does the actual signing -- the frontend just calls API endpoints and renders results.

**Why NOT react-signature-canvas:** That's for hand-drawn signatures (wet ink emulation). Our digital signatures are cryptographic (PKCS7/CMS) -- the UI shows certificate details, triggers server-side signing, and displays verification status. No canvas drawing needed.

### Retention, ACL, Queue Admin, Notification Preferences UI

No new npm dependencies needed. These are standard CRUD forms and data tables using existing shadcn/ui components, TanStack Table, and TanStack Query. The backend APIs already exist (v1.2 shipped these features); the frontend just needs pages wired up.

### Process Analytics Dashboard

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| @dagrejs/dagre | (already installed) | Process graph layout | Already in package.json. Used for workflow designer layout. Reuse for process mining result visualization (discovered process models). |
| @xyflow/react | (already installed) | Process model visualization | Already installed. Reuse the same canvas component to render discovered process models from pm4py output. |

No new frontend dependencies for analytics. Recharts (already installed) handles bar/line charts for performance metrics. React Flow (already installed) renders discovered process models. The pm4py backend outputs JSON graph structures that the frontend visualizes.

### System Monitoring Dashboard

No new npm dependencies needed. Recharts (installed) for time-series charts, TanStack Query for polling /health and /metrics endpoints, shadcn/ui for status cards and alerts.

## New Infrastructure Dependencies

### CMIS Standard API

**No library -- custom implementation required.** There is no Python CMIS server library. cmislib/cmislib3 are client libraries for connecting TO CMIS servers, not for building one. We need to implement the CMIS Browser Binding (JSON-based, simpler than AtomPub) as FastAPI routes.

Implementation approach:
- CMIS Browser Binding spec: JSON over HTTP, maps cleanly to FastAPI routes
- ~15 endpoints covering: getRepositoryInfo, getObject, getChildren, query (CMIS-QL), createDocument, updateProperties, deleteObject, getContentStream, setContentStream, checkOut/checkIn, getVersions
- CMIS-QL query parsing: implement a minimal parser or translate CMIS-QL to our existing DQL-like query engine
- Estimated scope: ~1500-2000 lines of API routes + CMIS-specific schemas

**Why Browser Binding over AtomPub:** Browser Binding uses JSON (our existing format), works with standard HTTP tools, and is the modern CMIS binding. AtomPub uses XML/Atom, is complex to implement, and is being deprecated by most CMIS clients.

### Email Archiving SMTP Service

If using aiosmtpd for direct email capture, it needs a dedicated port (25 or 587). Add to Docker Compose as either:
- A new container running the SMTP listener
- An additional port on the Celery worker container

### System Dependencies (Docker)

| Dependency | Container | Purpose |
|------------|-----------|---------|
| xmlsec1 | FastAPI container | Required by python3-saml for XML signature verification. Add `apt-get install xmlsec1 libxmlsec1-dev` to Dockerfile. |
| graphviz | Analytics worker | Required by pm4py for process model rendering. Add `apt-get install graphviz` to analytics worker Dockerfile. |

No new Docker Compose services needed beyond what exists. The analytics worker can be a Celery worker with pm4py installed. The SMTP listener can run in the same container or a dedicated lightweight one.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| OAuth2/OIDC | authlib | python-social-auth | Over-abstracted, hides protocol details we need to control |
| OAuth2/OIDC | authlib | fastapi-oidc | Too narrow (verification only), no OAuth2 server capability |
| SAML | python3-saml | pysaml2 | Less documented, more complex API, fewer production examples |
| LDAP | ldap3 | python-ldap | Requires C libraries (libldap), harder to containerize |
| Email parsing | mail-parser + extract-msg | flanker | Flanker unmaintained since 2019 |
| Email capture | aiosmtpd | IMAP polling (aioimaplib) | Polling adds latency; direct SMTP is real-time |
| WebDAV | wsgidav | asgi-webdav | Less protocol compliance, no lock support, smaller community |
| Process mining | pm4py | Custom implementation | Research-grade algorithms, not worth reimplementing |
| Monitoring | psutil + prometheus-client | Full APM (DataDog) | SaaS dependency, overkill for internal tool |
| CMIS | Custom FastAPI routes | cmislib3 | cmislib3 is a CLIENT library, not a server implementation |

## Installation

```bash
# SSO / Authentication
pip install authlib>=1.6,<2 python3-saml>=1.16,<2 ldap3>=2.9,<3

# Email archiving
pip install mail-parser>=4.1,<5 extract-msg>=0.51,<1 aiosmtpd>=1.4,<2

# Process mining (install in analytics worker only, NOT main app)
pip install pm4py>=2.7,<3

# System monitoring
pip install psutil>=7.2,<8 prometheus-client>=0.25,<1

# WebDAV server
pip install wsgidav>=4.3,<5

# System dependencies (Dockerfile)
# apt-get install -y xmlsec1 libxmlsec1-dev pkg-config
# Analytics worker: apt-get install -y graphviz
```

No new frontend npm packages required. All new UI features use existing dependencies.

## Integration Points with Existing Stack

| New Component | Integrates With | How |
|---------------|----------------|-----|
| authlib (OAuth2/OIDC) | Existing JWT auth (PyJWT) | External IdP tokens exchanged for internal JWT tokens. Existing /auth/login stays for local users; new /auth/sso/* endpoints handle federated login. User table gets `external_id` and `idp_provider` columns. |
| python3-saml | FastAPI routes | SAML ACS endpoint receives POST from IdP, validates assertion, creates/maps user, issues internal JWT. |
| ldap3 | User/Group sync | Celery Beat task periodically syncs LDAP directory to local user/group tables. Login can also authenticate against LDAP in real-time. |
| mail-parser / extract-msg | Document upload pipeline | Parsed emails become documents in the repository (MinIO for content, PostgreSQL for metadata). Attachments become child documents. |
| aiosmtpd | Celery worker | SMTP handler receives email, creates Celery task to parse and archive it. |
| pm4py | Celery worker + API | API endpoint exports workflow execution logs as event log. Celery task runs pm4py algorithms. Results stored in PostgreSQL, visualized by frontend. |
| psutil + prometheus-client | FastAPI middleware | /health endpoint uses psutil for system metrics. /metrics exposes Prometheus format. Dashboard polls these endpoints. |
| wsgidav | MinIO + PostgreSQL | Custom DAVProvider reads document metadata from PostgreSQL and content from MinIO. Runs as separate WSGI service behind reverse proxy. |
| CMIS (custom) | Existing FastAPI routes | CMIS endpoints delegate to existing document/folder service layer. Thin translation layer from CMIS object model to our internal model. |

## What NOT to Add

| Temptation | Why Avoid |
|------------|-----------|
| Elasticsearch for email search | PostgreSQL FTS (tsvector) already handles full-text search. Adding ES doubles operational complexity for marginal gain at this scale. |
| Kafka for event streaming | Redis pub/sub + PostgreSQL LISTEN/NOTIFY already handle real-time events. Kafka is for 100K+ events/sec scale we don't need. |
| GraphQL API | REST + CMIS Browser Binding covers all client needs. GraphQL adds a second API paradigm to maintain. |
| Keycloak (self-hosted IdP) | We're building an SSO CLIENT, not running our own IdP. authlib + python3-saml connect to whatever IdP the enterprise uses. |
| Apache Airflow for workflow orchestration | We HAVE a workflow engine. Airflow is for data pipelines, not human-in-the-loop business workflows. |
| Heavy PDF libraries (reportlab) | LibreOffice headless (already configured) handles document-to-PDF conversion. pdfplumber (already installed) handles extraction. |
| react-pdf-viewer for frontend | The current approach of rendering PDFs via browser native or iframe is sufficient. A dedicated viewer adds 500KB+ to the bundle. |

## Dependency Weight Summary

| Category | New Packages | Approx. Size | Risk Level |
|----------|-------------|-------------|------------|
| SSO (authlib + python3-saml + ldap3) | 3 | ~15MB | Low -- mature, stable APIs |
| Email (mail-parser + extract-msg + aiosmtpd) | 3 | ~8MB | Low -- parsing is well-understood |
| Analytics (pm4py) | 1 (+pandas, numpy, scipy, networkx) | ~200MB+ | Medium -- heavy deps, isolate in worker |
| Monitoring (psutil + prometheus-client) | 2 | ~5MB | Low -- zero-issue dependencies |
| WebDAV (wsgidav) | 1 | ~3MB | Low -- mature, well-tested |
| **Total new Python packages** | **10** | | |
| **Total new npm packages** | **0** | | |

## Sources

- [Authlib PyPI - v1.6.10](https://pypi.org/project/Authlib/) -- HIGH confidence
- [Authlib docs](https://docs.authlib.org/) -- HIGH confidence
- [python3-saml GitHub](https://github.com/SAML-Toolkits/python3-saml) -- HIGH confidence
- [ldap3 PyPI - v2.9.1](https://pypi.org/project/ldap3/) -- MEDIUM confidence (last release 2021, but protocol is stable)
- [mail-parser PyPI](https://pypi.org/project/mail-parser/) -- HIGH confidence
- [extract-msg PyPI](https://pypi.org/project/extract-msg/) -- MEDIUM confidence
- [aiosmtpd PyPI](https://pypi.org/project/aiosmtpd/) -- MEDIUM confidence
- [pm4py PyPI - v2.7.22](https://pypi.org/project/pm4py/) -- HIGH confidence
- [pm4py GitHub](https://github.com/process-intelligence-solutions/pm4py) -- HIGH confidence
- [psutil PyPI - v7.2.2](https://pypi.org/project/psutil/) -- HIGH confidence
- [prometheus-client PyPI - v0.25.0](https://pypi.org/project/prometheus-client/) -- HIGH confidence
- [WsgiDAV PyPI - v4.3.x](https://pypi.org/project/WsgiDAV/) -- HIGH confidence
- [asgi-webdav GitHub](https://github.com/rexzhang/asgi-webdav) -- MEDIUM confidence
- [CMIS Browser Binding spec (OASIS)](https://docs.oasis-open.org/cmis/CMIS/v1.1/CMIS-v1.1.html) -- HIGH confidence
