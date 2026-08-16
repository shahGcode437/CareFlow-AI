# CareFlow AI — Capstone Delivery, Git, Collaboration & MLflow Workflow

**Project:** CareFlow AI — Agentic Healthcare Appointment Management System

## 1. Purpose

This document supplements the existing CareFlow AI technical specifications. The existing documents define what the system should do and its technical contracts; this document defines how the project will be developed, version-controlled, collaborated on, tested, packaged, and submitted.

## 2. Capstone Requirements

The final project must be organized in a GitHub repository and demonstrate proper version-control practices, including meaningful commits and branching.

The project should also consider MLflow because it is highly encouraged.

The final VIVA uses the 3 Minute Thesis (3MT) format:
- One poster/slide only.
- The poster must clearly show the technical flow diagram.
- The panel may ask questions based on the poster.
- Everything shown must be explainable by the team.

**Submission deadline:** 6:00 AM, Thursday, 20 August.

## 3. Repository Strategy

Use one shared GitHub repository:

```text
CareFlow-AI/
├── docs/
├── backend/
├── frontend/
├── tests/
├── data/
├── docker/
├── .gitignore
├── README.md
└── requirements.txt
```

The exact implementation structure may be adjusted after Phase-0 inspection.

## 4. Git Branching Strategy

`main` represents the stable, integrated project state.

Feature work should use focused branches such as:

```text
main
├── feature/backend-agent
├── feature/frontend
├── feature/mlflow
└── feature/voice
```

Not every branch must be created immediately. Create a branch when that feature is actually being developed.

Rules:
1. Avoid direct development on `main` for substantial features.
2. Use meaningful branch names.
3. Keep branches focused.
4. Test before merging.
5. Merge completed work into `main` after review/testing.
6. Avoid unrelated changes in one branch.

## 5. Team Collaboration

### Backend / Agentic AI

Primary responsibilities include:
- FastAPI backend.
- Pydantic schemas.
- Appointment service.
- Excel repository operations.
- Appointment agent.
- Agent tools.
- Tool orchestration.
- Backend testing.
- Docker integration for backend services.
- Supporting MLflow integration where appropriate.

### Frontend

Primary responsibilities include:
- User interface.
- Appointment request interface.
- Availability display.
- Confirmation/update/cancellation interactions.
- FastAPI integration.
- Frontend testing.
- Frontend Docker integration where appropriate.

### Shared Responsibilities

Both contributors should understand and participate in:
- Architecture.
- Integration.
- Testing.
- Git/GitHub.
- Final documentation.
- 3MT poster.
- VIVA preparation.

## 6. Documentation Source of Truth

Approved project specifications are maintained under `/docs`.

The dependency hierarchy is:

```text
Master Specification
        ↓
Excel Model
        ↓
Pydantic Data Contracts
        ↓
FastAPI API Contracts
        ↓
Agent Tool Contracts
        ↓
Service Design
        ↓
Implementation Guide
        ↓
Actual Code
```

If implementation requires a genuine specification change:
1. Identify the change.
2. Update the relevant documentation.
3. Review dependent components.
4. Update implementation.
5. Commit documentation and code with meaningful messages.

## 7. Commit Standards

Recommended format:

```text
type: short description
```

Examples:

```text
docs: add capstone delivery workflow
feat: add appointment availability service
feat: add appointment agent tools
feat: add frontend appointment form
fix: handle unavailable appointment slots
test: add appointment service tests
refactor: simplify Excel repository layer
chore: add Docker configuration
```

Avoid vague messages such as `update`, `changes`, `final`, or `done`.

## 8. Pull Request / Integration Workflow

```text
main
  ↓
Create feature branch
  ↓
Implement
  ↓
Test locally
  ↓
Meaningful commits
  ↓
Push branch
  ↓
Review / inspect
  ↓
Merge into main
  ↓
Verify integrated system
```

## 9. MLflow Strategy

MLflow is **highly encouraged**, but CareFlow AI is primarily an Agentic AI appointment-management system rather than a conventional model-training project.

Therefore, MLflow should not be forced into the core appointment CRUD workflow merely to claim usage.

Where practical, MLflow may support:
- AI/agent experiment tracking.
- Prompt/configuration variants.
- Evaluation runs.
- Other measurable AI workflow experiments.

Conceptually:

```text
CareFlow AI
├── FastAPI
├── Agent
├── Tools
├── Appointment Service
├── Excel Repository
└── MLflow
    └── AI / experiment tracking
```

Priority:

```text
P0 — Core appointment functionality
P0 — Agent and tools
P0 — Git/GitHub workflow
P0 — Testing
P1 — Docker
P1 — MLflow
P1 — Voice/additional capabilities
```

If time is limited, a stable MVP takes priority over a complex MLflow implementation.

## 10. Docker Strategy

Docker is part of the engineering/deployment workflow.

Conceptual target:

```text
Docker Desktop
├── CareFlow Backend
│   ├── FastAPI
│   ├── Agent
│   ├── Tools
│   └── Services
├── Frontend
└── MLflow
```

The exact container architecture will be decided after Phase-0 inspection.

## 11. Environment and Secrets

Never commit:
- API keys.
- Tokens.
- Passwords.
- Private credentials.
- Secret environment variables.

Use local `.env` files where needed and keep them ignored by Git.

A safe `.env.example` may be committed.

```text
.env          → local only
.env.example  → safe template
```

## 12. Testing and Integration

Verify:

### Appointment
- Create appointment.
- Check doctor availability.
- Confirm an available slot.
- Recommend alternatives when unavailable.
- Update appointment.
- Cancel/delete appointment.
- Handle invalid requests.
- Handle unavailable slots.
- Preserve data correctly.

### Agent
- Understand supported requests.
- Select the appropriate tool.
- Use valid tool arguments.
- Return clear responses.
- Avoid incorrect data modifications.

### API
- Validate requests.
- Return expected response structures.
- Handle errors.

### Frontend
- Submit appointment request.
- Display availability/result.
- Support update/cancellation workflows.
- Handle API errors.

### Integration
Frontend, backend, agent, tools, service layer, and Excel repository must work together as one demonstrable system.

## 13. Final Repository Preparation

```text
Code
 ↓
Tests
 ↓
Documentation
 ↓
Docker
 ↓
Optional MLflow
 ↓
README
 ↓
Git history review
 ↓
Final main branch
 ↓
GitHub submission
```

The final `main` branch must represent the presentation-ready version.

## 14. README Requirements

The final README should explain:
1. Project name.
2. Problem.
3. Solution.
4. Key features.
5. Technical architecture.
6. Agent workflow.
7. Technology stack.
8. Project structure.
9. Setup.
10. Environment variables.
11. Local execution.
12. Docker execution.
13. Testing.
14. MLflow usage, if implemented.
15. Team contributions.
16. Demo/use cases.

## 15. 3MT Poster

The single poster should communicate the technical flow clearly.

Target flow:

```text
Patient
   ↓
Chat / Voice Interface
   ↓
CareFlow AI Agent
   ↓
Appointment Tools
   ↓
Appointment Service
   ↓
Excel Repository
   ↓
Appointment Result
   ↓
Patient / Staff
```

Supporting technologies can include:

```text
FastAPI
Pydantic
Agentic AI
Git/GitHub
Docker
MLflow
```

Do not show technical claims that the team cannot explain.

## 16. VIVA Preparation

The team must be able to explain:
- The problem and users.
- Why CareFlow AI is needed.
- Appointment request flow.
- Agent/tool selection.
- CRUD operations.
- Excel repository.
- FastAPI.
- Pydantic.
- Git/GitHub.
- Docker.
- MLflow usage or reason for limited use.
- Team contributions.
- MVP limitations.
- Future improvements.

## 17. Change Management

The architecture should remain extensible.

Possible future changes include:

```text
Excel Repository → Database Repository
Chat Interface   → Voice Interface
Single Agent     → Supervisor + Specialized Agents
Single Clinic    → Multi-clinic Platform
```

Prefer modular services, explicit contracts, and replaceable components.

## 18. Claude / AI Coding Assistant Rules

Claude should treat repository documentation as the project source of truth.

Before modifying code, Claude should:
1. Inspect the repository.
2. Read relevant documentation.
3. Identify affected components.
4. Avoid unnecessary architectural changes.
5. Preserve approved contracts unless a change is explicitly approved.
6. Keep modules loosely coupled.
7. Follow the Git workflow.
8. Never expose secrets.
9. Prefer small, testable implementation steps.
10. Explain major architectural decisions before implementing them.
11. Do not implement optional features before the core MVP is stable.
12. Keep implementation compatible with Docker.
13. Use MLflow only where it provides meaningful value.
14. Never invent requirements unsupported by the project specifications.

Generated code must be inspected, tested, and verified by the team.

## 19. Development Sequence

```text
Phase 0 — Project / Environment Inspection
        ↓
GitHub + Documentation Baseline
        ↓
Team Roles
        ↓
Feature Branches
        ↓
Environment Setup
        ↓
Backend Foundation
        ↓
Appointment Repository
        ↓
Appointment Service
        ↓
Agent Tools
        ↓
Agent Orchestration
        ↓
FastAPI Integration
        ↓
Frontend Integration
        ↓
Testing
        ↓
Docker
        ↓
MLflow (if practical)
        ↓
Final Integration
        ↓
README + Documentation
        ↓
GitHub Cleanup
        ↓
3MT Poster
        ↓
VIVA Practice
```

## 20. Definition of Done

CareFlow AI is ready for submission when:
- Core appointment workflows work.
- CRUD operations work.
- Availability checking works.
- Alternative slot recommendation works.
- Agent/tool interaction works.
- FastAPI endpoints work.
- Frontend interacts with backend.
- Important workflows are tested.
- Docker setup works.
- GitHub repository is organized.
- Git history demonstrates meaningful development.
- Team contributions are represented.
- MLflow is included if a meaningful implementation is feasible.
- README is complete.
- Final `main` is presentation-ready.
- The team can explain the complete technical flow from the single 3MT poster.

## Final Principle

**Build the smallest reliable CareFlow AI system that solves the defined appointment-management problem. Add supporting engineering features such as Docker, MLflow, voice, and other capabilities only when they improve the project without putting the core MVP at risk.**

The final system must be **working, explainable, reproducible, version-controlled, and demonstrable.**
