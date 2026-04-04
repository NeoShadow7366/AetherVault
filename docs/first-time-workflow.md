# First-Time Full Documentation Workflow

## Overview

This guide walks you through bootstrapping the entire AetherVault documentation set from scratch using the AI Agent Ecosystem. It is designed for developers and documentation maintainers who need to generate or regenerate the complete `docs/` tree in a single coordinated session.

The workflow relies on three agent skills, invoked in strict sequence:

| Step | Agent Skill | Responsibility |
|------|------------|----------------|
| 1 | **Codebase Analyst** | Deep read-only investigation of source files, flows, and architecture |
| 2 | **Codebase Documenter** | Structures findings into standardized Markdown documents |
| 3 | **Doc Guardian** | Safely writes files to `docs/`, creating timestamped backups of any existing content |

> [!IMPORTANT]
> The canonical workflow command is `/Generate_Docs`. Invoke it in any AI-assisted conversation to trigger the full Analyst → Documenter → Guardian pipeline.

---

## Scope Gate (Run Before Every Write)

Before generating or updating any documentation file, complete this mandatory pre-flight checklist:

1. **Identify target scope:** Is this a system-wide architectural document or a single feature deep dive?
2. **Confirm scope alignment:** Core documents (`architecture.md`, `index.md`, `api-reference.md`) should never be used for single-feature content. Feature-specific content belongs in `docs/features/`.
3. **Verify backup path:** Confirm the `docs/dochistory/` directory exists and the Doc Guardian's versioning strategy (timestamped `v[YYYYMMDD]-[HHMMSS]` backups) is operational.
4. **Check existing content:** Review the current version of the target file to understand what is already documented and what needs updating.

---

## Phase 1: High-Level Architecture

**Goal:** Produce the foundational system-wide documents that describe the AetherVault as a whole.

### Source Files to Investigate

| File | What the Analyst Extracts |
|------|--------------------------|
| [server.py](../../.backend/server.py) | HTTP router with 45+ API endpoints, CORS handling, `ThreadingHTTPServer` binding, cold-start bootstrap guard, LAN sharing toggle, and graceful teardown sequence |
| [metadata_db.py](../../.backend/metadata_db.py) | SQLite schema (models, gallery, user_tags, prompts tables), CRUD methods, backward-compatible `ALTER TABLE` migrations |
| [agents.md](../../agents.md) | Three-layer agent architecture (Directive → Orchestration → Execution), agent hierarchy, model router, skill discovery, error recovery policies |
| [tray_launcher.py](../../tray_launcher.py) | PyInstaller-bundled system tray application with mutex singleton, auto-bootstrap GUI, graceful process cleanup sweeps |
| [bootstrap.py](../../.backend/bootstrap.py) | First-run directory scaffold (9 Global Vault subdirectories, cache/thumbnails, packages), database initialization |

### Documents Produced

| Target File | Content |
|-------------|---------|
| `docs/architecture.md` | System overview: backend server, monolithic frontend, SQLite persistence, background scanners, process management model |
| `docs/index.md` | Master table of contents linking to all feature docs, operational guides, and governance documents |
| `docs/team-setup-guide.md` | Documentation structure map, role-based navigation guide, development sandbox instructions |

### Analyst Prompt Template

> "Investigate the `server.py`, `metadata_db.py`, `agents.md`, `tray_launcher.py`, and `bootstrap.py` files. Summarize the multi-engine proxy system, SQLite layer, agent architecture, system tray launcher, and cold-start bootstrap sequence for a Product Owner audience."

---

## Phase 2: Feature Documentation

**Goal:** Generate complete, standalone Markdown documents for each of the six major system features.

### Feature Matrix

| Feature | Target File | Primary Source Files |
|---------|------------|---------------------|
| **Zero-Friction Inference** | `docs/features/zero_friction_inference.md` | `proxy_translators.py`, `server.py` (proxy endpoints), `static/index.html` (Inference Studio UI) |
| **App Store & Isolation** | `docs/features/app_store_isolation.md` | `installer_engine.py`, `server.py` (install/launch/uninstall handlers), `.backend/recipes/*.json` |
| **Global Vault System** | `docs/features/global_vault_system.md` | `symlink_manager.py`, `vault_crawler.py`, `bootstrap.py` (vault directory scaffold) |
| **Agentic Model Meta-Scraping** | `docs/features/agentic_model_meta_scraping.md` | `civitai_client.py`, `hf_client.py`, `vault_crawler.py`, `embedding_engine.py` |
| **Studio Analytics** | `docs/features/studio_analytics.md` | `metadata_db.py` (gallery table), `server.py` (gallery endpoints), `static/index.html` (My Creations lightbox) |
| **Self-Healing OTA Updates** | `docs/features/ota_ghost_upgrades.md` | `updater.py`, `update_checker.py`, `server.py` (`/api/system/update` handler) |

### Additional Feature File

| Feature | Target File | Primary Source Files |
|---------|------------|---------------------|
| **System Configuration** | `docs/features/configuration.md` | `.backend/settings.json`, `server.py` (`/api/settings` GET/POST handlers) |

### Document Structure Pattern

Every feature document should follow this consistent layout:

```markdown
## Overview
## Key Features / User Flows
## Architecture & Modules
## Data & Logic Flow
## Configuration Options
## Business Rules & Edge Cases
## Related Files & Functions
## Observations / Notes
```

### Analyst Prompt Template (per feature)

> "Deep dive into the [Feature Name]. Map the complete flow from the frontend UI trigger through the backend API endpoint to the underlying engine/database. List all involved files, functions, data shapes, and edge cases."

---

## Phase 3: Core & Operational Documentation

**Goal:** Generate the technical reference and operational runbooks that support day-to-day usage, debugging, and contributor onboarding.

### Documents Matrix

| Target File | Content Scope | Primary Source Files |
|-------------|--------------|---------------------|
| `docs/deployment-and-setup.md` | Zero-friction install process, portable Python bootstrap, launcher scripts, boot sequence, directory initialization | `install.bat`, `install.sh`, `start_manager.bat`, `start_manager.sh`, `tray_launcher.py`, `bootstrap.py` |
| `docs/api-reference.md` | Full API endpoint catalog with request/response shapes for all 40+ routes | `server.py` (all `do_GET`/`do_POST` handlers), `proxy_translators.py` |
| `docs/database-schema.md` | SQLite table definitions, column types, migration logic, indexing strategy | `metadata_db.py` |
| `docs/troubleshooting-guide.md` | Diagnostic runbook for SQLite locks, zombie processes, broken symlinks, CORS issues, and the Runtime Health Doctor | `server.py` (teardown, pre-flight checks), `vault_crawler.py`, `symlink_manager.py` |
| `CONTRIBUTING.md` | Contributor guidelines, coding standards, zero-dependency policy, Git workflow, QA requirements | `agents.md` (Layer 3 execution rules), `.agent/rules/` |

### Analyst Prompt Template

> "Evaluate the `start_manager` scripts, `.backend/bootstrap.py`, and launcher payloads. Generate a deployment and setup reference covering prerequisites, install steps, launch sequence, and directory initialization for all three platforms (Windows, macOS, Linux)."

---

## Phase 4: Governance & Agent Documentation

**Goal:** Document the AI Agent ecosystem, maintenance procedures, and this workflow itself.

### Documents Matrix

| Target File | Content |
|-------------|---------|
| `docs/agent-guide.md` | Overview of all AI agents, their authority hierarchy, skill locations, invocation commands, and escalation paths |
| `docs/maintenance.md` | Documentation maintenance procedures: backup/versioning via Doc Guardian, cleanup rules, review cadence |
| `docs/first-time-workflow.md` | This file — the meta-guide for bootstrapping the full documentation set |

---

## Phase 5: Polish & Finalize

After all individual documents are generated:

1. **Update `docs/index.md`** to include links to all newly created files, organized under the correct section headings (Getting Started, Core Features, Configuration, Agent Workflows).
2. **Add cross-links** between related documents:
   - Troubleshooting Guide ↔ Architecture Overview (for system context)
   - API Reference ↔ Feature docs (for endpoint-to-feature mapping)
   - Database Schema ↔ Studio Analytics and Meta-Scraping features
3. **Verify internal links** — ensure all relative paths (`features/*.md`, `../CONTRIBUTING.md`) resolve correctly.
4. **Run the Doc Guardian cleanup** — check for any stale `*-vYYYYMMDD-*.md` backup files outside of `docs/dochistory/` and relocate them.

---

## Execution Checklist

Use this checklist to track progress through a full documentation bootstrap session:

```
Phase 1: High-Level Architecture
- [ ] architecture.md
- [ ] index.md (initial scaffold)
- [ ] team-setup-guide.md

Phase 2: Feature Documentation
- [ ] features/zero_friction_inference.md
- [ ] features/app_store_isolation.md
- [ ] features/global_vault_system.md
- [ ] features/agentic_model_meta_scraping.md
- [ ] features/studio_analytics.md
- [ ] features/ota_ghost_upgrades.md
- [ ] features/configuration.md

Phase 3: Core & Operational
- [ ] deployment-and-setup.md
- [ ] api-reference.md
- [ ] database-schema.md
- [ ] troubleshooting-guide.md
- [ ] CONTRIBUTING.md

Phase 4: Governance
- [ ] agent-guide.md
- [ ] maintenance.md
- [ ] first-time-workflow.md

Phase 5: Polish
- [ ] index.md (final update with all links)
- [ ] Cross-links verified
- [ ] Doc Guardian cleanup sweep
```

---

## Troubleshooting

### "Doc Guardian won't create a backup"

Ensure the `docs/dochistory/` directory exists. The Doc Guardian creates it automatically, but filesystem permission issues on shared drives can block `mkdir`. Create it manually if needed:

```bash
mkdir -p docs/dochistory
```

### "Codebase Analyst returns incomplete results"

The Analyst is read-only and relies on file access. If you encounter incomplete analysis:
- Verify the target files exist at the expected paths (`.backend/server.py`, etc.)
- Check that the file is not locked by another process
- For large files like `server.py` (~2200 lines), the Analyst may need multiple passes

### "Generated documentation refers to outdated APIs"

The Analyst reads the current codebase at the time of invocation. If the backend has been modified since the last documentation run, re-invoke `/Generate_Docs` targeting the stale document specifically.

---

## Related Documentation

- [Documentation Index](index.md) — Master table of contents
- [Agent Guide](agent-guide.md) — Full agent hierarchy and invocation commands
- [Maintenance Guide](maintenance.md) — Versioning, backup, and cleanup procedures
- [Architecture Overview](architecture.md) — System design reference
- [Deployment & Setup](deployment-and-setup.md) — Installation and launch procedures
