---
description: Enforces a mandatory pause-and-confirm workflow when the Intelligent Model Router recommends switching AI models. Prevents agents from proceeding with mismatched model tiers.
---

# Model Switch Confirmation Rule

## Policy

When the Intelligent Model Router skill (`.agents/skills/intelligent_model_router/SKILL.md`) recommends a model switch, the following protocol is **mandatory and non-negotiable**:

## The Three Commandments

### 1. PAUSE — Stop Heavy Work Immediately

```
When a model switch is recommended:
  → Complete any atomic operation in progress (don't leave corrupted state)
  → Do NOT start new file modifications
  → Do NOT begin new architectural decisions
  → Do NOT continue reasoning about complex problems
```

### 2. ASK — Explicitly Request the Switch

```
The agent MUST:
  → Output the model recommendation in the standard format
     (see .agents/skills/intelligent_model_router/SKILL.md → Output Format)
  → Clearly state which model to switch to
  → Clearly state where to switch (AetherVault UI → Model Selection)
  → Explain WHY the switch is needed (1-2 sentences)
```

### 3. WAIT — Do Not Proceed Until Confirmation

```
The agent MUST NOT:
  → Continue coding while waiting for the switch
  → Assume the user will switch and start working
  → Skip the switch and proceed with the current model for COMPLEX tasks
  → Interpret silence as confirmation

The agent MAY:
  → Answer clarifying questions about the recommendation
  → Provide a summary of what work will resume after the switch
  → Suggest alternatives if the user cannot switch immediately
```

## Enforcement Triggers

| Scenario | Required Action |
|----------|----------------|
| Router says COMPLEX but current model is FAST | **HARD STOP** — must switch before proceeding |
| Router says COMPLEX but current model is STANDARD | **RECOMMEND** — strongly suggest but may proceed with caution |
| Router says STANDARD but current model is FAST | **RECOMMEND** — suggest switch, may proceed for non-critical tasks |
| Router says FAST but current model is COMPLEX | **INFORM** — notify user they could save tokens by switching down |

## Exception Handling

### User Declines the Switch
```
IF user explicitly says "proceed without switching":
  → Log the decision
  → Acknowledge the risk (if downgrading from recommended tier)
  → Continue with current model
  → Add a note in any artifacts produced: "⚠️ Produced on [model] — recommended tier was [tier]"
```

### User is Unavailable
```
IF the user does not respond within the conversation:
  → Do NOT proceed with COMPLEX tasks on a FAST model (hard block)
  → MAY proceed with STANDARD tasks on any model (soft recommendation)
  → MAY proceed with FAST tasks on any model (informational only)
```

### Mid-Task Escalation
```
IF a task initially classified as STANDARD reveals COMPLEX issues mid-flight:
  → PAUSE at the next safe stopping point
  → Re-invoke the model router
  → Follow the full pause-and-confirm protocol
  → Do NOT continue COMPLEX reasoning on an underpowered model
```

## Integration

This rule is enforced by:
- **agents.md** Layer 2 → Switching Protocol (steps 1-7)
- **`.agents/skills/intelligent_model_router/SKILL.md`** → Execution Steps 4-5
- **`.agent/workflows/New_Phase_Start_With_Model_Router.md`** → Step 2
