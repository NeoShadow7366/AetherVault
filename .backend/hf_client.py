import urllib.request
import urllib.parse
import json
import os

class HFClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://huggingface.co/api"

    def search_models(self, query=None, filter_tags=None, sort="downloads", direction=-1, limit=20):
        url = f"{self.base_url}/models?"
        params = []
        if query:
            params.append(f"search={urllib.parse.quote(str(query))}")
        if filter_tags:
            if isinstance(filter_tags, list):
                for tag in filter_tags:
                    params.append(f"filter={urllib.parse.quote(str(tag))}")
            else:
                params.append(f"filter={urllib.parse.quote(str(filter_tags))}")
        
        params.append(f"sort={str(sort)}")
        if direction == -1:
            params.append("direction=-1")
        params.append(f"limit={str(limit)}")
        params.append("full=True") # Get metadata
        
        final_url = url + "&".join(params)
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            req = urllib.request.Request(final_url, headers=headers)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode('utf-8'))
                return self.format_results(data)
        except Exception as e:
            print(f"HF Search Error: {e}")
            return []

    def format_results(self, raw_data):
        formatted = []
        for item in raw_data:
            model_id = item.get("modelId")
            # Extract basic info
            tags = item.get("tags", [])
            downloads = item.get("downloads", 0)
            likes = item.get("likes", 0)
            
            # Find the best sibling file (usually .safetensors)
            siblings = item.get("siblings", [])
            primary_file = None
            for s in siblings:
                if s.get("rfilename", "").endswith(".safetensors"):
                    primary_file = s.get("rfilename")
                    break
            if not primary_file and siblings:
                primary_file = siblings[0].get("rfilename")

            # Try to find a preview image (HF doesn't have a direct "thumbnail" API for search,
            # but sometimes there's a README image or we can use a generic icon)
            thumb = f"https://huggingface.co/front/assets/huggingface_logo-noborder.svg"

            short_tags = []
            for t in tags:
                if len(str(t)) < 15:
                    short_tags.append(str(t))
                if len(short_tags) >= 5:
                    break

            formatted.append({
                "id": model_id,
                "name": model_id.split("/")[-1],
                "creator": {"username": model_id.split("/")[0]},
                "description": item.get("id"),
                "stats": {"downloadCount": downloads, "rating": likes},
                "tags": short_tags,
                "modelVersions": [{
                    "id": model_id,
                    "name": "Main",
                    "files": [{
                        "name": primary_file,
                        "downloadUrl": f"https://huggingface.co/{model_id}/resolve/main/{primary_file}" if primary_file else None
                    }] if primary_file else [],
                    "images": [{"url": thumb}],
                    "baseModel": self.infer_base_model(tags)
                }]
            })
        return formatted

    def infer_base_model(self, tags):
        for t in tags:
            if "sdxl" in t.lower(): return "SDXL 1.0"
            if "sd15" in t.lower() or "stable-diffusion-v1-5" in t.lower(): return "SD 1.5"
            if "flux" in t.lower(): return "Flux.1"
        return "Unknown"

if __name__ == "__main__":
    client = HFClient()
    results = client.search_models(query="flux", limit=5)
    print(json.dumps(results, indent=2))
