"""Proxy domain handlers — ComfyUI, A1111, Forge, Fooocus engine proxying.

Mixin class providing inference proxy HTTP handler methods.
Composed into AIWebServer via multiple inheritance.
"""
import os
import json
import base64
import logging
import urllib.request


class ProxyHandlersMixin:
    """Proxy domain handlers for the AIWebServer class.

    Handles:
        POST /api/comfy_proxy    → handle_comfy_proxy
        GET  /api/comfy/image    → handle_comfy_image
        POST /api/comfy/upload   → handle_comfy_upload
        POST /api/a1111_proxy    → handle_a1111_proxy
        POST /api/forge_proxy    → handle_forge_proxy
        POST /api/fooocus_proxy  → handle_fooocus_proxy
    """

    def handle_comfy_proxy(self, data):
        from server import _ENGINE_CONFIG, AIWebServer
        from proxy_translators import build_comfy_workflow
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
                p = entry.get("process") if entry else None
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
        """Proxy raw image bytes from ComfyUI."""
        from urllib.parse import urlparse
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
            body = self.rfile.read(length)

            url = "http://127.0.0.1:8188/upload/image"
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
        from server import _ENGINE_CONFIG
        config = _ENGINE_CONFIG.get(engine_name)
        if not config:
            self.send_json_response({"error": f"Unknown engine: {engine_name}"}, 400)
            return

        payload = data.get("payload")
        endpoint = data.get("endpoint", config["gen_endpoint"])

        if endpoint == "/api/generate" and payload:
            try:
                payload = config["translator"](payload)
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
