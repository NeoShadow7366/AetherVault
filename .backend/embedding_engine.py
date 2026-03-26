import os
import json
import logging
from sentence_transformers import SentenceTransformer
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class EmbeddingEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._model = None
        
    @property
    def model(self):
        if self._model is None:
            logging.info("Loading sentence-transformers model (all-MiniLM-L6-v2) - this takes ~80MB...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def embed_text(self, text: str):
        return self.model.encode(text).tolist()

    def generate_missing_embeddings(self):
        import sqlite3
        from metadata_db import MetadataDB
        db = MetadataDB(self.db_path)
        unembedded = db.get_models_unembedded()
        
        if not unembedded:
            return 0
            
        logging.info(f"Found {len(unembedded)} models missing embeddings. Processing...")
        processed = 0
        for model in unembedded:
            try:
                parts = [model['filename'], model['vault_category']]
                metadata = {}
                if model.get('metadata_json'):
                    metadata = json.loads(model['metadata_json'])
                
                if 'baseModel' in metadata:
                    parts.append(metadata['baseModel'])
                if 'tags' in metadata:
                    parts.extend(metadata['tags'])
                
                user_tags = db.get_user_tags(model['file_hash'])
                parts.extend(user_tags)
                
                text_to_embed = " ".join([str(p) for p in parts if p]).replace("_", " ").lower()
                vector = self.embed_text(text_to_embed)
                
                db.save_embedding(model['file_hash'], json.dumps(vector))
                processed += 1
            except Exception as e:
                logging.error(f"Error embedding {model['filename']}: {e}")
                
        return processed

    def search(self, query: str, top_k: int = 20):
        # Allow natural language via semantic match
        query_vector = self.embed_text(query)
        from metadata_db import MetadataDB
        db = MetadataDB(self.db_path)
        embeddings = db.get_all_embeddings()
        
        if not embeddings:
            return []
            
        import math
        def cosine_similarity(v1, v2):
            dot = sum(a*b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a*a for a in v1))
            norm2 = math.sqrt(sum(b*b for b in v2))
            if norm1 == 0 or norm2 == 0: return 0
            return dot / (norm1 * norm2)

        results = []
        for emb in embeddings:
            try:
                vec = json.loads(emb['vector_json'])
                score = cosine_similarity(query_vector, vec)
                results.append((score, emb['file_hash']))
            except Exception:
                continue
                
        results.sort(reverse=True, key=lambda x: x[0])
        # Return tuples of (hash, score)
        return results[:top_k]

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".backend", "metadata.sqlite")
    engine = EmbeddingEngine(db_file)
    while True:
        try:
            processed = engine.generate_missing_embeddings()
            if processed > 0:
                logging.info(f"Embedded {processed} models in background run.")
        except Exception as e:
            logging.error(f"Embedding Engine Error: {e}")
        time.sleep(60) # Run every minute
