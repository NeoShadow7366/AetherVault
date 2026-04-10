# 🌌 Generative AI Manager — agents.md

> **The ultimate cross-platform orchestrator that eliminates GenAI ecosystem fragmentation.**

This file defines the canonical three-layer agent architecture for all AI-assisted development on this project. Any agent (human or automated) modifying this codebase **MUST** read and comply with this document before making changes.

For detailed instructions on any skill, read the corresponding `SKILL.md` in `.agents/skills/<skill_name>/`.
For rules and policies, read the corresponding `.md` in `.agents/rules/`.

---

## Layer 1 — Directive Layer

### Project Mission

Generative AI Manager is a singular hub that automates Runtimes, APIs, Assets, and Workflows for the fragmented GenAI ecosystem. Instead of re-downloading Python environments or duplicating 6GB Stable Diffusion models across applications, the Manager provides:

1. **Zero-Friction Inference** — Universal dashboard driving ComfyUI, Forge, Automatic1111, and Fooocus.
2. **Advanced App Store** — Config-driven `.json` recipes with isolated virtual environments.
3. **Global Vault** — Drop ANY model once, use everywhere via zero-byte directory junctions/symlinks.
4. **Agentic Metadata** — Ultra-fast crawlers with CivitAI/HuggingFace metadata and semantic search.
5. **Studio Analytics** — SQLite-backed gallery with drag-and-drop canvas restore.
6. **Self-Healing Architecture** — OTA ghost upgrades that patch the dashboard without touching user data.

### Non-Negotiable Requirements

| # | Requirement | Rationale |
|---|-------------|-----------|
| 1 | **Zero user data loss** | Global_Vault, packages/, cache/thumbnails, metadata.sqlite, and settings.json are sacred. No operation may delete, corrupt, or overwrite them without explicit user consent. |
| 2 | **Cross-platform parity** | Every feature MUST work on Windows 10/11, macOS (Intel + Apple Silicon), and Linux (x86_64 + arm64). See `.agents/rules/cross_platform.md` for implementation patterns. |
| 3 | **Isolated environments** | Each installed app gets its own `.venv`. PyTorch version conflicts are structurally impossible. |
| 4 | **No admin/root required** | Windows uses NTFS Directory Junctions (`mklink /J`). UNIX uses `os.symlink()`. |
| 5 | **Portable Python** | Ships with `python-build-standalone` binaries. System Python is a fallback, never a requirement. |
| 6 | **Offline-first** | Dashboard boots instantly from local SQLite. Network calls are background-only and failure-tolerant. |
| 7 | **Single-file frontend** | Monolithic `index.html` served by Python HTTP server. No Node.js, no npm, no bundler. |
| 8 | **Subprocess safety** | All spawned processes use `CREATE_NEW_PROCESS_GROUP` on Windows. PIDs are tracked. Orphan detection mandatory. |
| 9 | **Never Un-track Developer Architecture** | `.tests/`, `.github/`, `.agents/` remain Git-tracked. Exclude in `build.py` instead of `.gitignore`. |

### Success Metrics

- **< 2s** cold-start to dashboard render
- **0 duplicate model bytes** across engines
- **100%** CivitAI metadata resolution per scan cycle
- **Zero** cross-app PyTorch conflicts
- **< 500ms** inference proxy round-trip on localhost

---

## Layer 2 — Orchestration Layer

### Agent Hierarchy (Chain of Command)

1. **Human User** – Final authority. Approves rule overrides, architectural changes, ADRs.
2. **Architecture Guardian** – Technical authority on structure. Veto on code structure, dependencies, system boundaries. → See [SKILL.md](file:///g:/AG%20SM/.agents/skills/architecture_guardian/SKILL.md)
3. **QA Guardian** – Authority over testing and correctness. Yields to Architecture Guardian on structural matters. → See [SKILL.md](file:///g:/AG%20SM/.agents/skills/qa_guardian_agent/SKILL.md)
4. **Diagnostics (Health Doctor & API Librarian)** – Read-only advisory. Escalate upward. → See respective SKILL.md files.
5. **Worker Agents / Skills** – Pure execution layer. Zero authority to create or modify rules.

#### Conflict Resolution

| Conflict Type | Deciding Authority | Escalation |
|:---|:---|:---|
| Dependency, Structure, Tools | Architecture Guardian | → Human User |
| Testing, Correctness | QA Guardian | → Architecture Guardian → Human |
| Telemetry / Diagnostics | Advisory only | → Relevant Guardian |
| New Rule or Memory Update | Human User only | N/A |

### Reasoning Pipeline

Every code change follows:
```
1. UNDERSTAND  → Read the relevant SKILL.md + existing code
2. PLAN        → Outline the change (what, why, where)
3. RED-TEAM    → "What breaks? What edge case? What data corruption risk?"
4. IMPLEMENT   → Write the code
5. VERIFY      → Run or describe verification
6. DOCUMENT    → Update skills or comments if behavior changed
```

### Model Selection

> Invoke the [Intelligent Model Router](file:///g:/AG%20SM/.agents/skills/intelligent_model_router/SKILL.md) at phase starts, task-type changes, or when complex reasoning is required. Follow the [model switch confirmation rule](file:///g:/AG%20SM/.agents/rules/model_switch_confirmation.md).

### Self-Correction Checklist

Before committing any file change:
- [ ] Respects Non-Negotiable Requirements?
- [ ] Works on Windows AND UNIX? (Check every `os.path`, `subprocess`, `symlink` call)
- [ ] Could corrupt `metadata.sqlite`? (Raw SQL without transactions?)
- [ ] Leaks file handles or subprocess PIDs?
- [ ] Race condition with background scanners?

### Error Recovery

> See `.agents/rules/data_safety.md` for database safety patterns and `.agents/rules/security.md` for subprocess/injection prevention.

**Terminal failures:** Capture stderr + return code. Retry retryable errors (network, file lock) with exponential backoff ×3. Surface non-retryable errors to UI — never swallow silently.

**Subprocess crashes:** Pre-flight check manifest.json + symlinks. On `URLError`, poll process, read `runtime.log` tail, search for `ModuleNotFoundError`. Return structured error to frontend with repair button.

**Database failures:** "database is locked" → retry 500ms × 5. "disk I/O error" → surface critical alert, never auto-repair. Schema mismatch → `ALTER TABLE` with `try/except`.

### Parallelism Constraints

| Task Type | Parallel? | Constraint |
|-----------|----------|------------|
| File hashing | ✅ ThreadPoolExecutor(4) | No concurrent hash + metadata write on same file |
| CivitAI API | ❌ | 1 req/sec rate limit |
| HuggingFace API | ✅ up to 3 | Respect rate limits |
| Package installs | ❌ | One at a time — pip lock conflicts |
| Symlink creation | ❌ | Sequential — directory race conditions |
| Embedding | ✅ single worker | SentenceTransformer not thread-safe |
| Batch generation | ❌ | Sequential via `_batch_worker` |

### Skill Discovery

Check `.agents/skills/` for a matching SKILL.md → read its `description` → follow input/output contract.

| Skill | Purpose |
|-------|---------|
| [Universal Inference Router](file:///g:/AG%20SM/.agents/skills/universal_inference_router/SKILL.md) | Multi-engine payload translation, proxy dispatch, batch queue |
| [App Store Installer](file:///g:/AG%20SM/.agents/skills/app_store_installer/SKILL.md) | Config-driven installation with isolated venvs |
| [Global Vault Symlinker](file:///g:/AG%20SM/.agents/skills/global_vault_symlinker/SKILL.md) | Zero-byte cross-platform directory junctions |
| [Asset Crawler & Metadata Scraper](file:///g:/AG%20SM/.agents/skills/asset_crawler_metadata_scraper/SKILL.md) | Background indexing, hashing, CivitAI/HF metadata |
| [Canvas Gallery Restore](file:///g:/AG%20SM/.agents/skills/canvas_gallery_restore/SKILL.md) | My Creations gallery with drag-and-drop restore |
| [OTA Ghost Updater](file:///g:/AG%20SM/.agents/skills/ota_ghost_updater/SKILL.md) | Self-healing code updates without data loss |
| [Intelligent Model Router](file:///g:/AG%20SM/.agents/skills/intelligent_model_router/SKILL.md) | AI model tier selection for development tasks |
| [QA Guardian Agent](file:///g:/AG%20SM/.agents/skills/qa_guardian_agent/SKILL.md) | Automated regression testing on save/commit |
| [Architecture Guardian](file:///g:/AG%20SM/.agents/skills/architecture_guardian/SKILL.md) | Proactive architectural integrity and zero-dependency enforcement |
| [Runtime Health Doctor](file:///g:/AG%20SM/.agents/skills/runtime_health_doctor/SKILL.md) | Read-only runtime infrastructure health monitor |
| [API Contract Librarian](file:///g:/AG%20SM/.agents/skills/api_contract_librarian/SKILL.md) | JSON payload drift prevention between frontend/backend |
| [Ecosystem Health Dashboard](file:///g:/AG%20SM/.agents/skills/ecosystem_health_dashboard/SKILL.md) | Consolidated guardian ecosystem status overview |
| [Safe Test Runner](file:///g:/AG%20SM/.agents/skills/safe_test_runner/SKILL.md) | OS-level timeout wrapper for QA tests |
| [Codebase Analyst](file:///g:/AG%20SM/.agents/skills/codebase_analyst/SKILL.md) | Read-only investigative expert for architecture and code flows |
| [Codebase Documenter](file:///g:/AG%20SM/.agents/skills/codebase_documenter/SKILL.md) | Generates structured Markdown documentation |
| [Doc Guardian](file:///g:/AG%20SM/.agents/skills/doc_guardian/SKILL.md) | Manages documentation files with timestamped backups |

### Rules & Policies

| Rule | Purpose |
|------|---------|
| [security.md](file:///g:/AG%20SM/.agents/rules/security.md) | Path traversal, subprocess injection, API keys, SQL injection |
| [cross_platform.md](file:///g:/AG%20SM/.agents/rules/cross_platform.md) | Windows/macOS/Linux parity patterns |
| [data_safety.md](file:///g:/AG%20SM/.agents/rules/data_safety.md) | Sacred files, DB safety, OTA protection |
| [qa_guardian.md](file:///g:/AG%20SM/.agents/rules/qa_guardian.md) | Test isolation, flakiness, Playwright stability |
| [model_switch_confirmation.md](file:///g:/AG%20SM/.agents/rules/model_switch_confirmation.md) | Pause-and-confirm workflow for model switches |
| [learning_and_memory.md](file:///g:/AG%20SM/.agents/rules/learning_and_memory.md) | Prevents autonomous rule modification |

---

## Layer 3 — Execution Layer

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend** | Python 3.11+ stdlib `http.server.ThreadingHTTPServer` | Zero dependencies, portable |
| **Database** | SQLite3 (stdlib) | Single-file, zero-config, crash-safe |
| **Frontend** | Monolithic HTML/CSS/JS (`index.html`) | No build step, instant reload |
| **Hashing** | `hashlib.sha256` (stdlib) | CivitAI SHA-256 identification |
| **HTTP Client** | `urllib.request` (stdlib) | Zero-dependency REST calls |
| **Semantic Search** | `sentence-transformers` (all-MiniLM-L6-v2) | ~80MB, CPU-only, 384-dim |
| **Process Mgmt** | `subprocess.Popen` + PID tracking | Full lifecycle control |
| **Symlinks** | `mklink /J` (Win) / `os.symlink` (UNIX) | Zero-byte, no admin |
| **Portable Python** | `python-build-standalone` | Self-contained CPython |

### Folder Structure

```
AG SM/                              ← Project Root
├── agents.md                       ← THIS FILE — agent routing document
├── .agents/                        ← Agent ecosystem
│   ├── skills/                     ← One SKILL.md per capability (16 skills)
│   ├── rules/                      ← Policy documents (6 rules)
│   ├── workflows/                  ← Reusable multi-step procedures
│   ├── contracts/                  ← API payload contracts
│   ├── architectural_decisions/    ← ADRs
│   └── visualizations/             ← Mermaid diagrams
│
├── .backend/                       ← Python backend
│   ├── server.py                   ← HTTP server + API router (~2300 lines, 70 endpoints)
│   ├── proxy_translators.py        ← ComfyUI/SDAPI payload translation
│   ├── metadata_db.py              ← SQLite ORM layer
│   ├── vault_crawler.py            ← Background file indexer
│   ├── civitai_client.py           ← CivitAI API metadata scraper
│   ├── hf_client.py                ← HuggingFace Hub search
│   ├── installer_engine.py         ← App installer (clone + venv + pip + symlinks)
│   ├── symlink_manager.py          ← Cross-platform junction/symlink creation
│   ├── embedding_engine.py         ← Semantic search vectors
│   ├── updater.py                  ← OTA ghost upgrade daemon
│   ├── static/index.html           ← Monolithic frontend
│   └── recipes/*.json              ← App Store templates
│
├── Global_Vault/                   ← Universal model storage (gitignored)
├── packages/                       ← Installed applications (gitignored)
├── bin/python/                     ← Portable Python (gitignored)
└── .tests/                         ← QA test suite
```

### Coding Standards

#### Python (.backend/)
- Type hints on all public functions
- Docstrings on classes and non-trivial functions
- `logging` over `print()` — module-level logger
- Exception handling with context — never bare `except: pass`
- Cross-platform branching via `os.name` / `platform.system()`
- No hard-coded absolute paths

#### JavaScript (static/index.html)
- Unique IDs on all interactive elements
- Error handling on all `fetch()` calls
- Template literals for dynamic HTML
- Explicit route mapping — never blindly interpolate `${engine}_proxy`

#### Security (Quick Reference)
> Full details in `.agents/rules/security.md`

| Rule | Pattern |
|------|---------|
| Path traversal | `if ".." in path: send_error(403)` |
| API error format | Always `send_json_response({"error": ...})`, never raw `send_error(404)` on `/api/` |
| Symlink validation | `os.path.abspath()` both source and target |
| Subprocess safety | List-form `subprocess.run([...])`, never `shell=True` with user input |
| DB queries | Parameterized `cursor.execute('...?', (param,))` always |
| API keys | Never in logs, error responses, or Git |
| HTTP redirects | Strip `Authorization` headers on redirect |
