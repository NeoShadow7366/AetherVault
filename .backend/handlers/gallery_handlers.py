"""Gallery domain handlers — My Creations gallery CRUD, ratings, and tags.

Mixin class that provides gallery-related HTTP handler methods.
Composed into AIWebServer via multiple inheritance.
"""
import os
import json
import logging


class GalleryHandlersMixin:
    """Gallery domain handlers for the AIWebServer class.
    
    Assumes 'self' has:
        - send_json_response(data, status)
        - root_dir
        - _get_db() available at module level
    
    Handles:
        GET  /api/gallery       → handle_gallery_list
        GET  /api/gallery/tags  → handle_gallery_tags
        POST /api/gallery/save  → handle_gallery_save
        POST /api/gallery/delete → handle_gallery_delete
        POST /api/gallery/rate  → handle_gallery_rate
    """

    def handle_gallery_list(self):
        """GET /api/gallery — list generations with self-healing for stale entries."""
        try:
            from server import _get_db
            from urllib.parse import urlparse, parse_qs
            db = _get_db()
            qs = parse_qs(urlparse(self.path).query)
            sort = qs.get("sort", ["newest"])[0]
            tag = qs.get("tag", [""])[0]
            
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
            from server import _get_db
            db = _get_db()
            tags = db.get_gallery_tags()
            self.send_json_response({"status": "success", "tags": tags})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_save(self, data):
        """POST /api/gallery/save — save a generation to the gallery."""
        try:
            from server import _get_db
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
        """POST /api/gallery/delete — remove a generation."""
        gen_id = data.get("id")
        if not gen_id:
            self.send_json_response({"status": "error", "message": "Missing id"}, 400)
            return
        try:
            from server import _get_db
            db = _get_db()
            db.delete_generation(gen_id)
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

    def handle_gallery_rate(self, data):
        """POST /api/gallery/rate — rate a generation."""
        gen_id = data.get("id")
        rating = data.get("rating", 0)
        if not gen_id:
            self.send_json_response({"status": "error", "message": "Missing id"}, 400)
            return
        try:
            from server import _get_db
            db = _get_db()
            db.rate_generation(gen_id, rating)
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)
