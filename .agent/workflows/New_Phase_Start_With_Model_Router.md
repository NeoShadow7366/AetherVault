---
description: Workflow that starts every major development phase by invoking the Intelligent Model Router skill to ensure the optimal AI model is selected before work begins.
---

# New Phase Start — Model Router Integration

This workflow MUST be executed at the beginning of every major development phase, sprint, or feature implementation.

## Prerequisites

1. Read `agents.md` — understand all three layers
2. Have the task/sprint definition ready
3. Know what files and domains will be touched

## Step 1: Invoke the Intelligent Model Router

Before writing any code or making architectural decisions:

- [ ] Read `.agents/skills/intelligent_model_router/SKILL.md`
- [ ] Classify the incoming task using the Decision Tree
- [ ] Determine the recommended model tier (COMPLEX / STANDARD / FAST)

## Step 2: Apply the Pause-and-Confirm Protocol

Follow `.agent/rules/model_switch_confirmation.md`:

- [ ] Output the model recommendation in standard format
- [ ] If a switch is needed, explicitly ask the user to change models in the AetherVault UI
- [ ] **WAIT** for the user's confirmation before proceeding
- [ ] Log the decision (accepted, declined, or already on correct model)

## Step 3: Read Relevant Skills

After model confirmation:

- [ ] Check `.agents/skills/` for skills relevant to the current task
- [ ] Read each relevant SKILL.md in full
- [ ] Note any input/output contracts that must be followed

## Step 4: Research the Codebase

- [ ] Read existing implementation files that will be modified
- [ ] Check the database schema if the feature touches `metadata_db.py`
- [ ] Identify cross-platform concerns (Windows vs UNIX branching)
- [ ] Review `.agent/rules/` for applicable safety rules

## Step 5: Plan the Work

- [ ] Write out the plan in natural language (what, why, where)
- [ ] Red-Team the plan: "What breaks? What edge case did I miss?"
- [ ] Create or update `implementation_plan.md` artifact
- [ ] Request user review on the plan

## Step 6: Begin Implementation

Only after both model selection AND plan approval:

// turbo-all

- [ ] Implement backend changes first (`.backend/`)
- [ ] Apply database migrations with backward compatibility
- [ ] Update API endpoints in `server.py`
- [ ] Update frontend in `index.html`
- [ ] Run verification steps

## Step 7: Post-Phase Check

- [ ] Re-evaluate model tier if the task scope changed significantly
- [ ] Update relevant SKILL.md files if behavior changed
- [ ] Update `agents.md` if new patterns were introduced
- [ ] Create walkthrough artifact summarizing changes

## Example Usage

```
🔀 MODEL ROUTER RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Task:        Sprint 3 — FLUX.1 Pipeline Integration
🏷️ Complexity:  COMPLEX
🔍 Reasoning:   FLUX.1 requires clip/unet/text_encoder dependency resolution
                and ComfyUI JSON graph topology construction. Multi-engine
                architecture with cross-platform symlink edge cases.
💡 Recommended: Claude Opus 4.6 (Thinking)
⚡ Current:     Gemini 3 Pro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏸️ ACTION: Please switch to Claude Opus 4.6 (Thinking) in the
           AetherVault UI settings before proceeding. Confirm when ready.
```
