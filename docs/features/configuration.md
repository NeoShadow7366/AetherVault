# System Configuration

## Overview
The AetherVault application employs a unified JSON-based configuration system `settings.json` that persistently stores user preferences, UI theme values, API keys for external services, runtime execution flags, and application usage analytics flags. It is designed to be highly portable and easily accessible across both the Javascript frontend and the Python backend execution environments.

## Key Features / User Flows
- **Theme and UI Customization**: Controls visual aspects such as global theme (`dark`, `glass`) and accent colors.
- **API Key Management**: Secure storage for external integration keys (e.g., CivitAI and HuggingFace).
- **Execution Settings**: Flags for auto-updates and LAN sharing capabilities.
- **Session Intelligence**: Caches state boundaries such as UI activity clearing timestamps to provide a streamlined Dashboard experience.

## Architecture & Modules
- **`settings.json`**: The core configuration artifact located at `.backend/settings.json`. It acts as the ultimate ground truth for persistent user settings.
- **Settings Handlers**: Within `.backend/server.py`, the `handle_get_settings` and `handle_save_settings` proxy API transactions from the frontend.
- **Server Bootstrap Integration**: The configuration is directly interfaced with the main application bootstrap process within `server.py` to enable networking features such as `lan_sharing` port hosting.

## Data & Logic Flow
1. **Frontend Request**: The vanilla JS frontend fetches configuration values asynchronously via a `GET /api/settings` API call upon initialization or when accessing the settings panel.
2. **Backend Processing**: `handle_get_settings` reads `.backend/settings.json`. If missing or corrupt, it automatically falls back to default safety values (`{"theme": "dark", "auto_updates": true}`).
3. **Save Operation**: The user alters a parameter in the interface. A `POST /api/settings` request carrying a partial JSON payload is dispatched. `handle_save_settings` merges the incoming payload with existing configuration via `dict.update()` to prevent dataloss of other unrelated keys, before flushing `json.dump()` synchronously to disk.

## Configuration Options
Key items within the configuration schema:
- `civitai_api_key`: API token for CivitAI model scraping and high-speed downloads.
- `hf_api_key`: Authorization token for HuggingFace model catalog integrations.
- `theme` / `accent`: UI styling variables used to dynamically inject CSS properties.
- `auto_updates`: Boolean parameter that determines if OTA Ghost Upgrades are polled on startup.
- `lan_sharing`: Networking boolean that alters the application bound host from `127.0.0.1` to `0.0.0.0`, rendering the dashboard accessible across the user's Local Area Network.
- `favorites`: Dictionary mapping favorite model parameters (used within UI).
- `activity_cleared_at`: Epoch timestamp tracking the latest cache / dashboard history wipe to exclude visually stale logs.

## Business Rules & Edge Cases
- **Missing File Graceful Recovery**: The application strictly refuses to crash if `settings.json` is corrupted or deleted. The `handle_get_settings` logic defaults safely to a dark mode layout alongside fallback features.
- **Partial Updates Resilience**: By merging partial `POST` payloads via `existing.update(data)` within `handle_save_settings()`, the configuration engine safeguards against overwriting complex JSON objects like `favorites`.
- **LAN Security Scope**: A local LAN interface IP lookup is implemented dynamically via outbound UDP test connection during server initialization if `lan_sharing` is set to true.

## Related Files & Functions
- `.backend/settings.json`: File storage for settings.
- `.backend/server.py`:
  - `handle_get_settings()`
  - `handle_save_settings()`
  - `handle_server_status()`: Applies `activity_cleared_at`.
  - `run_server()`: Checks `lan_sharing` to spin off `ThreadingHTTPServer` to `0.0.0.0`.

## Observations / Notes
- The settings implementation is strictly single-file and relies on atomic JSON writes without locks due to low concurrent write frequency. It fits perfectly within the AetherVault principle of zero external requirements by avoiding unnecessary database schemas for simple key-value configuration.
