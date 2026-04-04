# Documentation Maintenance Guide

## Overview
This guide explains how to keep documentation aligned with real system behavior as the AetherVault codebase evolves. It defines a repeatable process using the existing agent workflow (`Codebase Analyst` -> `Codebase Documenter` -> `Doc Guardian`) so updates stay evidence-based, consistent, and safely versioned.

Primary goals:
- Keep architectural and feature documentation accurate.
- Reduce stale or contradictory content.
- Preserve historical versions for traceability via the `Doc Guardian`.
- Use specialized agents for reliable drafting and publishing.

## Scope Guardrails (Mandatory)

These rules prevent core documentation from drifting into a single-feature narrative.

### Core vs Feature Boundaries
- Core documentation must remain system-wide:
  - `docs/index.md` (or `README.md`)
  - `docs/architecture.md`
  - `docs/agent-guide.md`
- Feature-specific depth belongs in `docs/features/*.md` files (e.g., `zero_friction_inference.md`, `global_vault_system.md`).
- Core docs may reference a feature, but must not become feature-led unless the change is genuinely platform-wide.

### Mandatory Scope Gate Checklist (before any write)
Complete all checks before using the writing handoff:
1. Is the change system-wide or feature-specific?
2. If feature-specific, are edits limited to the feature document plus minimal cross-links in core docs?
3. If core docs are being edited, is there evidence from two or more modules/features that justifies a core-level update?
4. Does any core doc now over-index on one feature compared to other major areas?
5. Is there a rollback path (timestamped backup) confirmed via Doc Guardian before publish?

If any answer fails, stop and re-scope before writing.

## How to Update Documentation Using the Agent System
Use the `/Generate_Docs` workflow for every substantial update:

1. **Analyze (Codebase Analyst)**
- Identify what changed in the codebase (e.g., new backend route in `server.py`, new proxy translator, database schema update in `metadata_db.py`).
- Map the change to target docs such as `docs/architecture.md` or a feature page in `docs/features/`.

2. **Format (Codebase Documenter)**
- Request content generation from actual code evidence.
- Ask for either a full regeneration of a document or section-only updates.
- Ensure the output strictly follows the Standard Layout pattern (Overview, Key Features, Architecture, etc.).

3. **Write & Backup (Doc Guardian)**
- The Doc Guardian assumes responsibility for writing the targeted document.
- It creates a `vYYYYMMDD-HHMMSS` timestamped backup in `docs/dochistory/` if the document already exists.
- It then overwrites the main file with finalized Markdown.

## Common Update Scenarios

### Scenario: A New Inference Backend is Added
1. Update `docs/features/zero_friction_inference.md` with the new engine details and proxy translators.
2. Update the Unified Engine schema and proxy map in architectural docs if necessary.
3. Publish via Doc Guardian and ensure a backup of the previous feature doc is created.

### Scenario: The Global Vault or SQLite Metadata Schema Changes
1. Regenerate affected sections in `docs/features/global_vault_system.md` or `docs/features/agentic_model_meta_scraping.md`.
2. Update operational implications (e.g., hash generation changes) in the architecture overview.
3. Publish and version with Doc Guardian.

### Scenario: Agent Hierarchy Changes
1. Update `docs/agent-guide.md` and related `.agents/skills/` guidelines.
2. Publish and version with Doc Guardian.

## Versioning and Backup Strategy
Use a conservative, traceable versioning process managed by the Doc Guardian:

1. **Preserve previous document versions.**
- Naming pattern: `[filename]-vYYYYMMDD-HHMMSS.md`
- Location: `docs/dochistory/`

2. **Keep canonical active files stable.**
- Main references remain in files directly under `docs/` and `docs/features/`.

3. **History Sweeps.**
- The Doc Guardian periodically runs a sweep to ensure all backup files are neatly organized inside `docs/dochistory/` rather than cluttering active workspaces.

## When to Regenerate Documentation
Regenerate immediately when any of the following occurs:

- Addition of a new core framework component (e.g., OTA Ghost Updater, Studio Analytics).
- Structural changes in Process Sandbox handling or AppStore installation routines.
- Changes to Key Agent boundaries (e.g., Architecture Guardian, QA Guardian).
- Major UI refactors linking to central API endpoints.

For minor edits (typo corrections), targeted block replacements are usually sufficient. For broad refactors or functional additions, regenerate full feature documents.
