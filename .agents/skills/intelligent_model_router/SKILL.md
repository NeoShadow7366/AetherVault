---
name: Intelligent Model Router
description: AI model tier selection and switching protocol for development tasks. Analyzes task complexity, recommends the optimal AI model (Claude Opus/Thinking, Sonnet, Flash, or Gemini variants), and enforces a pause-and-confirm workflow before proceeding.
keywords:
  - model selection
  - model switching
  - task complexity
  - claude
  - gemini
  - performance optimization
  - agent routing
---

# Intelligent Model Router

## Purpose

Ensure that the correct AI model tier is used for every development task on the Generative AI Manager project. This skill prevents over-spending tokens on trivial tasks (using Opus for a comment fix) and prevents under-powering complex reasoning tasks (using Flash for cross-platform symlink architecture).

## When to Use

```
IF the task involves:
  ├── Starting a new major development phase     → USE THIS SKILL
  ├── Agent output feels slow or imprecise       → USE THIS SKILL
  ├── Switching task types (code → debug → docs)  → USE THIS SKILL
  ├── Complex reasoning is required               → USE THIS SKILL
  └── Continuing work within the same task type   → DO NOT USE THIS SKILL
```

### Mandatory Trigger Points

| Trigger | When | Action |
|---------|------|--------|
| **Phase start** | Beginning of any sprint, feature, or major task | Invoke router → recommend model → wait for switch |
| **Performance degradation** | Agent output is slow, imprecise, or repeatedly failing | Re-evaluate model → escalate if needed |
| **Task-type change** | Switching between architecture, coding, debugging, documentation | Re-evaluate model appropriateness |
| **Complex reasoning** | Payload translators, symlink logic, FLUX structures, race conditions | Escalate to high-capability model |

## Decision Tree — Generative AI Manager Tasks

```
┌─────────────────────────────────────────────────────────┐
│                   TASK ARRIVES                           │
└────────────────────┬────────────────────────────────────┘
                     ▼
          ┌─────────────────────┐
          │  Classify Complexity │
          └──────┬──────────────┘
                 │
     ┌───────────┼───────────────┐
     ▼           ▼               ▼
 [COMPLEX]    [STANDARD]      [FAST]
     │           │               │
     ▼           ▼               ▼
┌──────────┐ ┌──────────┐  ┌──────────┐
│Claude    │ │ Sonnet / │  │ Flash /  │
│Opus /    │ │ Gemini 3 │  │ Gemini 3 │
│Thinking  │ │ Pro      │  │ Pro Low  │
│or Gemini │ │          │  │          │
│3 Pro High│ │          │  │          │
└──────────┘ └──────────┘  └──────────┘
```

### COMPLEX Tasks → Claude Opus/Thinking or Gemini 3 Pro High

These require deep architectural reasoning, multi-step logic, and safety-critical analysis:

- Inference payload translator design (ComfyUI JSON graph topology, A1111 sdapi mapping)
- Cross-platform symlink/junction logic with edge-case handling
- FLUX.1 model structure resolution (clip/unet/text_encoder dependency graphs)
- Multi-engine architecture decisions and refactors
- Database schema migrations with backward compatibility
- OTA update pipeline safety analysis
- Debugging elusive race conditions in background scanners
- Global Vault crawler threading model design
- Security audit and threat modeling

### STANDARD Tasks → Sonnet or Gemini 3 Pro

General-purpose coding and feature work with clear requirements:

- General backend feature implementation (new API endpoints, CRUD operations)
- Frontend UI components and interactivity (JavaScript/CSS in index.html)
- Recipe `.json` template creation for new engines
- Unit/integration test writing
- Documentation generation and README updates
- Routine bug fixes with clear stack traces
- CivitAI/HuggingFace API client modifications
- Gallery and canvas restore feature work

### FAST Tasks → Flash or Gemini 3 Pro Low

Quick, low-complexity tasks that don't require deep reasoning:

- Code formatting, linting, and comment cleanup
- Simple configuration changes (settings.json, gitignore entries)
- Renaming, reorganization, file moves
- Quick lookups and factual questions
- Generating boilerplate (docstrings, type stubs)
- Resolving trivial syntax errors
- Adding logging statements

## Execution Steps

When this skill is invoked, the agent MUST follow these steps in order:

### Step 1: Analyze the Task
```
Read the incoming task description carefully.
Identify:
  - Primary deliverable (what is being built/fixed/documented?)
  - Technical domains touched (symlinks? SQL? subprocess? frontend?)
  - Risk level (can this corrupt user data? break cross-platform?)
  - Estimated scope (single function fix vs. multi-file architecture change)
```

### Step 2: Classify Complexity
```
Map the task to one of three tiers using the Decision Tree above.
IF multiple tiers apply (e.g., "fix a bug that involves symlink race conditions"):
  → Use the HIGHEST applicable tier
```

### Step 3: Check Current Model
```
Determine what model is currently active.
IF the active model matches the recommended tier:
  → Proceed without switching (output a confirmation)
IF the active model is BELOW the recommended tier:
  → MUST request a switch (safety-critical)
IF the active model is ABOVE the recommended tier:
  → RECOMMEND a downgrade (cost optimization, not mandatory)
```

### Step 4: Recommend and Request Switch
```
Output the recommendation in the exact format shown below.
PAUSE all heavy work.
WAIT for the user to confirm the switch in the AetherVault UI.
Do NOT proceed until confirmation is received.
```

### Step 5: Resume Work
```
After the user confirms (or declines) the switch:
  → Log the decision
  → Resume work with the current model
```

## Output Format

When recommending a model switch, output the following block:

```
🔀 MODEL ROUTER RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Task:        [brief task description]
🏷️ Complexity:  [COMPLEX | STANDARD | FAST]
🔍 Reasoning:   [1-2 sentence justification]
💡 Recommended: [exact model name, e.g., "Claude Opus 4.6 (Thinking)"]
⚡ Current:     [current model if known, else "Unknown"]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏸️ ACTION: Please switch to [model name] in the AetherVault UI
           settings before proceeding. Confirm when ready.
```

When no switch is needed:

```
✅ MODEL ROUTER CHECK
━━━━━━━━━━━━━━━━━━━━
📋 Task:        [brief task description]
🏷️ Complexity:  [COMPLEX | STANDARD | FAST]
⚡ Current:     [current model]
✅ Status:      Current model is appropriate. Proceeding.
```

## Integration with agents.md

This skill is referenced in `agents.md` Layer 2 (Orchestration Layer) under:
- **Model Selection & Switching Rules** — defines when to invoke this skill
- **Self-Correction Loops** — includes a model tier check as part of the pre-commit checklist
- **Decision Tree** — mirrors the classification tree defined here

The companion rule at `.agent/rules/model_switch_confirmation.md` enforces the pause-and-confirm protocol, ensuring no agent bypasses the switch request.

The workflow at `.agent/workflows/New_Phase_Start_With_Model_Router.md` integrates this skill as the first step of every major development phase.

## Safety Checklist

- [ ] Never proceed with COMPLEX work on a FAST-tier model
- [ ] Always surface the recommendation to the user — never silently switch
- [ ] Log every model routing decision for auditability
- [ ] Re-evaluate if a task turns out to be more complex than initially classified
- [ ] Respect the user's decision if they decline a switch recommendation
