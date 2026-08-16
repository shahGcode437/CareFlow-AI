# CareFlow AI — Team Roles & Branching Strategy

**Project:** CareFlow AI — Agentic Healthcare Appointment Management System  
**Document:** 09 — Team Roles & Branching Strategy

## 1. Purpose

This document defines how the two-person CareFlow AI team will divide implementation responsibilities and collaborate through Git/GitHub.

The project is an AI Front-Office Copilot for small healthcare clinics. Its MVP focuses on front-office automation, including patient enquiries and appointment coordination while keeping healthcare staff in control. The project context describes patients contacting clinics through phone calls, WhatsApp, walk-ins, and websites, while reception staff currently perform repetitive appointment and information tasks.

## 2. Team Working Model

```text
Shared GitHub Repository
        │
        └── main
             │
       ┌─────┴─────┐
       ↓           ↓
Backend / AI    Frontend
   Branch        Branch
       │           │
       └─────┬─────┘
             ↓
        Integration
             ↓
           main
```

`main` is the stable, integrated branch.

## 3. Role A — Backend & Agentic AI

Primary responsibilities:

- FastAPI backend.
- Pydantic schemas and validation.
- Appointment service layer.
- Excel-based appointment repository operations.
- Appointment availability checking.
- Appointment creation/confirmation.
- Appointment update.
- Appointment cancellation/deletion.
- Alternative-slot recommendation logic.
- Appointment agent.
- Agent tool integration and orchestration.
- Backend error handling and testing.
- Backend Docker integration.
- MLflow integration if a meaningful and practical use case is implemented.

Primary flow:

```text
Patient Request
      ↓
Agent
      ↓
Appointment Tool
      ↓
Appointment Service
      ↓
Excel Repository
      ↓
Appointment Result
```

## 4. Role B — Frontend

Primary responsibilities:

- Frontend application structure.
- Appointment request interface.
- Patient input forms.
- Availability/result display.
- Appointment confirmation interface.
- Appointment update interface.
- Appointment cancellation interface.
- FastAPI integration.
- Frontend validation and error display.
- Frontend testing.
- Frontend Docker integration where applicable.

Primary flow:

```text
Patient
   ↓
Frontend UI
   ↓
FastAPI API
   ↓
Backend / Agent
   ↓
Appointment Result
   ↓
Frontend UI
```

The frontend must not directly modify the Excel repository.

## 5. Shared Responsibilities

Both contributors should understand:

- Overall architecture.
- API contracts.
- Agent workflow.
- Integration testing.
- Git/GitHub workflow.
- Debugging.
- Docker workflow.
- Final README/documentation.
- 3MT poster.
- VIVA preparation.
- Complete technical flow.

## 6. Initial Branch Strategy

The repository currently has:

```text
main
```

When implementation begins, use focused branches:

```text
main
│
├── feature/backend-agent
│
└── feature/frontend
```

Additional branches may be created when actually needed:

```text
feature/mlflow
feature/voice
feature/docker
feature/testing
```

They are not required immediately.

## 7. Branch Ownership

### Backend / Agentic AI

`feature/backend-agent`

Typical work:

```text
FastAPI
Pydantic
Appointment Repository
Appointment Service
Agent Tools
Agent Orchestration
Backend Tests
Backend Docker
```

### Frontend

`feature/frontend`

Typical work:

```text
UI
Appointment Forms
Availability Display
Confirmation
Update
Cancellation
API Integration
Frontend Tests
Frontend Docker
```

## 8. Branch Creation

Branches should start from the latest stable `main`.

Backend example:

```powershell
git checkout main
git pull origin main
git checkout -b feature/backend-agent
```

Frontend example:

```powershell
git checkout main
git pull origin main
git checkout -b feature/frontend
```

## 9. Development Workflow

```text
main
 ↓
Pull latest main
 ↓
Create / switch to feature branch
 ↓
Implement focused feature
 ↓
Run tests
 ↓
Inspect changes
 ↓
Commit meaningful changes
 ↓
Push feature branch
 ↓
Review
 ↓
Merge into main
 ↓
Pull latest main
```

Avoid long-lived branches containing unrelated changes.

## 10. Commit Convention

Recommended format:

```text
type: short description
```

Examples:

```text
feat: add appointment availability service
feat: add appointment CRUD tools
feat: implement appointment agent
test: add appointment service tests
fix: handle unavailable appointment slots
feat: add appointment request form
feat: integrate appointment availability API
fix: handle API validation errors
docs: update frontend API integration guide
chore: update Docker configuration
```

Avoid vague messages such as `update`, `changes`, `final`, `done`, or `working`.

## 11. Integration Rules

Backend and frontend integrate through the approved FastAPI API contracts.

Correct:

```text
Frontend
   ↓
FastAPI
   ↓
Agent / Service
   ↓
Excel Repository
```

Incorrect:

```text
Frontend
   ↓
Excel file directly
```

This keeps the data layer behind the backend/service boundary.

## 12. Contract-First Collaboration

Before implementing an integration point, refer to:

```text
Pydantic Schemas
        ↓
FastAPI API Contracts
        ↓
Agent Tool Contracts
        ↓
Service Design
        ↓
Implementation
```

If a contract needs to change:

1. Identify the reason.
2. Discuss the impact with the other contributor.
3. Update the relevant documentation.
4. Update affected code.
5. Test the integration.
6. Commit the related changes.

Do not silently change an agreed API contract just to simplify one module.

## 13. Pull Request / Merge Expectations

Before merging into `main`:

- Feature works.
- Relevant tests pass.
- No secrets are committed.
- No unrelated files are changed.
- Existing functionality is not unnecessarily broken.
- API contracts remain consistent.
- Documentation is updated when required.

For important features, the other contributor should inspect the change before integration.

## 14. Conflict Resolution

If both branches modify the same file:

1. Identify the conflicting changes.
2. Determine which change is required.
3. Preserve both where they serve different responsibilities.
4. Test the resolved result.
5. Commit the resolution.

Never overwrite the other contributor's work blindly.

## 15. Responsibility Boundaries

### Backend owns

```text
Data
Business logic
Appointment operations
Agent
Tools
API behavior
```

### Frontend owns

```text
Presentation
User interaction
Forms
Client-side validation
API consumption
```

### Shared

```text
Integration
Testing
Docker
Documentation
Git/GitHub
Final presentation
```

## 16. MVP Priority

Prioritize the working appointment MVP over optional features.

### Highest priority

```text
1. Appointment availability
2. Appointment creation
3. Appointment update
4. Appointment cancellation
5. Alternative slot recommendation
6. Agent/tool workflow
7. FastAPI integration
8. Frontend integration
9. Testing
```

### Secondary priority

```text
Docker
MLflow
Voice interface
Additional automation
```

Optional features must not delay the core demonstrable workflow.

## 17. MLflow Responsibility

MLflow is an encouraged capstone component but is not the core appointment data layer.

If implemented, the backend/AI contributor will initially own the technical integration, while both contributors should understand its purpose and explain it during VIVA.

The team should be able to explain:

- What is being tracked?
- Why is it being tracked?
- What information does MLflow provide?
- Where does MLflow fit in the architecture?

A small meaningful implementation is preferable to a complex implementation that adds risk.

## 18. Docker Responsibility

The backend/AI contributor initially owns backend containerization.

The frontend contributor owns frontend containerization where applicable.

Both contributors must understand how the final system is started and integrated through Docker.

Target:

```text
Docker Desktop
├── Backend
├── Frontend
└── MLflow (if implemented)
```

The final container structure will be confirmed during implementation.

## 19. Final Integration

Final integration is a shared responsibility:

```text
Backend branch
      ↓
Backend tested
      ↓
Frontend branch
      ↓
Frontend tested
      ↓
API integration tested
      ↓
End-to-end appointment workflow
      ↓
Docker verification
      ↓
Optional MLflow verification
      ↓
Final main
```

The final `main` branch must contain the presentation-ready version.

## 20. Claude / AI Coding Assistant Collaboration Rule

Claude should not assume that one contributor owns the entire project.

When working on a module, Claude should:

1. Read the relevant project documentation.
2. Identify the module owner.
3. Respect existing contracts.
4. Avoid modifying another contributor's module unnecessarily.
5. Clearly identify cross-module changes.
6. Keep implementation modular.
7. Identify required integration points before changing them.
8. Prefer small, testable implementation steps.
9. Never introduce secrets.
10. Preserve MVP priorities.

Claude should treat the GitHub repository and approved `/docs` directory as the source of truth.

## 21. Current Team Assignment

| Area | Backend / AI Contributor | Frontend Contributor |
|---|---|---|
| FastAPI | Primary | Understand integration |
| Pydantic | Primary | Understand contracts |
| Excel CRUD | Primary | No direct access |
| Appointment Service | Primary | Understand outputs |
| Agent | Primary | Understand workflow |
| Agent Tools | Primary | Understand integration |
| Frontend UI | Support integration | Primary |
| API Integration | Shared | Primary |
| Backend Testing | Primary | Support |
| Frontend Testing | Support | Primary |
| Docker | Backend primary | Frontend primary |
| MLflow | Primary if implemented | Understand |
| Git/GitHub | Shared | Shared |
| Documentation | Shared | Shared |
| 3MT/VIVA | Shared | Shared |

This is the initial working assignment and may be updated if the team changes responsibilities.

## 22. Definition of Done for Team Setup

Team setup is complete when:

- Both contributors know their responsibilities.
- `main` remains the stable branch.
- Feature branch names are agreed.
- Backend/frontend boundaries are understood.
- API contracts are treated as shared interfaces.
- Both contributors understand the overall system.
- The teammate has access to the relevant project documentation.
- Each contributor can work independently without directly modifying the other's core module.
- Integration responsibilities are clear.

## Final Principle

**Separate responsibilities, share understanding, integrate through contracts, and keep `main` stable.**

The purpose of branching is not to create complexity. It is to allow both contributors to work independently while keeping the final CareFlow AI system coherent, testable, and ready for integration.
