---
description: Generates or updates documentation using the Analysis -> Documenter -> Guardian pipeline.
---
# /Generate_Docs Workflow

This workflow guides the AetherVault agent through investigating code, structuring markdown, and safely writing documentation to the `docs/` folder with timestamped backups.

1. **Analyze (Codebase Analyst)**: Use the `codebase_analyst` skill to investigate the target feature, component, or the overall architecture. Do a deep read of the relevant codebase sections without making writes.
2. **Format (Codebase Documenter)**: Invoke the `codebase_documenter` skill. Take the insights from step 1 and structure them into the official Markdown layout (Overview, Features, Architecture, etc.).
3. **Write & Backup (Doc Guardian)**: Invoke the `doc_guardian` skill. Using the Markdown generated in step 2:
   - Check if the target documentation file already exists in `docs/` or `docs/features/`.
   - If it exists, create a timestamped backup in `docs/dochistory/`.
   - Write the fresh markdown to the target file.
4. **Conclusion**: Summarize which files were analyzed, created, updated, and backed up.
