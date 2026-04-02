# Change Log

All notable decisions and changes for the Incident Management Platform project are documented here.

## [2026-04-02] — Plan & Design Complete (Stage 2: Plan & Design)

### Added
- Created `docs/design/HLD.md` — High-Level Design Document v1.0
  - Defined 6 system components (COMP-001 through COMP-006)
  - Documented architecture diagram with component relationships
  - Specified technology stack: Python 3.11+, FastAPI, SQLite, Jinja2, PyJWT, httpx, aiosmtplib
  - Designed Azure Monitor webhook integration with severity mapping
  - Established component interaction diagrams and data flow patterns
  - Created full traceability matrix mapping HLD components to BRD requirements
- Created `docs/design/LLD/LLD-auth.md` — Auth & RBAC Service Low-Level Design
  - Designed JWT-based local authentication with bcrypt password hashing
  - Defined 3 user roles: Admin, Engineer, Viewer with FastAPI dependency injection enforcement
  - Specified users table schema, auth API endpoints, and security utilities
- Created `docs/design/LLD/LLD-incidents.md` — Incident Service Low-Level Design
  - Designed incident lifecycle state machine (open → acknowledged → investigating → resolved → closed)
  - Defined incident CRUD, assignment, RCA, comments, and timeline API endpoints
  - Specified incidents, incident_comments, and incident_timeline table schemas
  - Documented valid state transitions with enforcement rules
- Created `docs/design/LLD/LLD-notifications.md` — Notification Service Low-Level Design
  - Designed pluggable notification channel architecture using Strategy pattern
  - Specified email (SMTP), Slack (webhook), and Teams (webhook) channel implementations
  - Defined retry logic with exponential backoff (up to 3 attempts)
  - Designed notification configuration and logging tables
- Created `docs/design/LLD/LLD-azure-integration.md` — Azure Integration Service Low-Level Design
  - Designed Azure Monitor Common Alert Schema parser
  - Specified severity mapping: Sev0/Sev1→P1, Sev2→P2, Sev3→P3, Sev4→P4
  - Implemented alert deduplication to prevent duplicate incident creation
  - Designed resource metadata extraction (resource ID, group, subscription)
- Created `docs/design/LLD/LLD-dashboard-reporting.md` — Dashboard & Reporting Service Low-Level Design
  - Designed aggregated metrics API (counts by status/severity, MTTR, MTTA)
  - Specified CSV export with streaming response for large datasets
  - Designed Jinja2 dashboard template structure with responsive layout

### Decisions
- **DD-001**: Local auth with JWT for MVP (simplest; no external IdP dependency)
- **DD-002**: SQLite with WAL mode for MVP (BRD constraint; migration path to PostgreSQL planned)
- **DD-003**: Synchronous notification dispatch with async HTTP (no Celery overhead for MVP)
- **DD-004**: Jinja2 server-side rendering for frontend (minimal complexity for MVP)
- **DD-005**: Repository pattern for data access (clean separation; easy DB swap later)
- **DD-006**: Incoming Webhooks for Slack/Teams (simplest setup; no bot registration needed)
- **DD-007**: Azure Monitor Common Alert Schema for webhook parsing (standard; forward-compatible)

### Traceability
- Pipeline Tracker: https://github.com/sidlabs-platform/AI-SDLC/issues/1
- Design Issue: https://github.com/sidlabs-platform/AI-SDLC/issues/4
- Previous Stage PR: https://github.com/sidlabs-platform/AI-SDLC/pull/3

---

## [2026-04-02] — BRD Created (Stage 1: Requirements Gathering)

### Added
- Created `docs/requirements/BRD.md` — Business Requirements Document v1.0
  - Defined project scope for an incident management platform with Azure integration
  - Documented 15 functional requirements (BRD-FR-001 through BRD-FR-015)
  - Documented 12 non-functional requirements (BRD-NFR-001 through BRD-NFR-012)
  - Documented 4 Azure integration requirements (BRD-AZ-001 through BRD-AZ-004)
  - Documented 6 notification channel requirements (BRD-NC-001 through BRD-NC-006)
  - Defined 12 use cases (UC-001 through UC-012)
  - Identified 7 risks with mitigation strategies (R-001 through R-007)
  - Established 5 KPIs for success measurement

### Decisions
- **D-001**: Platform will use Python/FastAPI backend with SQLite for MVP storage
- **D-002**: Azure Monitor webhook integration is the primary alert ingestion mechanism for MVP
- **D-003**: Three notification channels supported for MVP: email (SMTP), Slack (webhooks), Microsoft Teams (webhooks)
- **D-004**: Local authentication for MVP with Azure AD (Entra ID) as a should-have
- **D-005**: Incident severity model uses P1–P4 mapped from Azure Monitor severity levels
- **D-006**: RCA is a structured section within each incident (not a separate entity)

### Traceability
- Pipeline Tracker: https://github.com/sidlabs-platform/AI-SDLC/issues/1
- Requirements Issue: https://github.com/sidlabs-platform/AI-SDLC/issues/2
