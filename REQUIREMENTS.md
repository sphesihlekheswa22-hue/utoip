# UITOP Software Requirements Specification

**System:** UITOP — Unified IT Operations Platform
**Document type:** Functional and non-functional requirements baseline
**Status:** As-is requirements with implementation status and target gaps
**Audience:** Product owner, IT operations, engineering, QA, security, and deployment teams

> This document describes the capabilities currently present in the UITOP codebase and the quality attributes required for a supported organizational deployment. `Implemented` means the behavior exists in code; `Partial` means a UI or service exists but depends on mock data, stubs, or incomplete enforcement; `Not implemented` means the capability is planned or represented only by a page.

---

## 1. Purpose and scope

UITOP is a web and desktop IT operations platform for the your organization. It provides:

- IT infrastructure inventory and monitoring for computers, servers, network devices, and printers.
- Windows agent enrollment, telemetry, and remote command workflows.
- LAN discovery and cloud/on-premises site-connector support.
- Asset ownership and lifecycle management.
- Helpdesk/ITSM, knowledge base, service catalog, workflows, and tasks.
- File repository, document control, and employee workspace services.
- Maintenance, security, calendar, analysis, reports, notifications, audit, and administration modules.
- An RBAC-aware IT Copilot assistant.
- A Flask/Jinja2 web UI, a versioned `/api/v1` REST API, and a Windows desktop shell.

### Out of scope for the current baseline

- A production backup/restore engine.
- Self-registration, password recovery, OTP, and MFA completion flows.
- Live software-license, vendor, security-posture, and software-inventory ingestion for every module.
- A complete write-capable REST API for every UI module.
- High-availability, disaster-recovery, and horizontal-scale infrastructure.

---

## 2. Actors and roles

| Actor | Description | Primary needs |
|---|---|---|
| Super Administrator | Platform owner | Full platform access, users, roles, departments, settings, audit, agents |
| IT Administrator | Infrastructure and operations lead | Manage infrastructure, assets, support, maintenance, reports, agents, connectors |
| Operator | Day-to-day IT operator | Operate inventory, assets, tickets, maintenance, backups, reports |
| Helpdesk | Support agent | Manage tickets, knowledge base, troubleshooting, read-only operational context |
| Employee | Organizational staff member | Self-service, own devices, own tickets, service requests, documents, workspace |
| Agent | Enrolled machine identity | Submit inventory, heartbeat, performance, events, and alerts |
| Site Connector | On-premises LAN scanner | Submit network and printer discovery data to a cloud-hosted platform |
| IT Copilot | Assisted user | Ask permission-aware operational questions and receive data-backed guidance |

RBAC is enforced through a central permission catalogue, database-backed roles, UI guards, API decorators, and agent scopes. Role changes are refreshed into the active UI session on subsequent requests.

---

# 3. Functional requirements

## FR-01 — Authentication and session management

**Status:** Implemented

The system shall:

1. Allow an active user to sign in with email and password.
2. Create a server-side session for web users.
3. Allow a user to sign out and revoke the active refresh token.
4. Require authentication for all non-public web pages.
5. Provide JWT access and refresh tokens for API clients.
6. Rotate refresh tokens and support explicit token revocation.
7. Redirect unauthenticated users to the login page.
8. Prevent inactive users from using existing sessions.
9. Ignore or reject unsafe post-login redirect targets.

**Acceptance criteria**

- Invalid credentials produce the same generic error for unknown email and wrong password.
- Expired, invalid, or revoked API tokens return the documented `401` error envelope.
- Agent tokens cannot be used as user tokens on user endpoints, and user tokens cannot be used as agent tokens.
- Logout invalidates the refresh-token session used by the request.

**Evidence:** `routes/auth.py`, `uitop/services/auth.py`, `uitop/api/v1/auth.py`, `uitop/config.py`.

---

## FR-02 — Roles, permissions, and navigation

**Status:** Implemented

The system shall:

1. Maintain granular permission codes for dashboard, monitoring, inventory, assets, software, licenses, vendors, helpdesk, files, maintenance, calendar, security, backup, analysis, reports, users, roles, departments, audit, settings, agents, and connectors.
2. Support the roles listed in Section 2.
3. Enforce permissions on API endpoints.
4. Enforce permissions on UI routes.
5. Hide navigation items the current user cannot use.
6. Redirect unauthorized HTML users to a safe accessible page.
7. Return `403` for unauthorized JSON requests.
8. Refresh session permissions from the database without requiring a new login.

**Acceptance criteria**

- An employee cannot access administrative inventory or settings pages.
- A helpdesk user can manage tickets but cannot perform asset-management or backup-management operations unless separately granted.
- A user without `roles:manage` cannot design or change role permissions through the UI.
- Agent and connector scopes are checked independently from human-user permissions.

**Evidence:** `uitop/core/permissions.py`, `uitop/core/ui_rbac.py`, `uitop/core/decorators.py`, `uitop/__init__.py`, `templates/components/sidebar.html`.

---

## FR-03 — Dashboard and monitoring

**Status:** Implemented

The system shall provide authorized users with:

1. An operational dashboard with KPIs, charts, activity, and quick actions.
2. Infrastructure-health and fleet-performance views.
3. Computer, server, network, and printer status views.
4. Alert and event views.
5. Service, process, and network-related device detail views where data is available.
6. AI-generated operational insights through the Copilot context layer.

**Acceptance criteria**

- KPI and chart panels render with real database data when inventory is present.
- A user without `monitoring:read` cannot access monitoring routes.
- Stale presence is visibly distinguishable from an active reporting device.

**Evidence:** `routes/dashboard.py`, `routes/monitoring.py`, `uitop/services/dashboard.py`, `uitop/services/monitoring_view.py`.

---

## FR-04 — Infrastructure inventory

**Status:** Implemented

The system shall manage four inventory domains:

- Computers.
- Servers.
- Network devices.
- Printers.

For each domain, authorized users shall be able to:

1. View inventory lists and device details.
2. View available performance, event, alert, network, and service information.
3. Search, filter, sort, and paginate large lists.
4. Download agent installers and installation scripts.
5. Use discovery or agent enrollment as the primary source of device records.
6. Assign supported remote actions to enrolled devices.

Legacy manual “create” entry points shall redirect users to agent installation or discovery workflows.

**Acceptance criteria**

- Inventory cannot be silently duplicated by repeated agent inventory submissions.
- Device detail pages preserve stable identifiers and links.
- Users without the relevant inventory read permission cannot view the list or detail page.

**Evidence:** `routes/computers.py`, `routes/servers.py`, `routes/network.py`, `routes/printers.py`, `uitop/services/computers_view.py`.

---

## FR-05 — LAN discovery and classification

**Status:** Implemented

The system shall provide an operator-driven discovery workflow:

1. Suggest suitable local CIDR ranges.
2. Accept a CIDR and optional device-type filter.
3. Start an asynchronous scan.
4. Probe ICMP and selected TCP service ports.
5. Classify discovered hosts as computers, servers, network devices, printers, or unknown.
6. Enrich results with available hostname and operating-system information.
7. Match results to existing inventory by IP address.
8. Allow an authorized user to import selected results into inventory.

**Safety requirements**

- Scans shall be limited to private RFC1918 address space.
- A scan shall not exceed a `/24` network.

**Evidence:** `routes/discovery.py`, `uitop/services/network_scan.py`.

---

## FR-06 — Agent enrollment and identity

**Status:** Implemented

The system shall support these enrollment methods:

1. **Enrollment token:** An authorized administrator creates a time-limited, usage-limited token. The enrolling agent registers and receives a client identifier, client secret, agent identifier, and linked computer identifier.
2. **Pairing code:** An authorized user generates a short-lived single-use pairing code for the employee “Connect my PC” workflow.
3. **Development helper:** The local agent can use an explicit development-only administrative fallback; this path shall not be used for production.

The system shall store enrollment tokens and client secrets as hashes and shall display a client secret only during registration.

**Evidence:** `uitop/services/agents.py`, `uitop/services/pairing.py`, `routes/computers.py`, `routes/employee.py`.

---

## FR-07 — Agent telemetry and device ownership

**Status:** Implemented

An enrolled agent shall be able to submit:

1. Heartbeat data including status, last-seen time, agent version, hostname, and IP address.
2. Inventory data for whitelisted computer fields.
3. Batched performance samples for CPU, memory, disk, network, process count, and uptime.
4. Batched events with type, severity, message, source, and occurrence time.
5. Batched alerts with code, severity, title, message, status, and resolution time.

The server shall:

- Upsert telemetry rather than creating duplicate rows.
- Create or update the linked computer record as needed.
- Create a linked asset for an enrolled computer.
- Match reported Windows login information to a UITOP user where possible and assign device ownership automatically.
- Record agent actions in the audit log.

**Evidence:** `uitop/api/v1/agents.py`, `uitop/services/agents.py`, `uitop/models/agent_telemetry.py`.

---

## FR-08 — Remote command workflow

**Status:** Implemented

The system shall support a queued command workflow:

1. An authorized user queues an allow-listed command for an enrolled device.
2. The server stores the command as pending and audits the action.
3. The agent claims pending commands through the API.
4. The agent executes the command locally.
5. The agent reports completed or failed status and a result.

Supported commands shall be limited to:

- Restart.
- Shutdown.
- Lock.
- Log off.
- Synchronize inventory.
- Collect diagnostics.
- Wake on LAN.

**Acceptance criteria**

- Unknown commands are rejected on both server and agent.
- Command execution uses bounded timeouts and does not use shell string interpolation.
- Command status transitions are visible in the audit trail.

**Evidence:** `uitop/services/agent_commands.py`, `uitop/api/v1/agents.py`, `agents/command_exec.py`.

---

## FR-09 — Site connector for cloud and on-premises deployments

**Status:** Implemented

When UITOP is hosted in a cloud environment, the system shall support an always-on on-premises PC running the site connector. The connector shall:

1. Enroll using an administrator-generated connector token.
2. Exchange credentials for a connector-scoped JWT.
3. Send periodic heartbeats with host, version, CIDR, scan, and statistics data.
4. Scan one or more permitted private `/24` CIDRs.
5. Submit network-device discovery results.
6. Submit printer discovery and SNMP telemetry results.
7. Continue operating when the server is temporarily unavailable and retry later.

**Acceptance criteria**

- Connector registration does not create a fake computer record.
- Ingest is idempotent by IP address.
- Existing agent-managed device attributes are not overwritten by low-confidence discovery data.
- Connector scopes are distinct from user and agent scopes.

**Evidence:** `uitop/api/v1/connectors.py`, `uitop/services/site_connectors.py`, `agents/site_connector.py`.

---

## FR-10 — Assets and ownership

**Status:** Implemented

The system shall provide asset lifecycle functions including:

1. Asset registration for store or non-IT assets.
2. Linking assets to discovered computers, servers, network devices, or printers.
3. Creating an asset and linking it to a device in one workflow.
4. Submitting, reviewing, and tracking asset requests.
5. Assigning and transferring assets.
6. Editing, categorizing, and viewing asset history.
7. Automatic asset creation for agent-enrolled computers.
8. Permission-controlled disposal operations.

**Evidence:** `routes/assets.py`, `uitop/services/assets.py`, `uitop/models/assets.py`.

---

## FR-11 — Helpdesk and ITSM

**Status:** Implemented

The system shall provide:

1. Ticket creation, editing, assignment, status changes, comments, and activity history.
2. Incident, service-request, problem, and support views.
3. Priority-based SLA targets, due dates, overdue indicators, and an SLA board.
4. Time logging and linked-object tracking.
5. Ticket search, filtering, pagination, and CSV export.
6. A knowledge base with search, create, edit, detail, helpfulness feedback, and deletion.
7. Employee visibility limited to the employee’s own tickets.

**Evidence:** `routes/helpdesk.py`, `uitop/services/helpdesk.py`, `uitop/services/knowledge.py`.

---

## FR-12 — Employee self-service

**Status:** Implemented

An employee shall be able to:

1. View a self-service dashboard.
2. View assigned or owned devices.
3. Generate a device pairing code and connect a PC.
4. Create and view personal tickets.
5. Report a problem against a device with a pre-filled ticket.
6. Browse and submit service-catalog requests.
7. View permitted documents and workspace files.

**Evidence:** `routes/employee.py`, `routes/catalog.py`, `uitop/services/employee_view.py`, `uitop/services/catalog.py`.

---

## FR-13 — Service catalog

**Status:** Implemented

The system shall provide searchable, categorized service offerings, including:

- New laptop.
- Password reset.
- Office installation.
- Software installation.
- Printer access.
- VPN access.
- Email account.
- Shared folder access.
- Backup restore.

Each offering shall support category filtering, a dynamic request form, and mapping to an allowed workflow definition.

**Evidence:** `routes/catalog.py`, `uitop/services/catalog.py`.

---

## FR-14 — Workflows and tasks

**Status:** Implemented

The system shall support:

1. Workflow definitions with ordered steps and per-step permissions.
2. Numbered workflow instances such as `WF-YYYY-NNNN`.
3. Status, type, and ownership filters.
4. Step timelines and role-gated actions.
5. Automatic creation of work tasks from workflow steps.
6. Notifications to role holders when a step requires action.
7. Task views for assigned, queued, and all work.

Baseline workflow definitions shall include restore request, service request, and software install workflows.

**Evidence:** `routes/workflows.py`, `routes/tasks/index.html`, `uitop/services/workflow.py`.

---

## FR-15 — Files, documents, and workspace

**Status:** Implemented

The system shall provide three related services:

1. **File repository:** upload, download, preview, tags, links, versions, and activity history.
2. **Document control:** status transitions, new versions, rollback to a prior version, and object links.
3. **Workspace:** per-user upload, sharing controls, versioning, and usage statistics.

The service shall enforce per-user workspace quotas and a configurable global upload limit. Server-generated paths and sanitized filenames shall be used for stored files.

**Evidence:** `routes/files.py`, `routes/documents.py`, `routes/workspace.py`, `uitop/services/files_view.py`.

---

## FR-16 — Maintenance and operations calendar

**Status:** Implemented

The system shall provide:

1. Maintenance work orders with status, priority, checklist items, parts, cost, and activity history.
2. Preventive maintenance plans and schedules.
3. Overdue detection and asset snapshots.
4. An operations calendar aggregating backup schedules, maintenance windows, ticket SLA due dates, and warranty dates.

**Evidence:** `routes/maintenance.py`, `routes/calendar.py`, `uitop/services/maintenance.py`, `uitop/services/calendar_view.py`.

---

## FR-17 — Security posture and records

**Status:** Partial

The system shall provide views for:

1. Security posture summaries.
2. Device posture detail.
3. Threats and vulnerabilities.
4. Security incidents.
5. Policies and user activity.
6. Security audit events.

Current security data is primarily seeded. A live agent or connector ingestion path for real security posture is not yet implemented.

**Evidence:** `routes/security.py`, `uitop/services/security_view.py`, `uitop/models/security.py`.

---

## FR-18 — Software, licenses, and vendors

**Status:** Partial

The system shall provide UI and service layers for:

1. Software catalog, versions, deployments, updates, requests, and activity.
2. License seats, assigned users/devices, purchase information, renewals, and compliance.
3. Vendor records, assets, software, contracts, purchase orders, warranties, contacts, and activity.

Software, license, and vendor views currently contain substantial demo or hard-coded data. Live agent software inventory and real license/vendor persistence must be completed before these modules can be considered production-complete.

**Evidence:** `routes/software.py`, `routes/licenses.py`, `routes/vendors.py`, `uitop/services/software_view.py`, `uitop/services/licenses_view.py`, `uitop/services/vendors_view.py`.

---

## FR-19 — Reports and analysis

**Status:** Partial

The system shall provide:

1. Executive, infrastructure, asset, helpdesk, maintenance, monitoring, security, software, license, vendor, user/access, backup, audit, and financial report categories.
2. Report dashboard, generation, template, history, scheduled, shared, export, and audit views.
3. Date-range and department filtering.
4. CSV and JSON export.
5. Printable HTML output for browser PDF generation.
6. Analysis views for infrastructure, assets, helpdesk, performance, security, maintenance, financial, forecasts, AI insights, and risk rankings.

Scheduled, shared, history, and several trend values currently use synthetic or demo data and must be connected to persisted records and a scheduler.

**Evidence:** `routes/reports.py`, `uitop/services/reports_view.py`, `routes/analysis.py`, `uitop/services/analysis_view.py`.

---

## FR-20 — IT Copilot

**Status:** Implemented with external-service dependency

The Copilot shall:

1. Accept natural-language operational questions.
2. Classify intent across dashboard, inventory, tickets, assets, printers, servers, backup, security, audit, software, files, monitoring, maintenance, reports, and troubleshooting topics.
3. Gather live context only for permissions held by the requesting user.
4. Send the permitted context and recent conversation to the configured OpenRouter or OpenAI model.
5. Persist per-user sessions and messages.
6. Provide a global assistant entry point from the application shell.
7. Return a safe, deterministic fallback when no model is configured.

Live data sent to an external model provider must be reviewed against organizational privacy and information-governance requirements.

**Evidence:** `routes/ai.py`, `uitop/services/copilot.py`, `static/js/ai.js`, `.env.example`.

---

## FR-21 — Notifications and audit

**Status:** Implemented

The system shall:

1. Create in-app notifications for ticket and workflow events.
2. Display an unread count globally.
3. Allow a user to mark one or all notifications as read.
4. Record authentication, agent, connector, administrative, settings, ticket, and remote-command actions in the audit log.
5. Support audit filtering by category, severity, result, actor, date, and resource.
6. Support audit CSV export.
7. Prevent normal UI users from editing or deleting audit records.

**Evidence:** `uitop/services/notifications.py`, `uitop/services/audit.py`, `uitop/services/audit_view.py`, `routes/audit.py`.

---

## FR-22 — Administration and settings

**Status:** Implemented

Authorized administrators shall be able to:

1. Manage users, roles, permissions, departments, teams, sessions, invitations, and assignments.
2. Edit profile name, email, and password.
3. Change password using the current password and confirmation.
4. View user assets, tickets, software, permissions, sessions, activity, documents, and history.
5. Configure general, organization, security, authentication, email, notification, backup, storage, monitoring, agent, integration, API-key, appearance, system, and audit settings.
6. Trigger the provided test-email action.

Email delivery, API-key enforcement, rate limits, and several configured security thresholds are not yet wired to active services.

**Evidence:** `routes/users.py`, `routes/profile.py`, `routes/settings.py`, `uitop/services/users_view.py`, `uitop/services/settings_view.py`.

---

## FR-23 — REST API

**Status:** Implemented for a defined subset

The API base path shall be `/api/v1`. Successful responses shall use:

```json
{"data": {}, "meta": {}}
```

Errors shall use:

```json
{"error": {"code": "", "message": "", "details": null}}
```

The current API includes:

- Authentication: `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`.
- Users: list, create, detail, update, role assignment.
- Roles and departments.
- Audit query with bounded limit.
- Read-only computer, server, network-device, and printer inventory.
- Agent enrollment, registration, pairing, token, heartbeat, inventory, performance, events, alerts, command polling, and command results.
- Site-connector enrollment, registration, token, heartbeat, network ingest, and printer ingest.

The API does not currently expose complete write operations for assets, helpdesk, files, workflows, maintenance, notifications, reports, software, licenses, vendors, security, calendar, or Copilot.

**Evidence:** `uitop/api/v1/__init__.py`, `uitop/api/v1/*.py`.

---

## FR-24 — Desktop and local deployment

**Status:** Implemented

The desktop application shall:

1. Start the Flask server in a background thread.
2. Bind to all interfaces so LAN agents can connect.
3. Open a native window when `pywebview` is available.
4. Fall back to the default browser when `pywebview` is unavailable.
5. Use a local database and file root next to the packaged application.
6. Wait for the server to become reachable before opening the UI.
7. Provide a Windows launcher for development use.

**Evidence:** `desktop_app.py`, `app.py`, `wsgi.py`, `Start UITOP.bat`, `uitop-desktop.spec`.

---

# 4. Non-functional requirements

## NFR-01 — Security and privacy

**Status:** Partial; production hardening required

The system shall:

1. Hash passwords and machine secrets using a modern password-hashing scheme.
2. Never return stored client secrets after registration.
3. Use short-lived access tokens and rotating refresh tokens.
4. Enforce least-privilege RBAC on UI, API, agent, and connector paths.
5. Validate and sanitize uploads and prevent path traversal.
6. Restrict network discovery to private, bounded ranges.
7. Record security-relevant actions in the audit trail.
8. Use secure session-cookie attributes in production.
9. Protect state-changing forms against CSRF.
10. Set security response headers, including a content-security policy and clickjacking protection.
11. Avoid exposing raw provider or internal exception details to end users.
12. Define a credential-rotation and revocation process for agents, connectors, API clients, and administrators.

Current gaps include absent CSRF protection, unset secure-cookie configuration, loose default CORS, a weak default secret, and no authentication rate limiting or lockout.

**Evidence:** `uitop/core/security.py`, `uitop/services/auth.py`, `uitop/config.py`, `uitop/services/agent_commands.py`, `uitop/services/files_view.py`.

---

## NFR-02 — Access control and least privilege

**Status:** Implemented for permission codes; object-level scope is partial

The system shall:

1. Use database-backed roles and permissions.
2. Re-synchronize permissions on every authenticated UI request.
3. Enforce agent scopes separately from human-user permissions.
4. Provide safe redirects for denied HTML requests.
5. Provide a distinct employee navigation experience.
6. Ensure role assignment requires the appropriate role-management permission.
7. Apply object-level authorization to files, tickets, devices, and other user-specific records.

Permission-code enforcement is implemented. Department scoping and complete per-object authorization require additional review.

**Evidence:** `uitop/core/permissions.py`, `uitop/core/ui_rbac.py`, `uitop/core/decorators.py`.

---

## NFR-03 — Availability and reliability

**Status:** Partial

The system shall:

1. Provide a health endpoint for agent and connector clients.
2. Continue operating when an agent or site connector temporarily loses connectivity.
3. Retry failed agent authentication and telemetry operations.
4. Preserve local data in a persistent database and file store.
5. Define database migration execution as a deployment step.
6. Provide a documented production WSGI deployment command.
7. Provide a real backup and restore process for the platform database and file repository.
8. Provide readiness/liveness checks that verify application and database availability.
9. Define a recovery point objective (RPO) and recovery time objective (RTO) for organizational operations.

The current backup/restore module is a UI simulation, and no high-availability or disaster-recovery implementation exists.

**Evidence:** `uitop/api/v1/agents.py`, `uitop/api/v1/connectors.py`, `desktop_app.py`, `uitop/services/backup_view.py`, `README.md`.

---

## NFR-04 — Performance and capacity

**Status:** Partial

The system shall:

1. Enforce upload size limits and workspace quotas.
2. Use bounded audit queries and paginated UI collections.
3. Use connection pre-ping and disable SQLAlchemy modification tracking.
4. Execute LAN scans asynchronously with bounded worker pools.
5. Batch agent telemetry submissions.
6. Provide retention, downsampling, or archival policies for performance samples, events, alerts, and audit data.
7. Avoid N+1 queries on inventory and monitoring lists.
8. Apply query-level filtering and pagination to API inventory endpoints.
9. Define target response times for login, dashboard, inventory, ticket, and report views.
10. Define a supported maximum number of agents, connectors, devices, and concurrent scans.

The current implementation has unbounded inventory API queries, N+1 patterns, no telemetry retention, and large per-page stylesheet/script loading without a build step.

**Evidence:** `uitop/config.py`, `uitop/services/network_scan.py`, `uitop/api/v1/inventory.py`, `uitop/services/monitoring_view.py`.

---

## NFR-05 — Scalability and deployment

**Status:** Partial

The system shall:

1. Support SQLite for local/desktop deployments and PostgreSQL for production.
2. Run under a multi-worker WSGI deployment.
3. Keep authentication state in the database where it must survive restarts.
4. Move pairing codes, scan jobs, notifications, and scheduled work to shared persistent storage before horizontal scaling.
5. Provide a background-job mechanism for scans, notifications, telemetry processing, and scheduled reports.
6. Provide repeatable deployment artifacts such as a service definition, container definition, or platform configuration.
7. Run database migrations automatically or as an explicit release step.

The current in-memory pairing and scan-job state is not shared across workers and therefore conflicts with a multi-worker production deployment.

**Evidence:** `uitop/config.py`, `uitop/services/pairing.py`, `uitop/services/network_scan.py`, `README.md`.

---

## NFR-06 — Usability and accessibility

**Status:** Partial

The system shall:

1. Provide a consistent responsive layout for desktop, tablet, and mobile widths.
2. Provide a mobile sidebar with a menu button, overlay dimmer, and Escape-key close behavior.
3. Provide a persistent light/dark theme with readable contrast in both themes.
4. Provide a skip-to-content link and semantic page landmarks.
5. Provide keyboard-visible focus states.
6. Provide status and error feedback through flash messages, toasts, and form validation.
7. Provide accessible labels for interactive controls.
8. Provide reduced-motion behavior for users who request it.
9. Provide print-friendly layouts for reports.
10. Ensure text and essential icons meet the project’s contrast target in light and dark themes.

Current gaps include incomplete focus management in modals, missing labels for some icon-only controls, and the absence of a formal automated contrast audit.

**Evidence:** `static/css/responsive.css`, `static/js/theme.js`, `static/js/sidebar.js`, `static/js/notifications.js`, `templates/layouts/base.html`.

---

## NFR-07 — Compatibility

**Status:** Implemented for the supported Windows-first baseline

The system shall:

1. Support current stable versions of Python supported by the deployment environment.
2. Support modern evergreen browsers.
3. Support Windows desktop deployment and Windows agent operation.
4. Support LAN agents connecting to the server over HTTP or HTTPS.
5. Support a documented fallback when `pywebview` is not installed.
6. Support cloud deployment where an on-premises site connector bridges LAN discovery.

Third-party CDN assets (fonts, Font Awesome, Chart.js) shall be either locally bundled or protected by an explicit availability and integrity policy for air-gapped organizational networks.

**Evidence:** `desktop_app.py`, `agents/`, `templates/layouts/base.html`, `requirements.txt`, `requirements-desktop.txt`.

---

## NFR-08 — Observability and auditability

**Status:** Partial

The system shall:

1. Provide structured application logging with configurable severity and rotation.
2. Provide request correlation identifiers.
3. Expose health and readiness endpoints.
4. Provide metrics for request rate, error rate, latency, agent connectivity, connector connectivity, scan duration, telemetry ingestion, and queue depth.
5. Emit server-side alerts when devices, agents, connectors, or jobs exceed configured thresholds.
6. Provide an audit trail for user and machine actions.
7. Define retention, archival, and export policies for operational data.
8. Ensure error reporting does not disclose secrets or internal stack traces.

The audit UI and machine-action records exist, but application logging, metrics, tracing, alerting, and server-side threshold evaluation are not implemented.

**Evidence:** `uitop/services/audit.py`, `uitop/services/audit_view.py`, `uitop/services/notifications.py`, `uitop/core/errors.py`.

---

## NFR-09 — Error handling and contract consistency

**Status:** Partial

The system shall:

1. Return typed API errors with stable codes, messages, and details.
2. Use the documented success and error envelopes consistently.
3. Return appropriate HTTP status codes for authentication, authorization, validation, conflict, and not-found conditions.
4. Present actionable, non-sensitive feedback in the UI.
5. Continue agent operation after an individual command or telemetry failure.
6. Log unexpected failures with correlation information.
7. Ensure provider errors and internal exceptions do not leak secrets to users.

The Copilot and a small number of discovery paths currently return simplified error strings or raw exception text instead of the standard envelope.

**Evidence:** `uitop/core/errors.py`, `uitop/schemas/__init__.py`, `uitop/api/v1/__init__.py`, `uitop/services/copilot.py`.

---

## NFR-10 — Data management and retention

**Status:** Partial

The system shall:

1. Store structured records in a relational database.
2. Use migrations for schema changes.
3. Store files under a configurable root with server-derived paths.
4. Enforce upload and per-user workspace limits.
5. Maintain activity and version history for controlled documents and files.
6. Define retention and archival periods for audit, telemetry, events, alerts, files, and backups.
7. Define data-subject access, correction, and deletion procedures appropriate to POPIA and organizational policy.
8. Provide an exportable, restorable copy of the platform database and file repository.

The current system implements versioning and soft deletion for some files, but not a complete retention, archival, or data-subject erasure policy.

**Evidence:** `uitop/config.py`, `uitop/services/files_view.py`, `uitop/models/files.py`, `uitop/services/audit.py`.

---

## NFR-11 — Maintainability and testability

**Status:** Partial

The system shall:

1. Separate route, service, model, and presentation logic.
2. Use an application factory and environment-specific configuration.
3. Provide migration tooling and CLI commands for seeding and administrator creation.
4. Provide automated unit, integration, API, and UI tests.
5. Provide a testing configuration with isolated database state.
6. Define linting, formatting, and type-checking commands in the development workflow.
7. Avoid leaking credentials into source control or packaged binaries.
8. Document API changes and database migrations with each release.

A testing configuration exists, but the current baseline has no complete automated test suite and no declared lint/type-check command.

**Evidence:** `uitop/__init__.py`, `uitop/config.py`, `uitop/seeds/cli.py`, `migrations/`, `requirements.txt`.

---

## NFR-12 — Integration safety

**Status:** Partial

The system shall:

1. Treat agent and connector credentials as machine identities.
2. Scope agent and connector permissions to the minimum required capabilities.
3. Use allow-listed remote commands only.
4. Validate CIDR ranges and enforce private-network boundaries for discovery.
5. Encrypt or otherwise protect credentials stored on endpoints.
6. Verify the authenticity and integrity of downloaded installers and executable artifacts.
7. Require HTTPS for non-local deployments and for installer bootstrap flows.
8. Document the data sent to external AI, email, webhook, or integration providers.

Current installer endpoints are intentionally public for bootstrap convenience, and agent credentials are stored locally in plain JSON without endpoint-level encryption or ACL hardening.

**Evidence:** `uitop/services/agents.py`, `uitop/services/site_connectors.py`, `agents/install.ps1`, `agents/install_site_connector.ps1`, `routes/auth.py`.

---

# 5. Data entities

The baseline data model covers:

- Identity: `User`, `Role`, `Permission`, `Department`.
- Authentication and machine identity: `RefreshToken`, `ApiClient`, `AgentEnrollmentToken`.
- Inventory: `Computer`, `Server`, `NetworkDevice`, `Printer`.
- Telemetry: `PerformanceSample`, `AgentEvent`, `AgentAlert`, `AgentCommand`.
- Site connectivity: `SiteConnector`, `SnmpProfile`.
- Assets: `Asset`, `AssetCategory`, `AssetVendor`, `AssetAssignment`, `AssetRequest`.
- Helpdesk: `Ticket`, `TicketComment`, `TicketObjectLink`, `TicketTimeLog`, `TicketActivity`, `KnowledgeArticle`.
- Files and documents: `RepoFile`, `FileVersion`, `FileLink`, `FileTag`, `FilePermission`, `FileActivity`, `DocumentApproval`.
- Operations: maintenance work orders, checklists, parts, plans, activity records.
- Security: posture, threats, vulnerabilities, incidents, policies, user activity, and security audit events.
- Workflows: definitions, instances, events, and work tasks.
- Platform services: `AuditLog`, `SystemSetting`, `AppNotification`, `CopilotSession`, and `CopilotMessage`.

**Evidence:** `uitop/models/__init__.py` and the model modules under `uitop/models/`.

---

# 6. Current implementation gaps and priorities

The following items should be treated as release blockers or high-priority roadmap work before a production organizational rollout.

## P0 — Security and data protection

1. Remove plaintext agent credentials from the working tree and exclude them from packaged binaries.
2. Add CSRF protection to all state-changing UI forms.
3. Configure secure session cookies and production security headers.
4. Replace default secrets with mandatory production secret provisioning and rotation.
5. Add login rate limiting, lockout, and failed-login auditing.
6. Restrict CORS to approved origins rather than defaulting to `*`.
7. Require HTTPS for non-local deployments and protect installer downloads.
8. Review Copilot data egress and add a consent, retention, and redaction policy.

## P1 — Production correctness and scale

1. Replace mock-only Backup/Restore behavior with a real backup engine and recovery procedure.
2. Replace hard-coded software, license, vendor, monitoring, analysis, report, and security data with persisted sources.
3. Move pairing codes and scan jobs out of process memory.
4. Add telemetry retention/downsampling and avoid per-request audit commits for high-frequency telemetry.
5. Add pagination and SQL-level filtering to inventory API endpoints.
6. Implement server-side threshold alerting for offline devices, CPU/memory thresholds, and connector failures.
7. Add scheduling for notifications, reports, scans, and retention jobs.
8. Add a real application backup and disaster-recovery runbook.

## P1 — Access and workflow governance

1. Enforce object- and department-level authorization for files, tickets, devices, and reports.
2. Require `roles:manage` for role assignment through every interface.
3. Add confirmation, cooldown, and authorization checks for disruptive remote commands.
4. Implement enrollment-token revocation and credential rotation interfaces.
5. Complete password policy enforcement consistently across UI, API, and administration.

## P2 — Quality and operations

1. Add automated unit, integration, API, and browser tests.
2. Add structured logging, request correlation, metrics, and alerting.
3. Add CI checks for linting, formatting, type checking, migrations, and security scanning.
4. Add accessibility tests and a documented contrast target.
5. Bundle or locally host CDN dependencies for reliable air-gapped operation.
6. Pin dependency versions with a reproducible lock file.

---

# 7. Acceptance summary

A release candidate should demonstrate all of the following:

- An administrator can seed or create an account, migrate the database, and start the application.
- A user can sign in, receive only permitted navigation, and access only permitted routes.
- An agent can enroll, report inventory/performance/events/alerts, and receive an allow-listed command.
- A site connector can discover private-LAN hosts and printers and ingest results idempotently.
- An employee can connect a device, view permitted self-service information, and submit a ticket or catalog request.
- A helpdesk user can manage tickets and knowledge articles within their permission scope.
- An operator can view inventory, assets, maintenance, and reports, with clear indication of any demo or incomplete data.
- Administrators can manage users, roles, settings, and audit records.
- Audit records capture human and machine actions with actor, resource, result, and timestamp.
- The application remains usable in light and dark themes and at supported viewport widths.
- Production deployment documentation, secret management, backup/recovery, monitoring, and security hardening are complete.

**Primary implementation evidence:** `README.md`, `routes/`, `uitop/`, `templates/`, `static/`, `agents/`, `desktop_app.py`, `migrations/`, and `requirements*.txt`.