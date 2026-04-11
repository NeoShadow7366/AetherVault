"""Vault domain handlers — search, tags, export, import, health, repair, bulk delete.

Mixin class providing vault-related HTTP handler methods.
Composed into AIWebServer via multiple inheritance.
"""
import os
import sys
import json
import time
import shutil
import logging
import zipfile
import io


class VaultHandlersMixin:
    """Vault domain handlers for the AIWebServer class.

    Handles:
        GET  /api/vault/search     → handle_vault_search
        GET  /api/vault/tags       → handle_get_all_tags
        GET  /api/hf/search        → handle_hf_search
        POST /api/vault/tag/add    → handle_add_tag
        POST /api/vault/tag/remove → handle_remove_tag
        POST /api/vault/export     → handle_vault_export
        POST /api/vault/import     → handle_vault_import
        POST /api/vault/updates    → handle_vault_updates
        POST /api/vault/health_check → handle_vault_health_check
        POST /api/vault/repair     → handle_vault_repair
        POST /api/vault/import_scan → handle_import_scan
        POST /api/vault/bulk_delete → handle_vault_bulk_delete
        POST /api/import/external  → handle_import_external
        GET  /api/favorites        → handle_get_favorites
        POST /api/favorites/add    → handle_add_favorite
        POST /api/favorites/remove → handle_remove_favorite
    """

    def handle_vault_search(self):
        try:
            from server import _get_db
            from urllib.parse import urlparse, parse_qs
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
                if score < 0.1:
                    continue
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
            from server import _get_db
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
            from server import _get_db
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
            from server import _get_db
            db = _get_db()
            db.remove_user_tag(hash_val, tag.strip())
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_hf_search(self):
        from urllib.parse import urlparse, parse_qs
        from server import _get_settings
        qs = parse_qs(urlparse(self.path).query)
        query = qs.get("query", [""])[0]
        type_filter = qs.get("type", [""])[0]
        limit = int(qs.get("limit", [40])[0])
        offset = int(qs.get("offset", [0])[0])

        filter_tags = None
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

    def handle_vault_updates(self, data):
        updater_script = os.path.join(self.root_dir, ".backend", "update_checker.py")
        python_exe = sys.executable
        try:
            import subprocess
            subprocess.Popen([python_exe, updater_script, "--root_dir", self.root_dir])
            self.send_json_response({"status": "success", "message": "Update check started in background."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_vault_health_check(self, data):
        """Checks vault symlinks/junctions in installed packages for broken targets."""
        from server import _get_db
        broken_links = 0
        packages_dir = os.path.join(self.root_dir, "packages")
        vault_dir = os.path.join(self.root_dir, "Global_Vault")

        if not os.path.exists(packages_dir):
            self.send_json_response({"status": "success", "message": "No packages installed."})
            return

        for pkg_name in os.listdir(packages_dir):
            pkg_path = os.path.join(packages_dir, pkg_name)
            if not os.path.isdir(pkg_path):
                continue
            for root, dirs, _ in os.walk(pkg_path):
                for d in dirs:
                    full = os.path.join(root, d)
                    if os.path.islink(full) or (os.name == 'nt' and os.path.isdir(full)):
                        try:
                            target = os.path.realpath(full)
                            if not os.path.exists(target):
                                broken_links += 1
                                # Attempt repair: re-point to vault equivalent
                                vault_equiv = os.path.join(vault_dir, d)
                                if os.path.exists(vault_equiv):
                                    try:
                                        from symlink_manager import create_safe_directory_link
                                        os.rmdir(full)
                                        create_safe_directory_link(vault_equiv, full)
                                    except Exception:
                                        pass
                        except Exception:
                            pass

        self.send_json_response({"status": "success", "message": f"Repaired {broken_links} broken symlinks/junctions in packages."})

    def handle_vault_repair(self, data):
        """POST /api/vault/repair — re-fetch metadata + thumbnails for a model.
        Accepts file_hash directly, or falls back to filename-based lookup."""
        from server import _get_db, _get_settings
        file_hash = data.get("file_hash")
        filename = data.get("filename")

        db = _get_db()

        if not file_hash and filename:
            model = db.get_model_by_filename(filename)
            if model:
                file_hash = model.get("file_hash")

        if not file_hash:
            self.send_json_response({"status": "error", "message": "Missing file_hash and unable to resolve from filename"}, 400)
            return

        try:
            from civitai_client import CivitaiClient
            settings = _get_settings()
            api_key = settings.get("civitai_api_key", "")
            client = CivitaiClient(db, api_key=api_key, root_dir=self.root_dir)
            client.fetch_and_store(file_hash)
            self.send_json_response({"status": "success", "message": f"Metadata refreshed for {file_hash[:12]}..."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_import_scan(self, data):
        try:
            from server import _get_db
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
        from server import _get_db
        filenames = data.get("filenames", [])
        include_files = data.get("include_files", False)

        if not filenames:
            self.send_json_response({"status": "error", "message": "No filenames specified"}, 400)
            return

        try:
            db = _get_db()
            manifest = db.export_models_metadata(filenames)

            if not include_files:
                self.send_json_response({
                    "status": "success",
                    "manifest": manifest,
                    "export_type": "metadata_only"
                })
                return

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                zf.writestr('vault_manifest.json', json.dumps(manifest, indent=2, default=str))
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

    def handle_vault_import(self, data):
        """POST /api/vault/import — import models from a metadata manifest."""
        from server import _get_db
        manifest = data.get("manifest", [])
        if not manifest:
            self.send_json_response({"status": "error", "message": "Empty manifest"}, 400)
            return
        try:
            db = _get_db()
            imported = db.import_models_metadata(manifest)
            self.send_json_response({"status": "success", "imported": imported})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_vault_bulk_delete(self, data):
        from server import _get_db
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

    def handle_import_external(self, data):
        from symlink_manager import create_safe_directory_link
        target_path = data.get("path")
        if not target_path or not os.path.exists(target_path) or not os.path.isdir(target_path):
            self.send_json_response({"status": "error", "message": "Invalid directory provided"}, 400)
            return
        try:
            folder_name = os.path.basename(os.path.abspath(target_path)).replace(" ", "_")
            if not folder_name:
                folder_name = "External_Import"
            vault_dir = os.path.join(self.root_dir, "Global_Vault", f"External_{folder_name}")
            os.makedirs(vault_dir, exist_ok=True)
            try:
                create_safe_directory_link(target_path, os.path.join(vault_dir, "Models"))
                self.send_json_response({"status": "success"})
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, 500)
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_get_favorites(self):
        try:
            from server import _get_db
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
            from server import _get_db
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
            from server import _get_db
            db = _get_db()
            db.remove_favorite(str(model_id))
            self.send_json_response({"status": "ok"})
        except Exception as e:
            logging.error(f"Failed to remove favorite: {e}")
            self.send_json_response({"error": str(e)}, 500)
