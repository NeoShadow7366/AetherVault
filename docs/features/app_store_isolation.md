# App Store & Isolation

## Overview
The App Store & Isolation feature provides a "zero-friction" installation mechanism for the complex AI generative engine ecosystem. It allows users to dynamically install, manage, and uninstall third-party AI backend tools (like ComfyUI and Forge) directly from the AetherVault dashboard. Utilizing config-driven JSON recipes, the system guarantees 100% dependency isolation by wrapping each engine in its own distinct Virtual Environment, effectively eliminating cross-app PyTorch or pip conflicts.

## Key Features / User Flows
- **Config-Driven Installations**: App installations are defined by simple JSON recipes detailing Git repositories, ordered pip command sequences, and target vault routing paths.
- **Zero-Conflict Isolation**: Each application is algorithmically boxed into a fully isolated Python virtual environment (`venv`).
- **Real-Time Progress Tracking**: The installer captures live Git `stderr` streams, extracting percentages and log text to feed UI loaders dynamically during application fetching or extension clones.
- **Automated Directory Wiring**: Automatically builds OS-specific directory junctions or symbolic links pointing to the unified `Global_Vault/`, preventing multi-gigabyte deduplication across different sandboxes.
- **Robust Uninstallation**: Safe atomic folder takedowns remove the isolated package footprint and symlinks, while ensuring user generative models in the global vault remain perfectly unharmed.

## Architecture & Modules
- `installer_engine.py`: The core Python backend logic housing the `RecipeInstaller` and `ExtensionCloneTracker` classes.
- `.backend/recipes/*.json`: The declarative definition layer describing how to install and path the respective generative ecosystems.
- `symlink_manager.py`: A native abstraction module that handles cross-platform directory routing securely (using Windows NTFS junctions or UNIX symlinks).

## Data & Logic Flow
1. **Trigger**: A user selects an engine (e.g. ComfyUI) to install via the dashboard. `RecipeInstaller.install()` is invoked and loads the associated `<app_id>.json` recipe.
2. **Environment Initialization**: The system verifies application paths inside the `packages/[app_id]` scope and identifies if the execution requires a fresh installation.
3. **Repository Fetch**: Performs a headless `git clone` on the target repository into `packages/[app_id]/app`. Raw byte-by-byte status logs are buffered contextually via `ExtensionCloneTracker`.
4. **Virtual Sandbox Creation**: A clean virtual environment (`venv`) is spun up inside `packages/[app_id]/env` relying primarily on the system's portable Python executable bundle if available.
5. **Coupled Proxy Execution**: The installer intercepts all `pip install` deployment commands sourced from the JSON recipe, enforcing strict translation into `venv/python -m pip` calls to bypass user-system namespace collision.
6. **Live Data Injection (Vault)**: Iterates over the `"model_symlinks"` mapping within the recipe, provisioning zero-byte symbolic bridges from `Global_Vault/...` straight into the application's native hierarchy.
7. **Lifecycle Commit**: Issues a final `manifest.json` verifying the installation's successful health state, passing tracking responsibility back to the system dashboard.

## Configuration Options
JSON Recipes (e.g., `comfyui.json`, `forge.json`) follow a strict declarative schema:
- `app_id` (string): Distinct alias for the folder mapping architecture.
- `name` (string): Human-readable UI title.
- `repository` (string): Full git upstream protocol URL.
- `install_commands` (array[string]): Sequential terminal commands (typically pip installations arrayed chronologically).
- `model_symlinks` (dictionary): Key-value pairings indexing a `Global_Vault` category to the package's local relative sub-directory framework.
- `launch_command` (string): The terminal daemon execution script.

## Business Rules & Edge Cases
- **Cross-Platform Native Fallbacks**: The framework autonomously searches for isolated "portable python" paths (such as `bin/python/python.exe`), cascading cleanly back to the OS-configured python if no standalone distributions are accessible.
- **Durable Target Wipes Checkpoint**: Trashing a package footprint utilizing the `RecipeInstaller.uninstall()` function harnesses a rigid `remove_readonly` subroutine. Uninstalls natively break the symbolic link, but preserve the heavyweight underlying Checkpoints mapped in `Global_Vault/`.
- **Interrupt Resistance & Rollbacks**: If a critical fault stops a virgin installation (e.g., network timeout during pip dependency builds), a rollback sequence auto-triggers. The application securely deletes the newly initialized `packages/[app_id]` tree preventing broken fragmented software persistence.
- **Process Decoupling**: Git executions execute heavily encapsulated within a brand new process group (`CREATE_NEW_PROCESS_GROUP`), enabling UI-based user cancellation hooks without disrupting the main backend server context list.

## Related Files & Functions
- `RecipeInstaller.install(recipe_path: str)`: Central orchestrator function tackling git pull logic, environmental compartmentalization, and proxying build scripts.
- `RecipeInstaller.uninstall(package_id: str)`: Excisory logic designed specifically around filesystem takedowns minimizing external drift.
- `ExtensionCloneTracker.clone_with_progress()`: Background asynchronous handler responsible for formatting and serializing git standard error streams toward polling buffers.

## Observations / Notes
- > [!TIP]
  > The automatic rewrite of pip commands (extracting `"pip install"` inputs off recipes and casting them toward execution explicitly via isolated virtual environment executables) represents an incredibly effective fail-safe, eliminating environment leakage risks entirely without mandating complex recipe syntaxes.
- > [!NOTE]
  > Staging installation milestones toward `extension_jobs.json` effectively provisions a stateless persistent layer. When the user rapidly refreshes the interface mid-download, the dashboard seamlessly picks up the identical rendering tick without severing the thread lifecycle.
