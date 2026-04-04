# AI Agent Reference Guide

## Overview
This guide documents the full ecosystem of specialized AI skills and agents used throughout the AetherVault project. It covers both the **documentation pipeline agents** (used for generating docs) and the **guardian/infrastructure agents** (used for code quality, architecture, and runtime monitoring).

The complete agent hierarchy and authority chain is defined in the canonical [`agents.md`](../agents.md) file at the project root.

## Documentation Pipeline Agents

These three agents form the `/Generate_Docs` workflow pipeline:

### 1. Codebase Analyst
- **Purpose**: Read-only investigative expert for system architecture, specific features, and detailed code flows. Explains findings in clear business language.
- **When to use**: At the start of a documentation cycle, when you need to understand the big picture or dive deep into a specific feature.
- **Responsibilities**: Provides architecture overviews, feature investigations, and traces logic details.
- **Handoff**: Passes its insights directly to the Codebase Documenter.

### 2. Codebase Documenter
- **Purpose**: Generates full systematic Markdown documentation based on analysis (read-only).
- **When to use**: After the codebase analysis is complete to turn findings into structured documents.
- **Responsibilities**: Transforms codebase analysis into the standard Markdown layout containing:
  - Overview & Key Features
  - Architecture & Modules
  - Data & Logic Flow
  - Configuration Options & Business Rules
- **Handoff**: Hands off the generated syntax and targeted file path to the Doc Guardian.

### 3. Doc Guardian
- **Purpose**: The official agent authorized to create, update, and manage documentation files in `docs/` using safe timestamped backups.
- **When to use**: To safely write the completed documentation outputs to the file system.
- **Behavior**: 
  - Creates a UTC-timestamped backup (e.g., `agent-guide-v20260404-043155.md`) in `docs/dochistory/` before updating any existing documentation file.
  - Keeps the main `docs/` workspace clean with the latest versions.
  - Manages version history and performs directory cleanups when requested.
- **Scope rule**: ONLY operates inside `docs/` and its subfolders.

---

## Full Agent Registry

The AetherVault project uses **15 specialized agent skills** defined in `.agents/skills/`. They operate under a strict authority hierarchy:

### Authority Hierarchy
1. **Human User** — Final and absolute authority.
2. **Architecture Guardian** — Ultimate technical authority on structural matters.
3. **QA Guardian** — Authority over testing and quality. Yields to Architecture Guardian.
4. **Diagnostics (Health Doctor, API Librarian)** — Read-only advisory roles.
5. **Worker Agents** — Pure execution layer with zero authority over rules.

### Complete Skills Table

| # | Skill | Location | Authority | Purpose | Invocation |
|---|-------|----------|-----------|---------|------------|
| 1 | **Universal Inference Router** | `.agents/skills/universal_inference_router/` | Worker | Multi-engine payload translation, proxy dispatch, and batch queue | Automatic on generation requests |
| 2 | **App Store Installer** | `.agents/skills/app_store_installer/` | Worker | Config-driven app installation with isolated venvs | `/api/install` endpoint |
| 3 | **Global Vault Symlinker** | `.agents/skills/global_vault_symlinker/` | Worker | Zero-byte cross-platform directory junctions | Automatic on app launch |
| 4 | **Asset Crawler & Metadata Scraper** | `.agents/skills/asset_crawler_metadata_scraper/` | Worker | Background file indexing, hashing, CivitAI/HF metadata | Background daemon |
| 5 | **Canvas Gallery Restore** | `.agents/skills/canvas_gallery_restore/` | Worker | My Creations gallery with drag-and-drop restore | Gallery UI interactions |
| 6 | **OTA Ghost Updater** | `.agents/skills/ota_ghost_updater/` | Worker | Self-healing code updates without data loss | `/api/system/update` |
| 7 | **Intelligent Model Router** | `.agents/skills/intelligent_model_router/` | Advisory | AI model tier selection for development tasks | `/New_Phase_Start_With_Model_Router` workflow |
| 8 | **Architecture Guardian** | `.agents/skills/architecture_guardian/` | Guardian (L2) | Proactive structural integrity and zero-dependency enforcement | `/analyze_architecture` |
| 9 | **QA Guardian Agent** | `.agents/skills/qa_guardian_agent/` | Guardian (L3) | Automated regression testing on save/commit | `/QA_Guardian_Run_Full_Suite` workflow |
| 10 | **Runtime Health Doctor** | `.agents/skills/runtime_health_doctor/` | Advisory | Read-only runtime infrastructure health monitor | `/run_health_check` |
| 11 | **API Contract Librarian** | `.agents/skills/api_contract_librarian/` | Advisory | JSON payload drift detection between frontend/backend | `/update_api_contracts` |
| 12 | **Ecosystem Health Dashboard** | `.agents/skills/ecosystem_health_dashboard/` | Advisory | Consolidated guardian ecosystem status overview | Via Architecture Guardian |
| 13 | **Safe Test Runner** | `.agents/skills/safe_test_runner/` | Worker | OS-level timeout wrapper for QA test execution | Invoked by QA Guardian |
| 14 | **Codebase Analyst** | `.agents/skills/codebase_analyst/` | Advisory | Read-only investigative expert for code flows | `/Generate_Docs` workflow |
| 15 | **Codebase Documenter** | `.agents/skills/codebase_documenter/` | Advisory | Systematic Markdown documentation generation | `/Generate_Docs` workflow |

---

## Recommended Workflows

### The `/Generate_Docs` Workflow
This is the primary workflow for generating or updating documentation. It automates the `Analysis → Documenter → Guardian` pipeline.

1. **Analyze (Codebase Analyst)**: Call the `/Generate_Docs` workflow. The `codebase_analyst` skill investigates the target feature, component, or overall architecture without making modifications.
2. **Format (Codebase Documenter)**: The `codebase_documenter` skill will automatically structure the insights into the official, comprehensive Markdown layout.
3. **Write & Backup (Doc Guardian)**: The `doc_guardian` skill safely writes the final document to the correct path in `docs/` and performs any necessary versioned backups automatically.

### Quick Single Feature Update
1. Select the specific documentation file you wish to modify.
2. Request a targeted change or addition directly passing the file or feature name to the appropriate workflow.
3. Allow the **Doc Guardian** to perform a versioned overwrite of the specific file once the change is approved or automatically generated.

## Best Practices
- **Use the Guardian System**: Always rely on the **Doc Guardian** to save outputs; do not manually overwrite or attempt to save documentation without using the versioning system.
- **Adhere to Formats**: Ensure all content placed in `docs/` strictly conforms to the standard sections and patterns defined by the **Codebase Documenter**.
- **Keep Documentation Scoped**: Keep documentation structured within the main platform's scope and ensure architectural and feature documentation remains separated logically.
- **Check Before Writing**: Always invoke the **Codebase Analyst** before the **Codebase Documenter** to ensure documentation is grounded in the current codebase state.