# Contributing to AetherVault

Thank you for your interest in contributing to the AetherVault! Because this project orchestrates sensitive user data across fragmented multi-GB GenAI file systems, we have very strict architectural guidelines designed to prevent bloat, dependency hell, and data loss.

## The Prime Directive: "AetherVault" Zero-Dependency Rule
The manager is designed to be completely standalone and friction-less. 
- **NO Node.js / NPM / Build steps.** The frontend must remain a monolithic, natively parsed `index.html` with vanilla JS and CSS.
- **NO External Python HTTP Frameworks.** The backend operates strictly via the Python standard library `http.server.ThreadingHTTPServer`. Do not submit PRs installing FastAPI, Flask, or Django.
- **NO External Database Runtimes.** Everything uses local `sqlite3`.

## The AI Guardian Ecosystem
This repository is co-maintained by humans and specialized AI Agents. If you are developing new features, you must abide by the hierarchy natively established in `agents.md`:

1. **Architecture Guardian (Monolith Sentinel):** Holds veto power over code structure, tool additions, or API drifts. Do not bypass or circumvent the Guardian's ADRs (Architecture Decision Records).
2. **QA Guardian:** Protects runtime stability natively using zero-dependency Python unit frameworks and headless Playwright DOM tests.

If you submit a pull request, the QA Guardian and Architecture Guardian will automatically evaluate your changes for boundary violations and cross-platform regressions.

## Cross-Platform Integrity
Every feature MUST work equally natively on:
- **Windows 10/11** (Use `mklink /J` for NTFS Directory Junctions)
- **macOS** (Intel and Apple Silicon arm64)
- **Linux** (x86_64, aarch64 standard symlinks via `os.symlink`)

## Testing Your Changes Locally
Before pushing commits, run the comprehensive QA array to validate Python unit logic and E2E DOM interaction natively.

```bash
# 1. Install QA-specific tools:
pip install -r requirements-qa.txt
playwright install chromium

# 2. Run the full matrix (backend coverage + frontend E2E):
python -m pytest .tests/ -v --cov=.backend/
```

## Data Safety Constraints
- Never write code that arbitrarily cleans or deletes files inside `Global_Vault/` or `packages/`.
- Ensure SQL queries default safely to transaction blocks to avoid `OperationalError: database is locked` during background `vault_crawler.py` scans.

## Submitting Pull Requests
1. Check the `docs/features/` folder and `api-reference.md`. If your change alters payload shapes or adds a new module, you must update the documentation or invoke the **Doc Guardian** to do so natively.
2. Provide simple, explicit instructions on how to test your feature.
3. Keep the Pull Request tightly scoped. *Do not mix UI formatting refactors into a PR dealing with inference proxies.*

Welcome aboard the project! 🚀
