"""Handler modules package for AIWebServer domain decomposition.

Each module in this package contains a mixin class with grouped handler methods
that are composed into the main AIWebServer class via multiple inheritance.

This decomposition preserves the single-class HTTP server requirement
(BaseHTTPRequestHandler needs 'self') while separating domains into
manageable files for easier maintenance and reduced cross-feature bugs.

Mixins:
    GalleryHandlersMixin   — My Creations gallery CRUD (save, list, delete, rate)
    VaultHandlersMixin     — Vault search, tags, export/import, health, repair
    DownloadHandlersMixin  — Model download/retry/clear, file import/delete
    SystemHandlersMixin    — Settings, server status, logs, updates, dashboard
    ProxyHandlersMixin     — ComfyUI/A1111/Forge/Fooocus engine proxying
    PackageHandlersMixin   — Install/launch/stop/repair, extensions, prompts, Ollama

Usage in server.py:
    from handlers.gallery_handlers import GalleryHandlersMixin
    from handlers.vault_handlers import VaultHandlersMixin
    from handlers.download_handlers import DownloadHandlersMixin
    from handlers.system_handlers import SystemHandlersMixin
    from handlers.proxy_handlers import ProxyHandlersMixin
    from handlers.package_handlers import PackageHandlersMixin

    class AIWebServer(
        GalleryHandlersMixin,
        VaultHandlersMixin,
        DownloadHandlersMixin,
        SystemHandlersMixin,
        ProxyHandlersMixin,
        PackageHandlersMixin,
        BaseHTTPRequestHandler
    ):
        ...
"""
