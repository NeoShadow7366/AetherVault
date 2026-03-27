# 🌌 Generative AI Manager

> **The ultimate cross-platform orchestrator that eliminates GenAI ecosystem fragmentation.**

Instead of re-downloading Python environments or duplicating 6GB Stable Diffusion models across applications, the Manager acts as a singular hub automating your Runtimes, APIs, Assets, and Workflows seamlessly.

---

## ✨ Features

### 🎨 Zero-Friction Inference
A universal dashboard that drives generations across **ComfyUI**, **SD WebUI Forge**, **Automatic1111**, and **Fooocus** without altering your workflow. Intelligent payload translators automatically map prompts, LoRAs, seeds, and samplers into each engine's native format.

### 📦 Advanced App Store
Install new generative applications instantly via simple `.json` recipe templates. Each app runs in its own isolated Python virtual environment — PyTorch conflicts are structurally impossible.

### 🏦 Global Vault
Drop ANY model once into `Global_Vault/` and use it across every engine forever. Zero-byte NTFS Directory Junctions (Windows) or symbolic links (UNIX) mean no disk duplication.

### 🔍 Agentic Metadata
Ultra-fast background crawlers hash multi-GB safetensors and automatically scrape CivitAI and HuggingFace for model names, descriptions, thumbnails, and version updates. Semantic search powered by sentence-transformers.

### 🖼️ Studio Analytics
Persistent SQLite-backed gallery of all your generations. Drag any thumbnail to instantly restore the exact seed, steps, model, prompt, and configuration back onto the canvas.

### 🔄 Self-Healing Updates
One-click OTA ghost upgrades that patch the dashboard without touching your models, settings, or installed apps.

---

## 🚀 Quick Start

### Windows
```batch
:: First time setup
install.bat

:: Launch the manager
start_manager.bat
```

### macOS / Linux
```bash
# First time setup
chmod +x install.sh && ./install.sh

# Launch the manager
chmod +x start_manager.sh && ./start_manager.sh
```

The dashboard opens automatically at **http://localhost:8080**.

---

## 📁 Project Structure

```
AG SM/
├── agents.md             ← AI agent architecture & coding standards
├── .agents/skills/       ← 6 single-responsibility skill definitions
├── .agent/rules/         ← Security, cross-platform, data safety rules
├── Workflows/            ← Reusable development workflow templates
├── .backend/             ← Python backend server + APIs
│   ├── server.py         ← HTTP server + API router
│   ├── static/index.html ← Monolithic frontend UI
│   ├── recipes/          ← App Store JSON templates
│   └── metadata.sqlite   ← Model database (gitignored)
├── Global_Vault/         ← Universal model storage (gitignored)
├── packages/             ← Installed applications (gitignored)
└── bin/python/           ← Portable Python runtime (gitignored)
```

---

## 🤖 Agent Architecture

This project uses a **three-layer agent architecture** defined in [`agents.md`](agents.md):

1. **Directive Layer** — Project goals, non-negotiable requirements, success metrics
2. **Orchestration Layer** — Chain-of-Thought reasoning, Red-Team review, error recovery
3. **Execution Layer** — Tech stack, coding standards, security rules

Any AI agent modifying this codebase must read and comply with `agents.md` before making changes.

### Skills

Six single-responsibility skills in `.agents/skills/`:

| Skill | Purpose |
|-------|---------|
| **Universal Inference Router** | Multi-engine proxy and payload translation |
| **App Store Installer** | Config-driven app lifecycle management |
| **Global Vault Symlinker** | Cross-platform zero-byte model sharing |
| **Asset Crawler & Metadata Scraper** | Background hashing, metadata, and embeddings |
| **Canvas Gallery Restore** | Persistent generation gallery with parameter restore |
| **OTA Ghost Updater** | Self-healing code updates preserving user data |

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+ stdlib (`http.server.ThreadingHTTPServer`) |
| Database | SQLite3 (stdlib) |
| Frontend | Monolithic HTML/CSS/JS (no build step) |
| Semantic Search | sentence-transformers (all-MiniLM-L6-v2) |
| Portable Python | python-build-standalone by indygreg |
| Symlinks | NTFS Junctions (Windows) / os.symlink (UNIX) |

---

## 📋 Requirements

- **No admin/root access required** (Windows uses junctions, not symlinks)
- **No Node.js/npm** required (pure Python + single HTML file)
- **Git** for App Store cloning and OTA updates
- **Disk space**: ~200MB base + your models

---

## 🛡️ Data Safety

These files are **sacred** and never overwritten by updates:

- `Global_Vault/` — Your model files
- `packages/` — Installed applications
- `.backend/metadata.sqlite` — Model database
- `.backend/settings.json` — Your preferences
- `bin/` — Portable Python

See [`.agent/rules/data_safety.md`](.agent/rules/data_safety.md) for full details.

---

## 📝 License

This project is under active development.

---

*Built with zero external dependencies (Python stdlib only — except sentence-transformers for semantic search).*
