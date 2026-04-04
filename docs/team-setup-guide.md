# AetherVault - Team Setup Guide

## 1. Introduction
This documentation set is the shared operating guide for the **AetherVault**, a zero-dependency Python/SQLite desktop and web platform orchestrating GenAI engines (ComfyUI, Forge, Fooocus), isolated app sandboxes, the Global Vault filesystem, and semantic background hashing.

The team built and maintains this set using specialized AI agents so documentation can stay aligned to the real codebase while remaining readable for contributors, end-users, and infrastructure managers.

## 2. Documentation Structure
High-level view of the docs folder:
- Entry point and navigation: [index.md](index.md)
- Architecture and system design: [architecture.md](architecture.md)
- Environment and setup: [deployment-and-setup.md](deployment-and-setup.md)
- Core endpoints & DB schema: [api-reference.md](api-reference.md) and [database-schema.md](database-schema.md)
- Operations and reliability: [troubleshooting-guide.md](troubleshooting-guide.md)
- Feature-level details: `docs/features/`
- Agent usage and update process: [agent-guide.md](agent-guide.md), [maintenance.md](maintenance.md), [first-time-workflow.md](first-time-workflow.md)
- Root contributor guidelines: [../CONTRIBUTING.md](../CONTRIBUTING.md)

Quick navigation guide:
- Start here for all roles: [index.md](index.md)
- Product Owners/UI Devs: [architecture.md](architecture.md), then feature files in `features/`
- Backend Developers: [database-schema.md](database-schema.md), [api-reference.md](api-reference.md)
- Operations and support: [deployment-and-setup.md](deployment-and-setup.md), [troubleshooting-guide.md](troubleshooting-guide.md)

Simple section diagram:

```text
Documentation Set
|
+-- Core
|   +-- index
|   +-- architecture
|   +-- api-reference
|   +-- database-schema
|
+-- Features
|   +-- zero_friction_inference
|   +-- app_store_isolation
|   +-- global_vault_system
|   +-- agentic_model_meta_scraping
|   +-- studio_analytics
|   +-- ota_ghost_upgrades
|
+-- Operations
|   +-- deployment-and-setup
|   +-- troubleshooting-guide
|
+-- Governance
    +-- agent-guide
    +-- first-time-workflow
    +-- maintenance
```

## 3. The AI Agent Team
This project relies heavily on autonomous agents (like the Architecture Guardian, QA Guardian, and Doc Guardian). See the [agent-guide.md](agent-guide.md) for full execution boundaries.

## 4. Development Sandbox
When launching a dev server, run `start_manager.bat/sh`. Any edits made directly to `server.py` or `index.html` require no compilation. The Architecture Guardian strictly prohibits introducing build steps (NPM, Webpack) to keep the project friction-less.
