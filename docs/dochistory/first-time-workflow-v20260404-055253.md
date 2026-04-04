# First-Time Full Documentation Workflow

## Overview
This guide walks you through analyzing and bootstrapping the entire documentation set from scratch using the Antigravity Agent Ecosystem.

## Scope Gate (Run Before Every Write)
Mandatory pre-write checks:
1. Identify target scope: system-wide or feature-specific.
2. Confirm core docs are not being used for single-feature deep dives.
3. Confirm timestamped backup/versioning path is in place via the `Doc Guardian`.

## Generating the Documentation

### Phase 1: High-Level Architecture
Investigate the `server.py`, `metadata_db.py`, and `agents.md` files. Ask the Codebase Analyst to summarize the multi-engine proxy system, SQLite layer, and agent architecture for a Product Owner.

### Phase 2: Feature Documentation
Generate complete Markdown content for the following feature files:
- `docs/features/zero_friction_inference.md`
- `docs/features/app_store_isolation.md`
- `docs/features/global_vault_system.md`
- `docs/features/agentic_model_meta_scraping.md`
- `docs/features/studio_analytics.md`
- `docs/features/ota_ghost_upgrades.md`

### Phase 3: Core & Operational Documentation
Use the documenter to evaluate `start_manager` scripts and `.backend` payloads to generate:
- `docs/deployment-and-setup.md`
- `docs/api-reference.md`
- `docs/database-schema.md`
- `docs/troubleshooting-guide.md`
- `CONTRIBUTING.md`

### Phase 4: Polish & Finalize
Update `docs/index.md` to map to all newly created endpoints. Add appropriate cross-links between the Troubleshooting Guide and the Architecture breakdown.
