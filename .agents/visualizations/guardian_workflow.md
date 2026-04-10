# 🛡️ AetherVault Guardian Workflow Execution (Sequence)

This sequence diagram details the real-time interaction between the guardians when a user introduces a code change. It highlights the primary "Happy Path" along with conditional escalations.

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor U as User / Developer
    participant AG as Architecture Guardian
    participant API as API Contract Librarian
    participant QA as QA Guardian
    participant STR as Safe Test Runner
    participant RHD as Runtime Health Doctor
    participant EHD as Ecosystem Health Dashboard

    U->>AG: File Save / Commit (Initiate Change)
    activate AG
    
    %% Phase 1: Architecture & API Boundaries
    Note over AG,API: 1. Design & Boundary Validation
    AG->>API: Request boundary & payload validation
    activate API
    
    alt Payload Drift Detected
        API-->>AG: Error: JSON Mismatch Detected
        AG-->>U: ⛔ BLOCK: API Contract Violation
    else Contracts Valid
        API-->>AG: OK: Boundaries Maintained
    end
    deactivate API

    AG->>AG: Analyze structural impact & zero-dependency rule
    
    alt Architectural Violation
        AG-->>U: ⛔ BLOCK: Structural/Dependency Hazard
    else Architecture Clean
        AG->>QA: Approve & Trigger Test Lifecycle
    end
    deactivate AG

    %% Phase 2: Testing & Timeout Protection
    activate QA
    Note over QA,STR: 2. Safe Test Execution
    QA->>STR: Wrap tests in OS-level Timeout Envelope (60s)
    activate STR
    STR->>STR: Execute pytest .tests/ within timeout
    
    alt Timeout Exceeded
        STR-->>QA: TIMEOUT: Pipeline killed after 60s
        QA-->>AG: ESCALATE: Deadlock/Structural Breakage
        activate AG
        AG-->>U: ⛔ BLOCK: Escalated Testing Failure
        deactivate AG
    else Tests Complete
        STR-->>QA: Return test results
    end
    deactivate STR

    alt Cosmetic / Minor Fail
        QA->>QA: Apply Self-Healing (locators/assertions)
        QA->>STR: Re-run updated tests
    else Structural Fail
        QA-->>AG: ESCALATE: Structural test failure
        activate AG
        AG-->>U: ⛔ BLOCK: Escalated Structural Failure
        deactivate AG
    else All Tests Pass
        QA->>RHD: Request Infrastructure Pre-flight Sweep
    end
    deactivate QA

    %% Phase 3: Runtime Sweeps
    activate RHD
    Note over RHD: 3. Pre-Flight Infrastructure Sweeps
    RHD->>RHD: Scan for DB Locks / Zombie Processes / Broken Junctions
    
    alt Infra Defect Found
        RHD-->>U: ⛔ BLOCK: Infrastructure Broken
    else Health OK
        RHD-->>U: ✅ DEPLOYMENT SUCCESS (Ready)
    end
    
    %% Phase 4: Observability
    RHD->>EHD: Push Final Telemetry & Status Logs
    deactivate RHD
    
    Note over U,EHD: 4. Ecosystem Observability
    activate EHD
    U->>EHD: Invokes /health_dashboard
    EHD-->>U: Serves Consolidated System Overview
    deactivate EHD
```

## Flow Explanation

1. **Initiation & Validation**: 
   The sequence begins when the developer saves a file. The **Architecture Guardian** catches the event and immediately queries the **API Contract Librarian**. If the librarian detects any drift between the frontend components and backend routers, it throws a JSON Mismatch error, allowing the Architecture Guardian to block the commit. If approved, the Architecture Guardian runs its own internal checks for AetherVault/zero-dependency violations.
   
2. **Safe Execution**: 
   Passing the structural checks, the baton is handed to the **QA Guardian**, which delegates actual test execution to the **Safe Test Runner**. The Safe Test Runner wraps all tests in a strict 60-second OS-level timeout envelope. If a test fails on a purely cosmetic issue (locator changes, UI text updates), the QA Guardian enters a self-healing inner loop. If a structural/architectural failure is detected, it escalates to the Architecture Guardian. If a timeout occurs, the pipeline is force-killed and escalated.

3. **Runtime Sweep**: 
   Assuming a perfect test pass, the **Runtime Health Doctor** executes a live sweep of the OS infrastructure. It looks for silent killers like locked SQLite databases, broken NTFS junctions, or orphaned engine processes that tests wouldn't natively catch.

4. **Telemetry Sync**: 
   Upon completion (whether successful or blocked), the current infrastructure footprint logs are funneled into the **Ecosystem Health Dashboard**, which the User pulls on-demand with `/health_dashboard`.

## Documentation Pipeline (Parallel Track)

For documentation changes, a separate pipeline is available via `/Generate_Docs`:

```mermaid
sequenceDiagram
    actor U as User
    participant CA as Codebase Analyst
    participant CD as Codebase Documenter
    participant DG as Doc Guardian

    U->>CA: /Generate_Docs (target feature)
    activate CA
    CA->>CA: Read-only investigation of codebase
    CA-->>CD: Analysis results
    deactivate CA

    activate CD
    CD->>CD: Structure into Markdown layout
    CD-->>DG: Generated documentation
    deactivate CD

    activate DG
    alt Target file exists
        DG->>DG: Backup to docs/dochistory/
    end
    DG->>DG: Write fresh documentation
    DG-->>U: Summary of files created/updated
    deactivate DG
```
