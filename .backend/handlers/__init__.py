"""Handler modules package for AIWebServer domain decomposition.

Each module in this package contains a mixin class with grouped handler methods
that are composed into the main AIWebServer class via multiple inheritance.

This decomposition preserves the single-class HTTP server requirement
(BaseHTTPRequestHandler needs 'self') while separating domains into
manageable files for easier maintenance and reduced cross-feature bugs.

Usage in server.py:
    from handlers.gallery_handlers import GalleryHandlersMixin
    from handlers.vault_handlers import VaultHandlersMixin
    
    class AIWebServer(GalleryHandlersMixin, VaultHandlersMixin, BaseHTTPRequestHandler):
        ...
"""
