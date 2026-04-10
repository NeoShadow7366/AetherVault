import os
import sys
import json
import logging
import subprocess
import signal
import time
import uuid
import threading
import datetime
import shutil
import urllib.request
import urllib.parse
import urllib.error
import math
import base64
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ── Centralized sys.path setup (done once, not per-request) ──────
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Import backend modules once at module level
from metadata_db import MetadataDB
from symlink_manager import create_safe_directory_link
from proxy_translators import build_comfy_workflow, build_a1111_payload, build_fooocus_payload

# ── Server State Globals ─────────────────────────────────────────
global_http_server = None
embedding_process = None

# ── Thread Safety: Settings file lock ────────────────────────────
_settings_lock = threading.Lock()

# ── Cached MetadataDB singleton (avoid re-running DDL per request)
_db_instance = None
_db_lock = threading.Lock()

def _get_db() -> MetadataDB:
    """Returns a cached MetadataDB instance. Schema init runs once.
    Re-creates if AIWebServer.root_dir has been changed (e.g., by tests)."""
    global _db_instance
    # Use AIWebServer.root_dir so tests can override the data root
    server_cls = globals().get('AIWebServer')
    current_root = getattr(server_cls, 'root_dir', _ROOT_DIR) if server_cls else _ROOT_DIR
    db_path = os.path.join(current_root, ".backend", "metadata.sqlite")
    if _db_instance is None or _db_instance.db_path != db_path:
        with _db_lock:
            if _db_instance is None or _db_instance.db_path != db_path:
                _db_instance = MetadataDB(db_path)
    return _db_instance

# ── Cached Settings (avoid re-reading 627KB JSON per request) ────
_settings_cache = {"data": None, "mtime": 0}

def _get_settings() -> dict:
    """Returns cached settings.json, re-reads only if file changed."""
    settings_path = os.path.join(_ROOT_DIR, ".backend", "settings.json")
    try:
        current_mtime = os.path.getmtime(settings_path) if os.path.exists(settings_path) else 0
    except OSError:
        current_mtime = 0
    if _settings_cache["data"] is not None and current_mtime == _settings_cache["mtime"]:
        return dict(_settings_cache["data"])  # Return copy to prevent mutation
    with _settings_lock:
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"theme": "dark", "civitai_api_key": "", "auto_updates": True}
            _settings_cache["data"] = data
            _settings_cache["mtime"] = current_mtime
            return dict(data)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to read settings.json: {e}")
            if _settings_cache["data"] is not None:
                return dict(_settings_cache["data"])
            return {"theme": "dark", "civitai_api_key": "", "auto_updates": True}

def _save_settings(data: dict) -> None:
    """Thread-safe settings save with merge semantics."""
    settings_path = os.path.join(_ROOT_DIR, ".backend", "settings.json")
    with _settings_lock:
        existing = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = {}
        existing.update(data)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=4)
        # Invalidate cache
        _settings_cache["data"] = existing
        try:
            _settings_cache["mtime"] = os.path.getmtime(settings_path)
        except OSError:
            _settings_cache["mtime"] = 0

# ── CivitAI MeiliSearch Public API Key ───────────────────────────
# This is CivitAI's public search key embedded in their web frontend.
# Override via settings.json "civitai_search_key" if rotated.
_CIVITAI_SEARCH_KEY = "8c46eb2508e21db1e9828a97968d91ab1ca1caa5f70a00e88a2ba1e286603b61"

def graceful_teardown():
    """Fixed: synchronous, kills sandboxes properly, no NameError"""
    print("\n[TEARDOWN] graceful_teardown() WAS CALLED")
    sys.stdout.flush()
    print("[TEARDOWN] Starting shutdown sequence...")
    sys.stdout.flush()

    # 1. Shutdown HTTP server (unblocks serve_forever on main thread)
    global global_http_server
    if global_http_server:
        print("[TEARDOWN] Shutting down HTTP server...")
        sys.stdout.flush()
        try:
            global_http_server.shutdown()
        except Exception as e:
            print(f"[TEARDOWN] HTTP shutdown warning: {e}")
            sys.stdout.flush()

    # 2. Kill ALL sandbox processes (ComfyUI, etc.)
    print("[TEARDOWN] Terminating sandbox engines...")
    sys.stdout.flush()
    try:
        for package_id, entry in list(AIWebServer.running_processes.items()):
            proc = entry.get("process") if isinstance(entry, dict) else entry
            if proc and proc.poll() is None:
                print(f"[TEARDOWN] Killing sandbox '{package_id}' (PID {proc.pid})")
                sys.stdout.flush()
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                    creationflags=0x08000000)
                else:
                    proc.kill()
    except Exception as e:
        print(f"[TEARDOWN] Sandbox cleanup warning: {e}")
        sys.stdout.flush()

    # 3. Kill tracked embedding engine
    global embedding_process
    if embedding_process and embedding_process.poll() is None:
        print(f"[TEARDOWN] Killing embedding engine (PID {embedding_process.pid})")
        sys.stdout.flush()
        try:
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(embedding_process.pid)],
                                creationflags=0x08000000)
            else:
                embedding_process.kill()
        except Exception as e:
            print(f"[TEARDOWN] Embedding kill warning: {e}")

    # 4. Safety wmic sweep for any orphaned embedding processes
    print("[TEARDOWN] Running safety sweep for orphaned embedding processes...")
    sys.stdout.flush()
    try:
        if os.name == 'nt':
            output = subprocess.check_output(
                r'wmic process where "name=\'python.exe\' and commandline like \'%embedding_engine.py%\'" get processid',
                shell=True,
                creationflags=0x08000000
            ).decode('utf-8', errors='ignore')
            for line in output.splitlines():
                pid = line.strip()
                if pid.isdigit() and pid != "ProcessId":
                    print(f"[TEARDOWN] Killing orphaned embedding PID {pid}")
                    sys.stdout.flush()
                    subprocess.call(['taskkill', '/F', '/T', '/PID', pid],
                                    creationflags=0x08000000)
        else:
            subprocess.call(['pkill', '-f', 'embedding_engine.py'])
    except Exception as e:
        print(f"[TEARDOWN] Fallback sweep warning: {e}")

    print("[TEARDOWN] Shutdown complete. Exiting.")
    sys.stdout.flush()
    time.sleep(0.5)
    os._exit(0)

# ── Sprint 9: Vault Size Cache (updated by background scanner) ───
_vault_size_cache = {"size": 0, "expires": 0}

# ── Sprint 9: In-Memory Batch Generation Queue ──────────────────
_batch_queue = []  # list of {id, status, payload, result, error}
_batch_lock = threading.Lock()
_batch_worker_running = False
_BATCH_MAX_HISTORY = 50  # Purge completed jobs beyond this limit

# ── Phase 5: Civitai Search Cache (max 50 entries) ───────────
_civitai_search_cache = {}  # dict of { cache_key: { "timestamp": float, "data": list } }
_CIVITAI_CACHE_MAX = 50

# ── Dashboard Stats Cache (30s TTL) ──────────────────────────────
_server_stats_cache = {"data": None, "expires": 0}
_SERVER_STATS_TTL = 30

# ── Engine Proxy Configuration ───────────────────────────────────
_ENGINE_CONFIG = {
    "comfyui": {"port": 8188, "translator": build_comfy_workflow, "gen_endpoint": "/prompt"},
    "a1111":   {"port": 7861, "translator": build_a1111_payload, "gen_endpoint": "/sdapi/v1/txt2img"},
    "forge":   {"port": 7860, "translator": build_a1111_payload, "gen_endpoint": "/sdapi/v1/txt2img"},
    "fooocus": {"port": 8888, "translator": build_fooocus_payload, "gen_endpoint": "/v1/generation/text-to-image"},
}

class AIWebServer(BaseHTTPRequestHandler):
    root_dir = _ROOT_DIR
    db_path = os.path.join(_ROOT_DIR, ".backend", "metadata.sqlite")
    static_dir = os.path.join(_ROOT_DIR, ".backend", "static")
    running_processes = {}  # PID tracking for launched packages
    running_installs = {}   # PID tracking for active installer processes

    # ── Shared Process Kill Helper ───────────────────────────────
    @classmethod
    def _kill_tracked_process(cls, package_id: str, remove_from_dict: bool = True) -> bool:
        """Kill a tracked sandbox process. Returns True if a process was killed."""
        entry = cls.running_processes.get(package_id)
        if not entry:
            return False
        proc = entry.get("process") if isinstance(entry, dict) else entry
        log_file = entry.get("log_file") if isinstance(entry, dict) else None
        killed = False
        if proc and proc.poll() is None:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                   check=False, capture_output=True)
                else:
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                killed = True
            except Exception as e:
                logging.error(f"Error killing {package_id}: {e}")
        if log_file:
            try:
                log_file.close()
            except Exception:
                pass
        if remove_from_dict and package_id in cls.running_processes:
            del cls.running_processes[package_id]
        return killed

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


    # ── Route Registry (O(1) dict lookup replaces O(n) if/elif chains) ──
    _GET_ROUTES = {
        "/api/models":              "send_api_models",
        "/api/packages":            "send_api_packages",
        "/api/recipes":             "send_api_recipes",
        "/api/install/status":      "handle_install_status",
        "/api/downloads":           "handle_get_downloads",
        "/api/comfy_image":         "handle_comfy_image",
        "/api/import/status":       "handle_import_status",
        "/api/import/jobs":         "handle_import_jobs",
        "/api/gallery":             "handle_gallery_list",
        "/api/vault/search":        "handle_vault_search",
        "/api/vault/tags":          "handle_get_all_tags",
        "/api/hf/search":           "handle_hf_search",
        "/api/extensions":          "handle_get_extensions",
        "/api/extensions/status":   "handle_extension_status",
        "/api/settings":            "handle_get_settings",
        "/api/server_status":       "handle_server_status",
        "/api/logs":                "handle_get_logs",
        "/api/prompts":             "handle_list_prompts",
        "/api/generate/queue":      "handle_batch_queue_status",
        "/api/gallery/tags":        "handle_gallery_tags",
        "/api/civitai_search":      "handle_civitai_search",
        "/api/ollama/status":       "handle_ollama_status",
        "/api/favorites":           "handle_get_favorites",
    }

    _POST_ROUTES = {
        "/api/install":             "handle_install",
        "/api/launch":              "handle_launch",
        "/api/repair_dependency":   "handle_repair_dependency",
        "/api/repair":              "handle_repair_install",
        "/api/stop":                "handle_stop",
        "/api/restart":             "handle_restart",
        "/api/comfy_upload":        ("handle_comfy_upload", False),  # (method, needs_data)
        "/api/uninstall":           "handle_uninstall",
        "/api/download":            "handle_download",
        "/api/download/retry":      "handle_retry_download",
        "/api/downloads/clear":     ("handle_clear_downloads", False),
        "/api/delete_model":        "handle_delete_model",
        "/api/open_folder":         "handle_open_folder",
        "/api/import":              "handle_import_file",
        "/api/gallery/save":        "handle_gallery_save",
        "/api/gallery/delete":      "handle_gallery_delete",
        "/api/gallery/rate":        "handle_gallery_rate",
        "/api/vault/tag/add":       "handle_add_tag",
        "/api/vault/tag/remove":    "handle_remove_tag",
        "/api/recipes/build":       "handle_build_recipe",
        "/api/extensions/install":  "handle_install_extension",
        "/api/extensions/remove":   "handle_remove_extension",
        "/api/extensions/cancel":   "handle_cancel_extension",
        "/api/vault/export":        "handle_vault_export",
        "/api/vault/import":        "handle_vault_import",
        "/api/vault/updates":       "handle_vault_updates",
        "/api/vault/repair":        "handle_vault_repair",
        "/api/vault/health_check":  "handle_vault_health_check",
        "/api/vault/import_scan":   "handle_import_scan",
        "/api/vault/bulk_delete":   "handle_vault_bulk_delete",
        "/api/generate/batch":      "handle_batch_generate",
        "/api/prompts/save":        "handle_save_prompt",
        "/api/prompts/delete":      "handle_delete_prompt",
        "/api/settings":            "handle_save_settings",
        "/api/dashboard/clear_history": "handle_clear_dashboard_history",
        "/api/import/external":     "handle_import_external",
        "/api/system/update":       "handle_system_update",
        "/api/comfy_proxy":         "handle_comfy_proxy",
        "/api/a1111_proxy":         "handle_a1111_proxy",
        "/api/forge_proxy":         "handle_forge_proxy",
        "/api/fooocus_proxy":       "handle_fooocus_proxy",
        "/api/ollama/enhance":      "handle_ollama_enhance",
        "/api/favorites/add":       "handle_add_favorite",
        "/api/favorites/remove":    "handle_remove_favorite",
    }

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        handler_name = self._GET_ROUTES.get(path)
        if handler_name:
            getattr(self, handler_name)()
        else:
            self.serve_static_files(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # /api/shutdown is special: sends response before teardown
        if path == "/api/shutdown":
            print("[SERVER] === /api/shutdown ENDPOINT WAS HIT ===")
            sys.stdout.flush()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "shutting down gracefully"}).encode('utf-8'))
            self.wfile.flush()
            sys.stdout.flush()

            print("[SERVER] Response sent. Running graceful_teardown() SYNCHRONOUSLY (no daemon thread)...")
            sys.stdout.flush()

            # Critical fix: run directly on this thread
            graceful_teardown()
            return
        
        route = self._POST_ROUTES.get(path)
        if not route:
            self.send_json_response({"error": f"Endpoint {path} not found"}, 404)
            return
        
        # Routes can be either "method_name" (receives data) or ("method_name", False) (no data arg)
        if isinstance(route, tuple):
            handler_name, needs_data = route
            getattr(self, handler_name)()
        else:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            
            try:
                data = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logging.warning(f"Failed to parse POST body as JSON: {e}")
                data = {}
            
            getattr(self, route)(data)

    def serve_static_files(self, path):
        # Decode and normalize path separators for Windows
        path = urllib.parse.unquote(path).replace('\\', '/')
        
        # Default to index.html
        if path == "/":
            path = "/index.html"
            
        # Security: Prevent directory traversal
        if ".." in path:
            self.send_error(403, "Forbidden")
            return
            
        # Serve root UI logo (redirect legacy path to icons/)
        if path == "/Logo.ico":
            filepath = os.path.join(self.root_dir, "icons", "Logo.ico")
        # Serve custom user icons
        elif path.startswith("/icons/"):
            clean_path = urllib.parse.unquote(path.lstrip("/"))
            filepath = os.path.join(self.root_dir, clean_path)
        # Check if they are requesting a thumbnail
        elif path.startswith("/.backend/cache/thumbnails/"):
            filepath = os.path.join(self.root_dir, path.lstrip("/"))
        else:
            filepath = os.path.join(self.static_dir, path.lstrip("/"))
            
        if not os.path.exists(filepath):
            if path.startswith("/api/"):
                self.send_json_response({"error": "Endpoint not found"}, 404)
            else:
                self.send_error(404, "File Not Found")
            return
            
        # Basic MIME types mapping
        ext = filepath.split(".")[-1].lower()
        content_type = "text/plain"
        if ext == "html": content_type = "text/html"
        elif ext == "css": content_type = "text/css"
        elif ext == "js": content_type = "application/javascript"
        elif ext in ["jpg", "jpeg"]: content_type = "image/jpeg"
        elif ext == "png": content_type = "image/png"
        elif ext == "json": content_type = "application/json"
        elif ext == "webp": content_type = "image/webp"
        elif ext == "ico": content_type = "image/x-icon"
        
        try:
            file_size = os.path.getsize(filepath)
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.end_headers()
            
            if file_size > 1_048_576:  # 1MB threshold: stream in chunks
                with open(filepath, "rb") as f:
                    while chunk := f.read(65536):
                        self.wfile.write(chunk)
            else:
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f"Server Error: {str(e)}")

    def handle_civitai_search(self):
        try:
            qs = parse_qs(urlparse(self.path).query)
            query = qs.get("query", [""])[0]
            type_filter = qs.get("type", [""])[0]
            offset = int(qs.get("offset", ["0"])[0])
            
            # Cache Check (15 mins TTL)
            cache_key = f"{query}_{type_filter}_{offset}"
            global _civitai_search_cache
            now = time.time()
            if cache_key in _civitai_search_cache:
                cached = _civitai_search_cache[cache_key]
                if now - cached["timestamp"] < 900:
                    self.send_json_response({"items": cached["data"]})
                    return
            
            payload = {
                "queries": [
                    {
                        "q": query,
                        "indexUid": "models_v9",
                        "limit": 40,
                        "offset": offset
                    }
                ]
            }
            
            filters = []
            if type_filter and type_filter != "Text Encoder":
                filters.append(f'(type="{type_filter}")')
            if filters:
                payload["queries"][0]["filter"] = " AND ".join(filters)
            
            url = "https://search-new.civitai.com/multi-search"
            # Load override key from settings if available
            search_key = _get_settings().get("civitai_search_key", _CIVITAI_SEARCH_KEY)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {search_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://civitai.com/",
                "Origin": "https://civitai.com"
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                ms_data = json.loads(res.read().decode('utf-8'))
            
            hits = ms_data.get("results", [{}])[0].get("hits", [])
            
            items = []
            for h in hits:
                version = h.get("version", {})
                images = h.get("images", [])
                mapped_imgs = []
                for img in images:
                    img_id = img.get("url") or img.get("id")
                    if not img_id or str(img_id).lower() == "undefined":
                        continue
                        
                    if not str(img_id).startswith("http"):
                        img_url = f"https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/{img_id}/width=450/image.jpeg"
                    else:
                        img_url = img_id
                        
                    mapped_imgs.append({
                        "url": img_url,
                        "type": img.get("type", "image")
                    })
                
                version_id = version.get("id")
                download_url = f"https://civitai.com/api/download/models/{version_id}" if version_id else None
                
                # Extract real file info from hashes/version if available
                version_hashes = h.get("hashes", [])
                file_name = version.get("fileName") or f"{h.get('name', 'ModelFile')}.safetensors"

                v1_item = {
                    "id": h.get("id"),
                    "name": h.get("name"),
                    "type": h.get("type", "Model"),
                    "nsfw": h.get("nsfw", False),
                    "creator": {"username": h.get("user", {}).get("username", "Unknown")},
                    "stats": {"downloadCount": h.get("metrics", {}).get("downloadCount", 0)},
                    "modelVersions": [{
                        "name": version.get("name", "Base"),
                        "baseModel": version.get("baseModel", "Unknown"),
                        "availability": version.get("availability") or h.get("availability", "Public"),
                        "earlyAccessEndsAt": version.get("earlyAccessEndsAt") or h.get("earlyAccessDeadline"),
                        "earlyAccessTimeFrame": version.get("earlyAccessTimeFrame", 0),
                        "images": mapped_imgs,
                        "files": [{
                            "sizeKB": version.get("fileSizeKB", 0),
                            "name": file_name,
                            "type": "Model",
                            "primary": True,
                            "downloadUrl": download_url
                        }],
                        "trainedWords": h.get("triggerWords", [])
                    }],
                    "tags": h.get("tags", [])
                }
                items.append(v1_item)
                
            _civitai_search_cache[cache_key] = {"timestamp": now, "data": items}
            # Evict oldest entries if cache exceeds max size
            if len(_civitai_search_cache) > _CIVITAI_CACHE_MAX:
                oldest_key = min(_civitai_search_cache, key=lambda k: _civitai_search_cache[k]["timestamp"])
                del _civitai_search_cache[oldest_key]
            self.send_json_response({"items": items})
        except Exception as e:
            logging.error(f"Target CivitAI proxy search failed: {e}")
            self.send_json_response({"error": str(e), "items": []}, 500)

    def send_api_models(self):
        try:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            
            limit = int(qs.get('limit', [1000])[0])
            offset = int(qs.get('offset', [0])[0])

            db = _get_db()
            result = db.get_models_paginated(limit=limit, offset=offset)
                
            self.send_json_response({
                "status": "success", 
                "models": result["models"],
                "total": result["total"],
                "limit": limit,
                "offset": offset
            })
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    # ── Disk size cache (non-blocking) ─────────────────────────────
    _disk_size_cache = {}  # {package_id: size_mb}
    _disk_size_thread = None

    @classmethod
    def _compute_dir_size_mb(cls, path: str) -> float:
        """Calculate total size of a directory in MB. Returns 0 on error."""
        total = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        except OSError:
            pass
        return round(total / (1024 * 1024), 1)

    @classmethod
    def _refresh_disk_sizes(cls, packages_dir: str):
        """Background worker: refresh disk sizes for all installed packages."""
        def _worker():
            try:
                if not os.path.exists(packages_dir):
                    return
                for d in os.listdir(packages_dir):
                    app_path = os.path.join(packages_dir, d)
                    if os.path.isdir(app_path):
                        cls._disk_size_cache[d] = cls._compute_dir_size_mb(app_path)
            except Exception:
                pass
            finally:
                cls._disk_size_thread = None

        if cls._disk_size_thread is None or not cls._disk_size_thread.is_alive():
            cls._disk_size_thread = threading.Thread(target=_worker, daemon=True)
            cls._disk_size_thread.start()

    def send_api_packages(self):
        packages_dir = os.path.join(self.root_dir, "packages")
        packages = []
        if os.path.exists(packages_dir):
            for d in os.listdir(packages_dir):
                app_path = os.path.join(packages_dir, d)
                if os.path.isdir(app_path):
                    manifest_path = os.path.join(app_path, "manifest.json")
                    pkg_info = {"id": d, "name": d.capitalize()}
                    
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                                pkg_info["name"] = manifest.get("name", d.capitalize())
                                pkg_info["installed_version"] = manifest.get("installed_version")
                                pkg_info["installed_at"] = manifest.get("installed_at")
                                pkg_info["port"] = manifest.get("port")
                        except (json.JSONDecodeError, OSError) as e:
                            logging.warning(f"Failed to read manifest for {d}: {e}")
                    
                    # Add running status by evaluating process handle
                    entry = AIWebServer.running_processes.get(d)
                    proc = entry.get("process") if isinstance(entry, dict) else entry
                    if proc and proc.poll() is None:
                        pkg_info["is_running"] = True
                    else:
                        pkg_info["is_running"] = False
                        if entry:
                            # Close leaked log file handle if present
                            if isinstance(entry, dict) and entry.get("log_file"):
                                try:
                                    entry["log_file"].close()
                                except Exception:
                                    pass
                            del AIWebServer.running_processes[d]

                    # Disk usage from cache (non-blocking)
                    pkg_info["disk_size_mb"] = AIWebServer._disk_size_cache.get(d)

                    packages.append(pkg_info)
                    
        # Trigger background refresh of disk sizes
        AIWebServer._refresh_disk_sizes(packages_dir)

        self.send_json_response({"status": "success", "packages": packages})

    def send_api_recipes(self):
        recipes_dir = os.path.join(self.root_dir, ".backend", "recipes")
        recipes = []
        if os.path.exists(recipes_dir):
            for file in os.listdir(recipes_dir):
                if file.endswith(".json"):
                    try:
                        with open(os.path.join(recipes_dir, file), 'r', encoding='utf-8') as f:
                            recipe = json.load(f)
                            recipes.append({
                                "id": file,
                                "app_id": recipe.get("app_id"),
                                "name": recipe.get("name", file),
                                "repository": recipe.get("repository", ""),
                                "description": recipe.get("description", "")
                            })
                    except Exception as e:
                        logging.error(f"Error reading recipe {file}: {e}")
                        
        self.send_json_response({"status": "success", "recipes": recipes})

    # NOTE: Duplicate handle_install_status removed (was overridden by definition at line 705)

    def handle_build_recipe(self, data):
        app_id = data.get("app_id")
        name = data.get("name")
        repository = data.get("repository")
        launch = data.get("launch")
        pip_packages = data.get("pip_packages", [])
        symlink_targets = data.get("symlink_targets", [])
        platform_flags = data.get("platform_flags", "")
        requirements_file = data.get("requirements_file", "requirements.txt")

        if not app_id or not name:
            self.send_json_response({"status": "error", "message": "Missing app_id or name"}, 400)
            return

        recipe_id = f"{app_id}_recipe.json"
        recipe_path = os.path.join(self.root_dir, ".backend", "recipes", recipe_id)

        recipe = {
            "app_id": app_id,
            "name": name,
            "repository": repository,
            "launch": launch,
            "pip_packages": pip_packages,
            "symlink_targets": symlink_targets,
            "platform_flags": platform_flags,
            "requirements_file": requirements_file
        }

        try:
            os.makedirs(os.path.dirname(recipe_path), exist_ok=True)
            with open(recipe_path, 'w', encoding='utf-8') as f:
                json.dump(recipe, f, indent=4)
            self.send_json_response({"status": "success", "recipe_id": recipe_id, "message": f"Recipe {recipe_id} created successfully."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_install_status(self):
        """Serve the install_jobs.json file so the frontend can poll progress."""
        jobs_file = os.path.join(self.root_dir, ".backend", "cache", "install_jobs.json")
        try:
            if os.path.exists(jobs_file):
                with open(jobs_file, 'r', encoding='utf-8') as f:
                    jobs = json.load(f)
            else:
                jobs = {}
            self.send_json_response({"status": "success", "jobs": jobs})
        except (json.JSONDecodeError, OSError) as e:
            self.send_json_response({"status": "success", "jobs": {}})

    def handle_install(self, data):
        recipe_id = data.get("recipe_id")
        if not recipe_id:
            self.send_json_response({"status": "error", "message": "Missing recipe_id"}, 400)
            return
            
        recipe_path = os.path.join(self.root_dir, ".backend", "recipes", recipe_id)
        if not os.path.exists(recipe_path):
            self.send_json_response({"status": "error", "message": "Recipe not found"}, 404)
            return

        # Resolve app_id from recipe to check for duplicate installs
        try:
            with open(recipe_path, 'r', encoding='utf-8') as f:
                recipe_data = json.load(f)
            app_id = recipe_data.get("app_id", recipe_id)
        except Exception:
            app_id = recipe_id

        # Guard: Reject duplicate installs for the same app
        existing = AIWebServer.running_installs.get(app_id)
        if existing and existing.poll() is None:
            self.send_json_response({
                "status": "error",
                "message": f"{app_id} is already being installed. Please wait for it to finish."
            }, 409)
            return

        installer_script = os.path.join(self.root_dir, ".backend", "installer_engine.py")
        
        logging.info(f"Triggering background installation for {recipe_id}")
        
        # Spawn isolated installation process with PID tracking
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
            
        proc = subprocess.Popen([sys.executable, installer_script, recipe_path], **kwargs)
        AIWebServer.running_installs[app_id] = proc
        
        self.send_json_response({"status": "success", "message": "Installation started in background"})

    def handle_launch(self, data):
        package_id = data.get("package_id")
        if not package_id:
            self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
            return

        # Guard: Prevent double-launch — return existing URL if already running
        existing = AIWebServer.running_processes.get(package_id)
        if existing:
            proc = existing.get("process") if isinstance(existing, dict) else existing
            if proc and proc.poll() is None:
                # Already running — resolve port and return URL
                port = existing.get("port", 7860) if isinstance(existing, dict) else 7860
                url = f"http://127.0.0.1:{port}"
                self.send_json_response({"status": "success", "message": "Package already running.", "url": url, "already_running": True})
                return

        package_path = os.path.join(self.root_dir, "packages", package_id)
        manifest_path = os.path.join(package_path, "manifest.json")
        app_path = os.path.join(package_path, "app")
        
        # PRE-FLIGHT 1: Recover missing manifest
        if not os.path.exists(manifest_path) and os.path.exists(app_path):
            recipe_path = os.path.join(self.root_dir, ".backend", "recipes", f"{package_id}.json")
            if os.path.exists(recipe_path):
                shutil.copy2(recipe_path, manifest_path)
                logging.info(f"Pre-flight: Auto-recovered manifest.json for {package_id}")

        if not os.path.exists(manifest_path) or not os.path.exists(app_path):
             self.send_json_response({"status": "error", "message": "Package improperly installed"}, 404)
             return

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            self.send_json_response({"status": "error", "message": f"Could not read manifest: {str(e)}"}, 500)
            return

        launch_cmd = manifest.get("launch_command")
        if not launch_cmd:
            self.send_json_response({"status": "error", "message": "No launch_command found in manifest"}, 400)
            return

        # PRE-FLIGHT 2: Verify the launch script actually exists
        launch_script = launch_cmd.split(" ")[0]  # e.g. "main.py" from "main.py --arg"
        launch_script_path = os.path.join(app_path, launch_script)
        if not os.path.exists(launch_script_path):
            logging.error(f"Launch script not found: {launch_script_path}")
            self.send_json_response({
                "status": "error",
                "message": f"Source code is missing or corrupted ({launch_script} not found). Use Repair to re-download.",
                "needs_repair": True
            }, 404)
            return

        # PRE-FLIGHT 2: Symlinks verification
        try:
            symlinks = manifest.get("model_symlinks", {})
            vault_dir = os.path.join(self.root_dir, "Global_Vault")
            for vault_src, app_target in symlinks.items():
                source_path = os.path.join(vault_dir, vault_src)
                target_path = os.path.join(app_path, app_target)
                if not os.path.exists(target_path):
                    os.makedirs(source_path, exist_ok=True)
                    create_safe_directory_link(source_path, target_path)
                    logging.info(f"Pre-flight: Recreated missing symlink for {app_target}")
        except Exception as e:
            logging.error(f"Pre-flight symlink check failed: {e}")

        # Determine python executable location
        if os.name == 'nt':
            python_exe = os.path.join(package_path, "env", "Scripts", "python.exe")
        else:
            python_exe = os.path.join(package_path, "env", "bin", "python")
            
        # PRE-FLIGHT 3: Executable environment verification
        if not os.path.exists(python_exe):
            self.send_json_response({
                "status": "error", 
                "message": "Isolated python environment not found. Please repair the installation."
            }, 404)
            return

        logging.info(f"Launching {package_id}...")
        
        # Pipe output to a runtime log file for web-terminal tailing (append mode preserves history)
        log_path = os.path.join(package_path, "runtime.log")
        try:
            log_file = open(log_path, 'a', encoding='utf-8')
            log_file.write(f"\n{'='*60}\n")
            log_file.write(f"  Session started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"{'='*60}\n\n")
            log_file.flush()
        except OSError as e:
            logging.error(f"Failed to open log file for {package_id}: {e}")
            self.send_json_response({"status": "error", "message": f"Cannot open log file: {e}"}, 500)
            return
            
        # Combine command, e.g. python_exe main.py
        full_command = [python_exe] + launch_cmd.split(" ")
        
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
            
        p = subprocess.Popen(full_command, cwd=app_path, stdout=log_file, stderr=subprocess.STDOUT, **kwargs)
        
        # Read port from manifest, fall back to legacy hardcoded map
        _fallback_ports = {"comfyui": 8188, "forge": 7860, "auto1111": 7861, "fooocus": 8888}
        port = manifest.get("port", _fallback_ports.get(package_id, 7860))
        
        AIWebServer.running_processes[package_id] = {"process": p, "log_file": log_file, "port": port}
        url = f"http://127.0.0.1:{port}"
        
        self.send_json_response({"status": "success", "message": "Package starting...", "url": url, "port": port})

    def handle_repair_dependency(self, data):
        package_id = data.get("package_id")
        if not package_id:
            self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
            return
            
        package_path = os.path.join(self.root_dir, "packages", package_id)
        if os.name == 'nt':
            python_exe = os.path.join(package_path, "env", "Scripts", "python.exe")
        else:
            python_exe = os.path.join(package_path, "env", "bin", "python")
            
        req_path = os.path.join(package_path, "app", "requirements.txt")
        if not os.path.exists(python_exe):
            self.send_json_response({"status": "error", "message": "Python env not found"}, 404)
            return
            
        logging.info(f"Auto-repairing dependencies for {package_id}...")
        try:
            cmd = [python_exe, "-m", "pip", "install"]
            if os.path.exists(req_path):
                cmd.extend(["-r", "requirements.txt"])
            else:
                self.send_json_response({"status": "error", "message": "requirements.txt not found"}, 404)
                return
                
            kwargs = {}
            if os.name == 'nt':
                kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
                
            subprocess.Popen(cmd, cwd=os.path.join(package_path, "app"), **kwargs)
            self.send_json_response({"status": "success", "message": "Repair started..."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": f"Repair failed: {str(e)}"}, 500)

    def handle_repair_install(self, data):
        """Repair a corrupted package by re-running the install pipeline.
        
        The installer_engine now detects corrupted app directories (missing source
        but .git present) and handles them with a temp-clone-and-copy fallback.
        """
        package_id = data.get("package_id")
        if not package_id:
            self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
            return

        recipe_path = os.path.join(self.root_dir, ".backend", "recipes", f"{package_id}.json")

        if not os.path.exists(recipe_path):
            self.send_json_response({"status": "error", "message": f"No recipe found for {package_id}"}, 404)
            return

        # Auto-stop running process first
        AIWebServer._kill_tracked_process(package_id)

        # Clear stale install job status so frontend doesn't see old "completed"
        jobs_file = os.path.join(self.root_dir, ".backend", "cache", "install_jobs.json")
        try:
            if os.path.exists(jobs_file):
                with open(jobs_file, 'r', encoding='utf-8') as f:
                    jobs = json.load(f)
                if package_id in jobs:
                    del jobs[package_id]
                with open(jobs_file, 'w', encoding='utf-8') as f:
                    json.dump(jobs, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not clear stale install job for {package_id}: {e}")

        # Re-run the full install pipeline (handles locked dirs with temp-clone fallback)
        installer_script = os.path.join(self.root_dir, ".backend", "installer_engine.py")
        logging.info(f"Repair: Re-installing {package_id} from recipe...")

        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)

        # Track to prevent duplicate installs
        existing = AIWebServer.running_installs.get(package_id)
        if existing and existing.poll() is None:
            self.send_json_response({"status": "error", "message": f"{package_id} repair is already in progress."}, 409)
            return

        proc = subprocess.Popen([sys.executable, installer_script, recipe_path], **kwargs)
        AIWebServer.running_installs[package_id] = proc

        self.send_json_response({"status": "success", "message": f"Repair started for {package_id}. The app will be re-downloaded."})

    def handle_stop(self, data=None):
        package_id = data.get("package_id") if data else None
            
        if not package_id:
            self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
            return

        if package_id not in AIWebServer.running_processes:
            self.send_json_response({"status": "error", "message": "Package not running or not tracked"}, 404)
            return

        logging.info(f"Terminating package {package_id}...")
        AIWebServer._kill_tracked_process(package_id)
        self.send_json_response({"status": "success", "message": "Package stopped successfully"})

    def handle_restart(self, data):
        """Atomic restart: stop → wait for port release → re-launch in a single request."""
        package_id = data.get("package_id")
        if not package_id:
            self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
            return

        AIWebServer._kill_tracked_process(package_id)

        # Brief delay to let the OS release the port
        time.sleep(1.0)

        # Re-launch via the existing handler
        self.handle_launch(data)

    def handle_uninstall(self, data):
        package_id = data.get("package_id")
        if not package_id:
            self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
            return

        # Safety: Auto-stop the package if it's currently running
        AIWebServer._kill_tracked_process(package_id)

        logging.info(f"Triggering uninstallation for {package_id}")
        
        try:
            from installer_engine import RecipeInstaller
            installer = RecipeInstaller(self.root_dir)
            success = installer.uninstall(package_id)
            if success:
                self.send_json_response({"status": "success", "message": "Package uninstalled successfully"})
            else:
                self.send_json_response({"status": "error", "message": "Failed to uninstall package"}, 500)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_get_extensions(self):
        try:
            qs = parse_qs(urlparse(self.path).query)
            package_id = qs.get("package_id", [""])[0]
            
            if not package_id:
                self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
                return
                
            # For now, extensions only apply strictly to ComfyUI (or similar structure)
            target_dir = os.path.join(self.root_dir, "packages", package_id, "custom_nodes")
            extensions = []
            
            if os.path.exists(target_dir):
                for folder in os.listdir(target_dir):
                    ext_path = os.path.join(target_dir, folder)
                    if os.path.isdir(ext_path) and not folder.startswith("__"):
                        extensions.append({"name": folder, "path": ext_path})
            
            self.send_json_response({"status": "success", "extensions": extensions})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_install_extension(self, data):
        package_id = data.get("package_id")
        repo_url = data.get("repo_url")
        
        if not package_id or not repo_url:
            self.send_json_response({"status": "error", "message": "Missing package_id or repo_url"}, 400)
            return
            
        target_dir = os.path.join(self.root_dir, "packages", package_id, "custom_nodes")
        os.makedirs(target_dir, exist_ok=True)
        
        job_id = str(uuid.uuid4())[:8]
        
        try:
            from installer_engine import ExtensionCloneTracker
            tracker = ExtensionCloneTracker(self.root_dir)
            
            logging.info(f"Starting tracked clone of {repo_url} (job: {job_id})")
            t = threading.Thread(
                target=tracker.clone_with_progress,
                args=(repo_url, target_dir, job_id),
                daemon=False
            )
            t.start()
            self.send_json_response({"status": "success", "job_id": job_id, "message": "Extension clone started with progress tracking."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_extension_status(self):
        """GET /api/extensions/status?job_id=X — poll real-time clone progress."""

        qs = parse_qs(urlparse(self.path).query)
        job_id = qs.get("job_id", [""])[0]
        if not job_id:
            self.send_json_response({"status": "error", "message": "Missing job_id"}, 400)
            return
        try:
            from installer_engine import ExtensionCloneTracker
            tracker = ExtensionCloneTracker(self.root_dir)
            job = tracker.get_job_status(job_id)
            if not job:
                self.send_json_response({"status": "error", "message": "Job not found"}, 404)
            else:
                self.send_json_response(job)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_cancel_extension(self, data):
        """POST /api/extensions/cancel — kill a running extension clone."""
        job_id = data.get("job_id")
        if not job_id:
            self.send_json_response({"status": "error", "message": "Missing job_id"}, 400)
            return
        try:
            from installer_engine import ExtensionCloneTracker
            tracker = ExtensionCloneTracker(self.root_dir)
            success = tracker.cancel_job(job_id)
            if success:
                self.send_json_response({"status": "success", "message": "Clone cancelled."})
            else:
                self.send_json_response({"status": "error", "message": "Could not cancel (no PID or already finished)."}, 400)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_remove_extension(self, data):
        package_id = data.get("package_id")
        ext_name = data.get("ext_name")
        
        if not package_id or not ext_name:
            self.send_json_response({"status": "error", "message": "Missing package_id or ext_name"}, 400)
            return
            
        target_path = os.path.join(self.root_dir, "packages", package_id, "custom_nodes", ext_name)
        if not os.path.exists(target_path):
            self.send_json_response({"status": "error", "message": "Extension not found"}, 404)
            return
            
        try:
            shutil.rmtree(target_path)
            self.send_json_response({"status": "success", "message": "Extension removed."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_vault_updates(self, data):
        updater_script = os.path.join(self.root_dir, ".backend", "update_checker.py")
        python_exe = sys.executable
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
        
        try:
            subprocess.Popen([python_exe, updater_script], **kwargs)
            self.send_json_response({"status": "success", "message": "Update check started in background."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_vault_health_check(self, data):
        """Checks vault symlinks/junctions in installed packages for broken targets."""
        broken_links = 0
        packages_dir = os.path.join(self.root_dir, "packages")
        
        if os.path.exists(packages_dir):
            for d in os.listdir(packages_dir):
                pkg_models = os.path.join(packages_dir, d, "models")
                if not os.path.exists(pkg_models):
                    continue
                for entry in os.listdir(pkg_models):
                    target = os.path.join(pkg_models, entry)
                    is_link = False
                    # os.path.islink() returns False for NTFS junctions on Windows.
                    # Detect both symlinks and junctions via os.readlink().
                    try:
                        link_target = os.readlink(target)
                        is_link = True
                        if not os.path.exists(link_target):
                            try:
                                os.unlink(target)
                                broken_links += 1
                                logging.info(f"Removed broken link: {target} -> {link_target}")
                            except OSError as e:
                                logging.warning(f"Failed to unlink broken link {target}: {e}")
                    except (OSError, ValueError):
                        pass  # Not a link/junction — skip
                                
        self.send_json_response({"status": "success", "message": f"Repaired {broken_links} broken symlinks/junctions in packages."})

    def handle_vault_repair(self, data):
        """POST /api/vault/repair — re-fetch metadata + thumbnails for a model.
        Accepts file_hash directly, or falls back to filename-based lookup."""
        file_hash = data.get("file_hash")
        filename = data.get("filename")
        
        try:
            from civitai_client import CivitaiClient

            
            db = _get_db()
            
            # Resolve file_hash from filename if not directly provided
            if not file_hash and filename:
                model = db.get_model_by_filename(filename)
                if model:
                    file_hash = model.get("file_hash")
            
            if not file_hash:
                self.send_json_response({"status": "error", "message": "Could not resolve model. Provide file_hash or a valid filename."}, 400)
                return
            
            client = CivitaiClient(self.root_dir)
            
            # Apply user's CivitAI API key if configured
            api_key = _get_settings().get("civitai_api_key", "")
            if api_key:
                client.headers["Authorization"] = f"Bearer {api_key}"
            
            success = client.repair_model_metadata(file_hash)
            if success:
                self.send_json_response({"status": "success", "message": "Metadata and thumbnail refreshed successfully."})
            else:
                self.send_json_response({"status": "error", "message": "Could not fetch metadata from CivitAI for this model. It may be a local-only model."}, 404)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_get_settings(self):
        try:
            data = _get_settings()
            self.send_json_response(data)
        except Exception as e:
            logging.warning(f"Failed to read settings, returning defaults: {e}")
            self.send_json_response({"theme": "dark", "civitai_api_key": "", "auto_updates": True})

    def handle_save_settings(self, data):
        try:
            _save_settings(data)
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_system_update(self, data):
        updater_script = os.path.join(self.root_dir, ".backend", "updater.py")
        if not os.path.exists(updater_script):
            self.send_json_response({"status": "error", "message": "Updater script not found!"}, 404)
            return
            
        python_exe = sys.executable
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
        
        try:
            subprocess.Popen([python_exe, updater_script, "--pid", str(os.getpid())], **kwargs)
            self.send_json_response({"status": "success", "message": "Applying System Update. The server may restart..."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_get_logs(self):
        try:
    
            qs = parse_qs(urlparse(self.path).query)
            package_id = qs.get("package_id", [""])[0]
            if not package_id:
                self.send_json_response({"status": "error", "message": "Missing package_id"}, 400)
                return
            
            log_path = os.path.join(self.root_dir, "packages", package_id, "runtime.log")
            if not os.path.exists(log_path):
                self.send_json_response({"status": "success", "logs": "--- No active execution environment. Logs empty. ---"})
                return
            
            # Tail-seek optimization: read only the last 32KB instead of the entire file
            _TAIL_BYTES = 32 * 1024
            try:
                file_size = os.path.getsize(log_path)
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if file_size > _TAIL_BYTES:
                        f.seek(file_size - _TAIL_BYTES)
                        f.readline()  # Skip partial first line after seek
                    tail = f.read()
            except OSError:
                tail = "--- Error reading log file ---"
            
            self.send_json_response({"status": "success", "logs": tail})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_download(self, data):
        url = data.get("url")
        filename = data.get("filename")
        model_name = data.get("model_name")
        dest_folder = data.get("dest_folder")
        api_key = data.get("api_key")

        if not all([url, filename, model_name, dest_folder]):
            self.send_json_response({"status": "error", "message": "Missing download parameters"}, 400)
            return
            
        job_id = str(uuid.uuid4())
        
        downloader_script = os.path.join(self.root_dir, ".backend", "download_engine.py")
        python_exe = sys.executable

        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)

        cmd = [
            python_exe, downloader_script,
            "--job_id", job_id,
            "--url", url,
            "--dest_folder", dest_folder,
            "--filename", filename,
            "--model_name", model_name,
            "--root_dir", self.root_dir
        ]
        if api_key:
            cmd.extend(["--api_key", api_key])

        subprocess.Popen(cmd, **kwargs)
        self.send_json_response({"status": "success", "job_id": job_id})

    def handle_retry_download(self, data):
        job_id = data.get("job_id")
        api_key = data.get("api_key")
        
        if not job_id:
            self.send_json_response({"status": "error", "message": "Missing job_id"}, 400)
            return
            
        cache_file = os.path.join(self.root_dir, ".backend", "cache", "downloads.json")
        if not os.path.exists(cache_file):
            self.send_json_response({"status": "error", "message": "No download history found"}, 404)
            return
            
        try:
            with open(cache_file, "r") as f:
                jobs = json.load(f)
            
            job = jobs.get(job_id)
            if not job:
                self.send_json_response({"status": "error", "message": "Job not found"}, 404)
                return
                
            url = job.get("url")
            dest_folder = job.get("dest_folder")
            filename = job.get("filename")
            model_name = job.get("model_name")
            
            if not all([url, dest_folder, filename, model_name]):
                self.send_json_response({"status": "error", "message": "Incomplete job metadata for retry"}, 400)
                return
                
            # Trigger same logic as handle_download but reuse job params
            # We use handle_download's logic directly to spawn a NEW job_id or same?
            # User likely wants to "retry" the same slot, but my system uses UUIDs per launch.
            # I will spawn a new job but the UI will probably just show a new entry.
            # Actually, let's just re-launch handle_download with the old params.
            self.handle_download({
                "url": url,
                "filename": filename,
                "model_name": model_name,
                "dest_folder": dest_folder,
                "api_key": api_key
            })
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_get_downloads(self):
        cache_file = os.path.join(self.root_dir, ".backend", "cache", "downloads.json")
        if not os.path.exists(cache_file):
            self.send_json_response({})
            return
        
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            self.send_json_response(data)
        except Exception:
            self.send_json_response({})

    def handle_clear_downloads(self):
        cache_file = os.path.join(self.root_dir, ".backend", "cache", "downloads.json")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                self.send_json_response({"status": "success", "message": "Download history cleared"})
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, 500)
        else:
            self.send_json_response({"status": "success", "message": "Already empty"})

    def handle_delete_model(self, data):
        filename = data.get("filename")
        category = data.get("category")
        if not filename or not category:
            self.send_json_response({"status": "error", "message": "Missing filename or category"}, 400)
            return
            
        filepath = os.path.join(self.root_dir, "Global_Vault", category, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                # Cleanup DB natively using metadata_db
    
                db = _get_db()
                db.remove_model_by_filename(filename)
                self.send_json_response({"status": "success", "message": "Model deleted"})
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, 500)
        else:
            self.send_json_response({"status": "error", "message": "File not found"}, 404)

    def handle_import_file(self, data):
        src_path = data.get("path")
        category = data.get("category", "")
        api_key = data.get("api_key", "")
        if not src_path or not os.path.exists(src_path):
            self.send_json_response({"status": "error", "message": "File not found"}, 400)
            return
        try:
            from import_engine import start_import
            import_id = start_import(src_path, category, self.root_dir, api_key)
            self.send_json_response({"status": "queued", "import_id": import_id})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_import_status(self):

        qs = parse_qs(urlparse(self.path).query)
        import_id = qs.get("id", [None])[0]
        if not import_id:
            self.send_json_response({"status": "error", "message": "Missing id"}, 400)
            return
        try:
            from import_engine import get_import_status
            result = get_import_status(import_id)
            if not result:
                self.send_json_response({"status": "error", "message": "Job not found"}, 404)
            else:
                self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_import_jobs(self):
        try:
            from import_engine import list_import_jobs
            self.send_json_response(list_import_jobs())
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_list(self):
        qs = parse_qs(urlparse(self.path).query)
        sort = qs.get("sort", ["newest"])[0]
        tag = qs.get("tag", [""])[0]
        try:
            db = _get_db()
            if tag:
                rows = db.list_generations_by_tag(tag)
            else:
                rows = db.list_generations(sort=sort)
                
            # Self-heal: Collect stale IDs and batch-delete them
            valid_rows = []
            stale_ids = []
            for r in rows:
                img_path = r.get("image_path", "")
                if not img_path:
                    stale_ids.append(r.get("id"))
                elif img_path.startswith("data:") or img_path.startswith("http://") or img_path.startswith("https://") or img_path.startswith("/api/"):
                    valid_rows.append(r)
                elif os.path.exists(img_path):
                    valid_rows.append(r)
                else:
                    stale_ids.append(r.get("id"))
            
            # Single batch DELETE instead of N individual queries
            if stale_ids:
                db.batch_delete_generations(stale_ids)
                logging.info(f"Gallery self-heal: removed {len(stale_ids)} stale entries.")
            
            self.send_json_response({"status": "success", "generations": valid_rows})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_tags(self):
        """GET /api/gallery/tags — returns unique tags from all generations."""
        try:

            db = _get_db()
            tags = db.get_gallery_tags()
            self.send_json_response({"status": "success", "tags": tags})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_save(self, data):
        try:

            db = _get_db()
            row_id = db.save_generation(
                image_path=data.get("image_path"),
                prompt=data.get("prompt", ""),
                negative=data.get("negative", ""),
                model=data.get("model", ""),
                seed=data.get("seed"),
                steps=data.get("steps"),
                cfg=data.get("cfg"),
                sampler=data.get("sampler", ""),
                width=data.get("width"),
                height=data.get("height"),
                extra_json=json.dumps(data.get("extra", {}))
            )
            self.send_json_response({"status": "success", "id": row_id})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_delete(self, data):
        gen_id = data.get("id")
        if not gen_id:
            self.send_json_response({"status": "error", "message": "Missing id"}, 400)
            return
        try:

            db = _get_db()
            db.delete_generation(gen_id)
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_rate(self, data):
        gen_id = data.get("id")
        rating = data.get("rating", 0)
        if not gen_id:
            self.send_json_response({"status": "error", "message": "Missing id"}, 400)
            return
        try:

            db = _get_db()
            db.rate_generation(gen_id, rating)
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_open_folder(self, data):
        category = data.get("category")
        if not category:
            self.send_json_response({"status": "error", "message": "Missing category"}, 400)
            return
            
        folder_path = os.path.normpath(os.path.join(self.root_dir, "Global_Vault", category))
        os.makedirs(folder_path, exist_ok=True)
            
        try:
            if os.name == 'nt':
                subprocess.Popen(['explorer', folder_path])
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, folder_path])
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_comfy_proxy(self, data):
        endpoint = data.get("endpoint")
        if not endpoint:
            self.send_json_response({"error": "No endpoint specified"}, 400)
            return
            
        payload = data.get("payload")
        if endpoint == "/api/generate" and payload:
            # Sprint 12: Upload inpainting mask to ComfyUI if present
            mask_b64 = payload.get("mask_b64")
            if mask_b64:
                mask_name = self._upload_b64_to_comfy(mask_b64, "inpaint_mask.png")
                if mask_name:
                    payload["mask_image_name"] = mask_name
                # Also upload the init_image for inpainting if sent as b64
                init_b64 = payload.get("init_image_b64")
                if init_b64 and not payload.get("init_image_name"):
                    init_name = self._upload_b64_to_comfy(init_b64, "inpaint_source.png")
                    if init_name:
                        payload["init_image_name"] = init_name
                        payload["denoising_strength"] = payload.get("denoising_strength", 0.75)
                        
            try:
                payload = build_comfy_workflow(payload)
                endpoint = "/prompt"
            except Exception as e:
                self.send_json_response({"error": str(e)}, 400)
                return


        url = f"http://127.0.0.1:8188{endpoint}"
        
        try:
            if payload:
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=30) as res:
                content = res.read().decode('utf-8')
                self.send_json_response(json.loads(content))
        except Exception as e:
            err_msg = str(e)
            if "Connection refused" in err_msg or "WinError 10061" in err_msg or "RemoteDisconnected" in err_msg:
                entry = AIWebServer.running_processes.get("comfyui")
                p = entry.get("process") if isinstance(entry, dict) else entry
                if p and p.poll() is not None:
                    # Process died quietly. Parse logs.
                    log_path = os.path.join(self.root_dir, "packages", "comfyui", "runtime.log")
                    missing_mod = None
                    if os.path.exists(log_path):
                        try:
                            with open(log_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()[-50:]
                            for line in lines:
                                if "ModuleNotFoundError" in line or "ImportError" in line:
                                    missing_mod = line.strip()
                                    break
                        except Exception:
                            pass
                    
                    if missing_mod:
                        self.send_json_response({
                            "error": "engine_crashed", 
                            "message": f"Engine crashed. {missing_mod}",
                            "missing_module": missing_mod,
                            "repair_available": True
                        }, 500)
                        return
            self.send_json_response({"error": err_msg}, 500)

    def handle_comfy_image(self):
        # proxy raw image bytes from comfyUI
        parsed = urlparse(self.path)
        qs = parsed.query
        url = f"http://127.0.0.1:8188/view?{qs}"
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as res:
                img_data = res.read()
                
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(img_data)
        except Exception as e:
            self.send_error(500, str(e))

    def handle_comfy_upload(self):

        try:
            length = int(self.headers['Content-Length'])
            boundary = self.headers['Content-Type'].split('boundary=')[1].encode()
            body = self.rfile.read(length)
            
            url = f"http://127.0.0.1:8188/upload/image"
            req = urllib.request.Request(url, data=body, headers={'Content-Type': self.headers['Content-Type']})
            with urllib.request.urlopen(req, timeout=30) as res:
                self.send_json_response(json.loads(res.read().decode('utf-8')))
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def _upload_b64_to_comfy(self, b64_data, filename="upload.png"):
        """Sprint 12: Upload base64-encoded PNG to ComfyUI's /upload/image endpoint.
        Returns the filename ComfyUI assigned, or None on failure."""
        try:
            img_bytes = base64.b64decode(b64_data)
            boundary = b"----AetherVaultMaskBoundary"
            body = b"--" + boundary + b"\r\n"
            body += f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode()
            body += b"Content-Type: image/png\r\n\r\n"
            body += img_bytes
            body += b"\r\n--" + boundary + b"--\r\n"
            
            url = "http://127.0.0.1:8188/upload/image"
            headers = {"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"}
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as res:
                result = json.loads(res.read().decode('utf-8'))
                return result.get("name", filename)
        except Exception as e:
            logging.warning(f"Failed to upload {filename} to ComfyUI: {e}")
            return None

    def _proxy_to_engine(self, engine_name: str, data: dict):
        """Consolidated proxy dispatcher for A1111, Forge, and Fooocus backends.
        Uses _ENGINE_CONFIG for port/translator lookup."""
        config = _ENGINE_CONFIG.get(engine_name)
        if not config:
            self.send_json_response({"error": f"Unknown engine: {engine_name}"}, 400)
            return

        payload = data.get("payload")
        endpoint = data.get("endpoint", config["gen_endpoint"])
        
        if endpoint == "/api/generate" and payload:
            try:
                payload = config["translator"](payload)
                # A1111/Forge: select img2img vs txt2img endpoint based on payload
                if engine_name in ("a1111", "forge") and "init_images" in payload:
                    endpoint = "/sdapi/v1/img2img"
                else:
                    endpoint = config["gen_endpoint"]
            except Exception as e:
                self.send_json_response({"error": str(e)}, 400)
                return
                
        url = f"http://127.0.0.1:{config['port']}{endpoint}"
        try:
            if payload:
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as res:
                content = res.read().decode('utf-8')
                self.send_json_response(json.loads(content))
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_a1111_proxy(self, data):
        self._proxy_to_engine("a1111", data)

    def handle_forge_proxy(self, data):
        self._proxy_to_engine("forge", data)

    def handle_fooocus_proxy(self, data):
        self._proxy_to_engine("fooocus", data)

    def handle_clear_dashboard_history(self, data):
        global _server_stats_cache
        try:
            # Clear downloads.json
            downloads_file = os.path.join(self.root_dir, ".backend", "cache", "downloads.json")
            if os.path.exists(downloads_file):
                with open(downloads_file, 'w') as f:
                    json.dump({}, f)
            # Add cleared_at timestamp via thread-safe settings helper
            _save_settings({"activity_cleared_at": time.time()})
            # Invalidate stats cache so next poll sees the change instantly
            _server_stats_cache["data"] = None
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_import_external(self, data):
        target_path = data.get("path")
        if not target_path or not os.path.exists(target_path) or not os.path.isdir(target_path):
            self.send_json_response({"status": "error", "message": "Invalid directory provided"}, 400)
            return
            
        try:
            folder_name = os.path.basename(os.path.abspath(target_path)).replace(" ", "_")
            if not folder_name: folder_name = "External_Import"
            vault_dir = os.path.join(self.root_dir, "Global_Vault", f"External_{folder_name}")
            os.makedirs(vault_dir, exist_ok=True)
            
            # Use symlink_manager logic which gracefully handles junction fallbacks
            try:
                create_safe_directory_link(target_path, os.path.join(vault_dir, "Models"))
                self.send_json_response({"status": "success"})
            except Exception as e:
                 self.send_json_response({"status": "error", "message": str(e)}, 500)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))



    def handle_vault_search(self):
        try:
    
            qs = parse_qs(urlparse(self.path).query)
            q = qs.get("query", [""])[0]
            limit = int(qs.get("limit", [50])[0])
            
            if not q:
                return self.send_api_models()
                
            logging.info(f"Performing semantic search for: {q}")

            db = _get_db()
            from embedding_engine import EmbeddingEngine
            engine = EmbeddingEngine(self.db_path)
            results = engine.search(q, top_k=limit)
            
            models = []
            for score, fhash in results:
                # Need similarity threshold to exclude bad matches
                if score < 0.1: continue
                m = db.get_model_by_hash(fhash)
                if m:
                    if m.get("metadata_json"):
                        try:
                            m["metadata"] = json.loads(m["metadata_json"])
                        except Exception:
                            m["metadata"] = {}
                    else:
                        m["metadata"] = {}
                    del m["metadata_json"]
                    
                    m["user_tags"] = db.get_user_tags(fhash)
                    m["search_score"] = float(score)
                    models.append(m)
                    
            self.send_json_response({"status": "success", "models": models})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_get_all_tags(self):
        try:

            db = _get_db()
            tags = db.get_all_user_tags()
            self.send_json_response({"status": "success", "tags": tags})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_add_tag(self, data):
        hash_val = data.get("file_hash")
        tag = data.get("tag")
        if not hash_val or not tag:
            self.send_json_response({"status": "error", "message": "Missing hash or tag"}, 400)
            return
        try:

            db = _get_db()
            db.add_user_tag(hash_val, tag.strip())
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_remove_tag(self, data):
        hash_val = data.get("file_hash")
        tag = data.get("tag")
        if not hash_val or not tag:
            self.send_json_response({"status": "error", "message": "Missing hash or tag"}, 400)
            return
        try:

            db = _get_db()
            db.remove_user_tag(hash_val, tag.strip())
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_hf_search(self):

        qs = parse_qs(urlparse(self.path).query)
        query = qs.get("query", [""])[0]
        type_filter = qs.get("type", [""])[0]
        limit = int(qs.get("limit", [40])[0])
        offset = int(qs.get("offset", [0])[0])
        
        filter_tags = None
        # Augment query for Text Encoder searches
        if type_filter == "Text Encoder":
            if not query:
                query = "clip t5-xxl encoder"
            else:
                query += " clip t5 encoder"
        elif type_filter and type_filter not in ["Model", "Checkpoint"]:
            filter_tags = type_filter.lower()
        
        try:
            from hf_client import HFClient
            api_key = _get_settings().get("hf_api_key")
            
            client = HFClient(api_key=api_key)
            result = client.search_models(query=query, limit=limit, offset=offset, filter_tags=filter_tags)
            self.send_json_response({"status": "success", "items": result})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_import_scan(self, data):
        try:

            from import_engine import start_import
            
            vault_dir = os.path.join(self.root_dir, "Global_Vault")
            db = _get_db()
            
            known_filenames = db.get_all_filenames()
            
            count = 0
            api_key = data.get("api_key", "")
            
            for root, _, files in os.walk(vault_dir):
                for f in files:
                    if any(f.lower().endswith(x) for x in ['.safetensors', '.ckpt', '.pt', '.bin']):
                        if f not in known_filenames:
                            f_path = os.path.join(root, f)
                            category = os.path.basename(root)
                            start_import(f_path, category, self.root_dir, api_key)
                            count += 1
                            
            self.send_json_response({"status": "success", "message": f"Queued {count} unmanaged files for background import.\nCheck terminal for process logs."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_vault_export(self, data):
        """POST /api/vault/export — export models as metadata JSON or streaming zip."""
        filenames = data.get("filenames", [])
        include_files = data.get("include_files", False)

        if not filenames:
            self.send_json_response({"status": "error", "message": "No filenames specified"}, 400)
            return

        try:

            db = _get_db()
            manifest = db.export_models_metadata(filenames)

            if not include_files:
                # Metadata-only export — return JSON
                self.send_json_response({
                    "status": "success",
                    "manifest": manifest,
                    "export_type": "metadata_only"
                })
                return

            # Streaming zip export with model files + manifest
            import zipfile
            import io

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                # Write metadata manifest
                zf.writestr('vault_manifest.json', json.dumps(manifest, indent=2, default=str))

                # Write model files
                for entry in manifest:
                    fn = entry.get('filename', '')
                    cat = entry.get('vault_category', '')
                    filepath = os.path.join(self.root_dir, 'Global_Vault', cat, fn)
                    if os.path.exists(filepath):
                        arcname = f"{cat}/{fn}"
                        zf.write(filepath, arcname)

            zip_bytes = buf.getvalue()
            ts = time.strftime('%Y%m%d_%H%M%S')
            filename = f"vault_export_{ts}.zip"

            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(zip_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(zip_bytes)

        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_server_status(self):
        global _vault_size_cache, _server_stats_cache
        try:
            db = _get_db()
            
            # Use cached settings instead of reading 627KB JSON every 3 seconds
            settings_data = _get_settings()
            lan_sharing = settings_data.get("lan_sharing", False)
            vault_size_warning_gb = settings_data.get('vault_size_warning_gb', 50)
            activity_cleared_at = settings_data.get('activity_cleared_at', 0)

            # Cache expensive DB queries with 30s TTL (polled every 3s = 10x reduction)
            now = time.time()
            if _server_stats_cache["data"] is None or now >= _server_stats_cache["expires"]:
                unpopulated = len(db.get_unpopulated_models())
                stats = db.get_dashboard_stats()
                raw_generations = db.get_recent_activity(limit=5)
                category_distribution = db.get_vault_category_distribution()
                _server_stats_cache["data"] = {
                    "unpopulated": unpopulated,
                    "stats": stats,
                    "raw_generations": raw_generations,
                    "category_distribution": category_distribution
                }
                _server_stats_cache["expires"] = now + _SERVER_STATS_TTL
            
            cached = _server_stats_cache["data"]
            unpopulated = cached["unpopulated"]
            stats = cached["stats"]
            raw_generations = cached["raw_generations"]
            category_distribution = cached["category_distribution"]
            
            downloads_file = os.path.join(self.root_dir, ".backend", "cache", "downloads.json")
            active_downloads = 0
            recent_downloads = []
            if os.path.exists(downloads_file):
                try:
                    with open(downloads_file, 'r') as f:
                        jobs = json.load(f)
                        active_downloads = sum(1 for j in jobs.values() if j.get("status") not in ["completed", "failed", "error"])
                        completed = [{"id": k, **v} for k, v in jobs.items() if v.get("status") == "completed"]
                        completed.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
                        recent_downloads = completed[:5]
                except (json.JSONDecodeError, OSError):
                    pass

            lan_ip = ""
            if lan_sharing:
                import socket
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    lan_ip = s.getsockname()[0]
                    s.close()
                except Exception:
                    lan_ip = "unknown"

            # Vault size: read from cache (updated by background scanner or 60s inline fallback)
            vault_size_bytes = _vault_size_cache["size"]
            if vault_size_bytes == 0 and now >= _vault_size_cache["expires"]:
                # First-time only fallback if background scanner hasn't run yet
                def _calc_vault_size():
                    vault_dir = os.path.join(self.root_dir, "Global_Vault")
                    total = 0
                    if os.path.exists(vault_dir):
                        for root, dirs, files in os.walk(vault_dir):
                            for f in files:
                                try:
                                    total += os.path.getsize(os.path.join(root, f))
                                except OSError:
                                    pass
                    _vault_size_cache["size"] = total
                    _vault_size_cache["expires"] = time.time() + 300  # 5 min TTL
                threading.Thread(target=_calc_vault_size, daemon=True).start()

            # Installed / running packages
            packages_dir = os.path.join(self.root_dir, "packages")
            installed_packages = 0
            if os.path.exists(packages_dir):
                installed_packages = sum(1 for d in os.listdir(packages_dir) if os.path.isdir(os.path.join(packages_dir, d)))
            running_packages = len(AIWebServer.running_processes)

            # Filter recent activity by cleared-at timestamp
            recent_generations = []
            for g in raw_generations:
                try:
                    dt = datetime.datetime.strptime(g.get("created_at", ""), "%Y-%m-%d %H:%M:%S.%f")
                    if dt.timestamp() > activity_cleared_at:
                        recent_generations.append(g)
                except Exception:
                    recent_generations.append(g)

            self.send_json_response({
                "unpopulated_models": unpopulated,
                "active_downloads": active_downloads,
                "is_syncing": (unpopulated > 0 or active_downloads > 0),
                "lan_sharing": lan_sharing,
                "lan_ip": lan_ip,
                "total_models": stats.get('total_models', 0),
                "total_generations": stats.get('total_generations', 0),
                "prompts_saved": stats.get('prompts_saved', 0),
                "vault_size_bytes": vault_size_bytes,
                "installed_packages": installed_packages,
                "running_packages": running_packages,
                "recent_generations": recent_generations,
                "recent_downloads": recent_downloads,
                "category_distribution": category_distribution,
                "vault_size_warning_gb": vault_size_warning_gb
            })
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    # ── Sprint 9: Vault Import Handler ──────────────────────────────

    def handle_vault_import(self, data):
        """POST /api/vault/import — restore model metadata from exported manifest."""
        manifest = data.get("manifest", [])
        if not manifest:
            self.send_json_response({"status": "error", "message": "No manifest data provided"}, 400)
            return

        try:

            db = _get_db()
            result = db.import_models_metadata(manifest)
            self.send_json_response({
                "status": "success",
                "imported": result["imported"],
                "skipped": result["skipped"],
                "failed": result["failed"],
                "message": f"Imported {result['imported']} models, skipped {result['skipped']} duplicates."
            })
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    # ── Sprint 9: Batch Generation Queue ────────────────────────────

    def handle_batch_generate(self, data):
        """POST /api/generate/batch — add one or more payloads to the batch queue."""
        global _batch_worker_running
        payloads = data.get("payloads", [])
        if not payloads:
            # Single payload shorthand
            payload = data.get("payload")
            if payload:
                payloads = [payload]

        if not payloads:
            self.send_json_response({"status": "error", "message": "No payloads provided"}, 400)
            return

        job_ids = []
        start_worker = False
        with _batch_lock:
            for p in payloads:
                job_id = str(uuid.uuid4())[:8]
                _batch_queue.append({
                    "id": job_id,
                    "status": "pending",
                    "payload": p,
                    "result": None,
                    "error": None,
                    "created_at": time.time()
                })
                job_ids.append(job_id)
            # Atomic check-then-set under lock to prevent double workers
            if not _batch_worker_running:
                _batch_worker_running = True
                start_worker = True

        if start_worker:
            t = threading.Thread(target=self._batch_worker, daemon=False)
            t.start()

        self.send_json_response({
            "status": "success",
            "job_ids": job_ids,
            "queue_length": len(_batch_queue),
            "message": f"Added {len(job_ids)} job(s) to batch queue."
        })

    def handle_batch_queue_status(self):
        """GET /api/generate/queue — returns current batch queue state."""
        with _batch_lock:
            queue_snapshot = [
                {
                    "id": j["id"],
                    "status": j["status"],
                    "prompt": (j.get("payload") or {}).get("prompt", "")[:80],
                    "result": j.get("result"),
                    "error": j.get("error"),
                    "created_at": j.get("created_at", 0)
                }
                for j in _batch_queue
            ]
        self.send_json_response({"status": "success", "queue": queue_snapshot})

    @staticmethod
    def _batch_worker():
        """Background worker that processes batch generation queue sequentially."""
        global _batch_worker_running
        logging.info("Batch generation worker started.")

        while True:
            job = None
            with _batch_lock:
                for j in _batch_queue:
                    if j["status"] == "pending":
                        j["status"] = "running"
                        job = j
                        break

            if not job:
                with _batch_lock:
                    _batch_worker_running = False
                    # Purge completed/failed jobs beyond max history to prevent memory bloat
                    terminal = [j for j in _batch_queue if j["status"] in ("done", "failed")]
                    if len(terminal) > _BATCH_MAX_HISTORY:
                        # Keep only the most recent ones
                        terminal.sort(key=lambda x: x.get("created_at", 0), reverse=True)
                        ids_to_keep = {j["id"] for j in terminal[:_BATCH_MAX_HISTORY]}
                        _batch_queue[:] = [j for j in _batch_queue if j["status"] in ("pending", "running") or j["id"] in ids_to_keep]
                logging.info("Batch generation worker finished — queue empty.")
                break

            try:
                backend = job["payload"].get("backend", "comfyui")
                engine = _ENGINE_CONFIG.get(backend, _ENGINE_CONFIG["comfyui"])
                port = engine["port"]
                translator = engine["translator"]
                base_url = f"http://127.0.0.1:{port}"

                translated = translator(job["payload"])
                # Determine correct endpoint (img2img vs txt2img for A1111/Forge)
                if backend in ("a1111", "forge") and "init_images" in translated:
                    endpoint = "/sdapi/v1/img2img"
                else:
                    endpoint = engine["gen_endpoint"]

                url = f"{base_url}{endpoint}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(translated).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=300) as res:
                    content = json.loads(res.read().decode('utf-8'))

                with _batch_lock:
                    job["status"] = "done"
                    job["result"] = content
                    # Strip base64 images from completed jobs to save memory
                    if isinstance(content, dict) and "images" in content:
                        job["result"] = {k: v for k, v in content.items() if k != "images"}
                        job["result"]["_image_count"] = len(content["images"])
                logging.info(f"Batch job {job['id']} completed.")

            except Exception as e:
                with _batch_lock:
                    job["status"] = "failed"
                    job["error"] = str(e)
                logging.error(f"Batch job {job['id']} failed: {e}")

    # ── Prompt Library Handlers ─────────────────────────────────────


    def handle_list_prompts(self):
        try:
    
            qs = parse_qs(urlparse(self.path).query)
            search = qs.get("search", [None])[0]
            limit = int(qs.get("limit", [100])[0])

            db = _get_db()
            prompts = db.list_prompts(search=search, limit=limit)
            self.send_json_response({"status": "success", "prompts": prompts})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_save_prompt(self, data):
        title = data.get("title", "").strip()
        if not title:
            self.send_json_response({"status": "error", "message": "Title is required"}, 400)
            return
        try:

            db = _get_db()
            row_id = db.save_prompt(
                title=title,
                prompt=data.get("prompt", ""),
                negative=data.get("negative", ""),
                model=data.get("model", ""),
                tags=data.get("tags", ""),
                extra_json=json.dumps(data.get("extra", {})) if data.get("extra") else None
            )
            self.send_json_response({"status": "success", "id": row_id})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_delete_prompt(self, data):
        prompt_id = data.get("id")
        if not prompt_id:
            self.send_json_response({"status": "error", "message": "Missing id"}, 400)
            return
        try:

            db = _get_db()
            db.delete_prompt(prompt_id)
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    # ── Bulk Vault Operations Handler ──────────────────────────────

    # ── Sprint 12: Ollama Prompt Enhancement ──────────────────────────

    def handle_ollama_status(self):
        """GET /api/ollama/status — Check if local Ollama is running"""

        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                self.send_json_response({"online": True, "models": models})
        except Exception:
            self.send_json_response({"online": False, "models": []})

    def handle_ollama_enhance(self, data):
        """POST /api/ollama/enhance — Enhance a prompt using Ollama"""

        prompt = data.get("prompt", "")
        model = data.get("model", "llama3.2")
        
        if not prompt.strip():
            self.send_json_response({"error": "Empty prompt"}, 400)
            return

        system_msg = (
            "You are an expert Stable Diffusion prompt engineer. "
            "Given a user's rough prompt idea, rewrite it as a detailed, high-quality image generation prompt. "
            "Include specific artistic styles, lighting, composition, and quality tags. "
            "Output ONLY the enhanced prompt text, no explanations or markdown. "
            "Keep the prompt under 200 words."
        )
        
        ollama_payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Enhance this prompt for image generation: {prompt}"}
            ],
            "stream": False
        }).encode()
        
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/chat",
                data=ollama_payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                enhanced = result.get("message", {}).get("content", "")
                self.send_json_response({"enhanced_prompt": enhanced.strip()})
        except Exception as e:
            self.send_json_response({"error": f"Ollama request failed: {str(e)}"}, 500)

    def handle_vault_bulk_delete(self, data):
        models = data.get("models", [])
        if not models:
            self.send_json_response({"status": "error", "message": "No models specified"}, 400)
            return

        deleted_count = 0
        failed = []
        filenames_to_remove = []

        for m in models:
            filename = m.get("filename")
            category = m.get("category")
            if not filename or not category:
                failed.append({"filename": filename, "reason": "Missing filename or category"})
                continue
            filepath = os.path.join(self.root_dir, "Global_Vault", category, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    filenames_to_remove.append(filename)
                    deleted_count += 1
                except Exception as e:
                    failed.append({"filename": filename, "reason": str(e)})
            else:
                failed.append({"filename": filename, "reason": "File not found"})

        # Batch remove DB entries
        if filenames_to_remove:
            try:
                db = _get_db()
                db.remove_models_by_filenames(filenames_to_remove)
            except Exception as e:
                logging.error(f"DB cleanup after bulk delete failed: {e}")

        self.send_json_response({
            "status": "success",
            "deleted": deleted_count,
            "failed": failed
        })

    # ── Favorites Handlers (SQLite-backed, replaces settings.json blob) ──
    def handle_get_favorites(self):
        try:
            db = _get_db()
            favs = db.get_all_favorites()
            self.send_json_response(favs)
        except Exception as e:
            logging.error(f"Failed to get favorites: {e}")
            self.send_json_response({})

    def handle_add_favorite(self, data):
        model_id = data.get("model_id")
        model_data = data.get("data", {})
        if not model_id:
            self.send_json_response({"error": "model_id required"}, 400)
            return
        try:
            db = _get_db()
            db.add_favorite(str(model_id), json.dumps(model_data))
            self.send_json_response({"status": "ok"})
        except Exception as e:
            logging.error(f"Failed to add favorite: {e}")
            self.send_json_response({"error": str(e)}, 500)

    def handle_remove_favorite(self, data):
        model_id = data.get("model_id")
        if not model_id:
            self.send_json_response({"error": "model_id required"}, 400)
            return
        try:
            db = _get_db()
            db.remove_favorite(str(model_id))
            self.send_json_response({"status": "ok"})
        except Exception as e:
            logging.error(f"Failed to remove favorite: {e}")
            self.send_json_response({"error": str(e)}, 500)



def start_background_scanners():
    """Starts background scanners and embedding engine"""
    global embedding_process

    # ── One-time favorites migration: settings.json → SQLite ──
    try:
        settings = _get_settings()
        if settings.get("favorites") and not settings.get("favorites_migrated_to_db"):
            favs = settings["favorites"]
            if isinstance(favs, dict) and len(favs) > 0:
                db = _get_db()
                db.bulk_import_favorites(favs)
                # Remove from settings.json to shrink it
                settings.pop("favorites", None)
                settings["favorites_migrated_to_db"] = True
                _save_settings(settings)
                logging.info(f"[MIGRATION] Migrated {len(favs)} favorites from settings.json to SQLite")
    except Exception as e:
        logging.warning(f"[MIGRATION] Favorites migration failed (non-fatal): {e}")

    def _run_scanners():
        global embedding_process
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # --- Embedding Engine ---
            embedding_script = os.path.join(root_dir, ".backend", "embedding_engine.py")
            python_exe = os.path.join(root_dir, "bin", "python", "python.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable

            if os.path.exists(embedding_script):
                print("[SERVER] Booting Embedding Engine (Semantic Indexer)...")
                
                popen_kwargs = {}
                if os.name == 'nt':
                    CREATE_NEW_PROCESS_GROUP = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
                    popen_kwargs['creationflags'] = CREATE_NEW_PROCESS_GROUP
                    
                embedding_process = subprocess.Popen(
                    [python_exe, embedding_script],
                    env=os.environ.copy(),
                    **popen_kwargs
                )
                print(f"[SERVER] Embedding engine started with PID: {embedding_process.pid}")

            # Background Vault and CivitAI Indexing Loop
            # Create scanner instances once, sharing the cached DB singleton
            from vault_crawler import VaultCrawler
            from civitai_client import CivitaiClient
            
            shared_db = _get_db()
            crawler = VaultCrawler(root_dir, db=shared_db)
            civitai = CivitaiClient(root_dir, db=shared_db)
            
            while True:
                try:
                    crawler.crawl()
                    civitai.process_unpopulated_models()
                except Exception as sc_e:
                    print(f"[SERVER] Background scanners iteration error: {sc_e}")
                
                time.sleep(300) # Re-scan every 5 minutes

        except Exception as e:
            print(f"[SERVER] Background scanners thread crashed: {e}")

    t = threading.Thread(target=_run_scanners, daemon=True)
    t.start()
    print("[SERVER] Background scanners thread started.")

def run_server(port=8080):
    global global_http_server
    
    # ── Cold Start Initialization Guard ──
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_sys = os.path.join(root_dir, ".backend")
    if backend_sys not in sys.path:
        sys.path.insert(0, backend_sys)
    try:
        import bootstrap
        bootstrap.main()
    except Exception as e:
        logging.error(f"[SERVER] Pre-flight Bootstrap Failed: {e}")
        
    # Check settings for LAN sharing
    lan_sharing = _get_settings().get("lan_sharing", False)

    host = '0.0.0.0' if lan_sharing else ''
    server_address = (host, port)
    global_http_server = ThreadingHTTPServer(server_address, AIWebServer)
    global_http_server.daemon_threads = True

    if lan_sharing:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
            logging.info(f"LAN sharing enabled — accessible at http://{lan_ip}:{port}")
        except Exception:
            logging.info(f"LAN sharing enabled — accessible at http://0.0.0.0:{port}")
    
    logging.info(f"Starting lightweight Web Server on http://localhost:{port}")
    start_background_scanners()
    try:
        global_http_server.serve_forever()
    except KeyboardInterrupt:
        logging.info("\n[SERVER] KeyboardInterrupt detected. Triggering Teardown...")
        graceful_teardown()
        
    if global_http_server:
        global_http_server.server_close()
    logging.info("Server stopped.")

if __name__ == "__main__":
    run_server()
