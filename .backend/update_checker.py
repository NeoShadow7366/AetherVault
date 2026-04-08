import os
import sys
import json
import time
import logging
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Ensure we can import our modules
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from metadata_db import MetadataDB

db_path = os.path.join(BACKEND_DIR, 'metadata.sqlite')
db = MetadataDB(db_path)

def check_for_updates():
    logging.info("Checking for model updates via CivitAI API...")
    models = db.get_models_for_update_check()
    
    # Optional: fetch user's CivitAI API key if available
    api_key_path = os.path.join(BACKEND_DIR, 'settings.json')
    api_key = ""
    if os.path.exists(api_key_path):
        try:
            with open(api_key_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                api_key = settings.get("civitai_api_key", "")
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to read settings for API key: {e}")
            
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AIManager/1.0"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Group by modelId to avoid redundant requests if multiple versions of same model exist
    model_groups = {}
    for row in models:
        try:
            meta = json.loads(row['metadata_json'])
            model_id = meta.get('modelId')
            version_id = meta.get('id')
            if model_id and version_id:
                if model_id not in model_groups:
                    model_groups[model_id] = []
                model_groups[model_id].append({
                    "file_hash": row['file_hash'],
                    "version_id": version_id
                })
        except Exception:
            continue

    updates_found = 0
    
    for model_id, items in model_groups.items():
        try:
            url = f"https://civitai.com/api/v1/models/{model_id}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    versions = data.get("modelVersions", [])
                    if not versions:
                        continue
                    # The first item in modelVersions is the highest/newest by CivitAI standards
                    latest_version = versions[0]
                    latest_version_id = latest_version.get("id")
                    
                    # Compare against all our installed files for this model
                    for item in items:
                        v_id = item["version_id"]
                        if latest_version_id and latest_version_id != v_id:
                            db.set_model_update_status(item["file_hash"], 1, latest_version_id)
                            updates_found += 1
                            logging.info(f"Update available for model #{model_id}: v{v_id} -> v{latest_version_id}")
                        else:
                            db.set_model_update_status(item["file_hash"], 0, None)
            
            # Rate limit politeness
            time.sleep(1.0)
        except urllib.error.HTTPError as e:
            logging.warning(f"HTTP error checking model {model_id}: {e.code}")
        except Exception as e:
            logging.warning(f"Error checking model {model_id} for updates: {e}")

    logging.info(f"Update check complete. {updates_found} updates found.")

if __name__ == "__main__":
    check_for_updates()
