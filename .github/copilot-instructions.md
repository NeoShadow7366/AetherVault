# Copilot Workspace Instructions

## Purpose
This repository uses a documentation-first, agent-assisted workflow for understanding and maintaining the AG SM knowledge base.

## Primary Workflow
1. Use read-only analysis agents to investigate architecture, features, and logic.
2. Use Codebase Documenter to generate polished Markdown content.
3. Use Doc Writer to write or version files under docs/.
4. Use History Cleaner periodically to move timestamped backups into docs/dochistory/.

## Agent Hierarchy (Workflow Order)
- Architecture Overviewer -> Feature Investigator / Codebase Analyst -> Codebase Documenter -> Doc Writer -> History Cleaner

## Defaults
- Prefer evidence-based explanations grounded in repository files.
- Prefer existing documentation structure and naming conventions.
- Keep Product Owner-facing language clear and business-friendly.
- Keep generated docs consistent with existing section style and internal links.

## Safety and Scope
- Do not invent behaviors that are not verifiable from code or docs.
- Avoid broad refactors unless explicitly requested.
- For docs/ file writes with versioning, prefer the Doc Writer agent path when available.
