# Change Log

All notable decisions and changes for the Incident Management Platform project are documented here.

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
