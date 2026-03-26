import os
import sys
import json
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Ensure we can import our modules
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from metadata_db import MetadataDB

db_path = os.path.join(ROOT_DIR, 'metadata.sqlite')
db = MetadataDB(db_path)

def check_for_updates():
    logging.info("Checking for model updates via CivitAI API...")
    models = db.get_models_for_update_check()
    
    # Optional: fetch user's CivitAI API key if available
    # but base info doesn't strictly need it unless model is early access/hidden
    api_key_path = os.path.join(ROOT_DIR, 'settings.json')
    api_key = ""
    if os.path.exists(api_key_path):
        try:
            with open(api_key_path, 'r') as f:
                settings = json.load(f)
                api_key = settings.get("civitai_api_key", "")
        except:
            pass
            
    headers = {"Content-Type": "application/json"}
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
        except Exception as e:
            continue

    updates_found = 0
    
    for model_id, items in model_groups.items():
        try:
            url = f"https://civitai.com/api/v1/models/{model_id}"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                versions = data.get("modelVersions", [])
                if not versions: continue
                # The first item in modelVersions is the highest/newest by CivitAI standards
                latest_version = versions[0]
                latest_version_id = latest_version.get("id")
                
                # Compare against all our installed files for this model
                for item in items:
                    v_id = item["version_id"]
                    # If the latest is physically different from what we crawled as this file's version
                    # (and assume IDs increment over time)
                    if latest_version_id and latest_version_id != v_id:
                        db.set_model_update_status(item["file_hash"], 1, latest_version_id)
                        updates_found += 1
                        logging.info(f"Update available for model #{model_id}: v{v_id} -> v{latest_version_id}")
                    else:
                        db.set_model_update_status(item["file_hash"], 0, None)
            
            # Rate limit politeness
            time.sleep(1.0)
        except Exception as e:
            logging.warning(f"Error checking model {model_id} for updates: {e}")

    logging.info(f"Update check complete. {updates_found} updates found.")

if __name__ == "__main__":
    check_for_updates()
