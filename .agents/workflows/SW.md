---
description: "Wraps up the current development session by updating session-summary.md with accomplishments, decisions, and next steps."
---

# Session Wrap

This workflow captures the current session's context into `session-summary.md` so that future sessions can pick up seamlessly.

1. Review all files modified during the session (use `git diff --stat` or recent edit history).
2. Review the current `pending_work.md` to identify what was completed and what remains.
3. Update `session-summary.md` at the project root with the following structure:
   - **Session Title** — A short label for the session's focus.
   - **Focus** — One-liner on what the session accomplished.
   - **Main Accomplishments** — Bullet list of completed tasks.
   - **Key Learnings & Decisions** — Architectural decisions, gotchas, or patterns discovered.
   - **Current Overall Project State** — High-level stability summary.
   - **Open Blockers, Questions, or TODOs** — Anything unresolved.
   - **Recommended Starting Point for Next Session** — Exact next step and workflow to invoke.
4. If any `pending_work.md` items were completed, mark them as done or remove them.
5. Confirm the summary with the user before ending.
