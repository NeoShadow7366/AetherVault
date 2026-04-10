---
description: Constraints preventing autonomous rule modification and defining the rigorous knowledge review process required to update system memory.
---

# Learning and Memory Policy

Autonomous structural learning is strictly prohibited. 

## Knowledge Review Process (Mandatory)

When any agent identifies a recurring pattern, lesson, or improvement that should become a rule or long-term memory:

1. The agent **MUST NOT** directly edit `agents.md`, `.agents/` rules, or any persistent rule file.
2. The agent **MUST** generate a standalone markdown artifact named `proposed_rule_update.md` (or similar) containing:
   - Clear rationale for the proposed change
   - Impact assessment (effect on context size, zero-dependency, future tasks, etc.)
   - Proposed exact diff or patch
   - Suggested sunset/review clause (e.g., "Re-evaluate after 30 days or X tasks")
3. The agent **MUST** halt further execution on this topic and explicitly prompt the user for review and approval.
4. Optionally, the **Architecture Guardian** may first review the proposal (read-only) and append an "Architecture Compliance Note" before presenting it to the user.
5. **Only after explicit user approval** (e.g., "Approved – commit changes") may the agent apply the update.

## Risks Mitigated
*   **Rule Bloat / Context Poisoning**: Prevents highly specific, transient fixes for edge cases from crystalizing into permanent rules that consume context limits and cause AI confusion.
*   **Architectural Drift**: Prevents structural violations, particularly preserving the strict zero-dependency AetherVault philosophy.
*   **Escalation Deadlocks**: Resolves conflicts between guardians constantly reverting each other's changes by enforcing a clear hierarchy.
*   **Uncontrolled "Learning"**: Ensures agents do not adapt behaviors that contradict core project principles without oversight.

## Additional Guidelines
*   Transient fixes and edge-case observations **SHALL** remain session-only or in temporary logs unless they meet a high bar for permanence.
*   All permanent structural changes **MUST** be accompanied by a lightweight Architectural Decision Record (ADR) in the `.agents/architectural_decisions/` folder.
*   No agent **SHALL** attempt to bypass the Human-in-the-Loop gate for core files.
