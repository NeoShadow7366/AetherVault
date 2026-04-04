# AetherVault Documentation Index

Welcome to the central documentation hub for the **AetherVault** (also known as the Generative AI Manager). This is a comprehensive guide to understanding, developing, and maintaining the cross-platform GenAI orchestrator.

## 🚀 Getting Started

- [Installation & Deployment](deployment-and-setup.md) - How to clone, initialize, and launch the portable Python server.
- [Architecture Overview](architecture.md) - High-level system architecture, technology stack, and orchestrator layers.
- [Team Setup Guide](team-setup-guide.md) - Guidelines for setting up team development environments.

## 📦 Core Features

Detailed breakdowns of the primary systems within the AetherVault:

- [Zero-Friction Inference](features/zero_friction_inference.md) - Multi-engine runtime execution and universal payload translation.
- [App Store & Isolation](features/app_store_isolation.md) - Config-driven application sandbox installation and dependency resolution.
- [Global Vault System](features/global_vault_system.md) - Universal model storage using zero-byte OS-level directory symlinks/junctions.
- [Agentic Model Meta-Scraping](features/agentic_model_meta_scraping.md) - Background pipeline for asset hashing, thumbnail extraction, and embedded metadata lookup via CivitAI and HuggingFace APIs.
- [Studio Analytics & My Creations](features/studio_analytics.md) - Persistent SQLite-backed UI gallery and drag-and-drop workflow canvas restore.
- [Self-Healing OTA Updates](features/ota_ghost_upgrades.md) - Ghost deployment pipeline for patching system updates without data loss.
- [Model Download Pipeline](features/model_downloads.md) - CivitAI/HuggingFace model downloads with progress tracking and auth-header security.
- [Model Import Pipeline](features/model_imports.md) - Drag-and-drop imports with hashing, metadata enrichment, and dependency resolution.

## ⚙️ Configuration & Sub-Systems

- [System Configuration](features/configuration.md) - Details on `settings.json`, networking, API keys, and auto-updating variables.
- [Database Schema Reference](database-schema.md) - Technical definition of the `metadata.sqlite` structure.
- [API Reference Operations](api-reference.md) - Internal JSON proxy payload shapes and system endpoints.
- [Troubleshooting & Runbook](troubleshooting-guide.md) - Diagnostic manual for SQLite locks, ghost processes, and the `/run_health_check` Runtime Doctor.

## 🤖 AI Agent Workflows

Guides on utilizing the built-in AI Guardians and agentic workflows to maintain the project safely:

- [AI Agent Reference Guide](agent-guide.md) - Complete registry of all 15 specialized AI agents, their authority hierarchy, and invocation commands.
- [Documentation Maintenance Guide](maintenance.md) - Procedures for keeping the `docs/` repository clean, updated, and safely backed up via the Doc Guardian.
- [First-Time Full Documentation Workflow](first-time-workflow.md) - How to bootstrap the entire documentation system from scratch.

---
*Documentation automatically generated and maintained by the AetherVault Codebase Documenter and Doc Guardian.*
