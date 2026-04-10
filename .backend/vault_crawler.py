import os
import sys
import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from metadata_db import MetadataDB

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class VaultCrawler:
    """Background worker designed to index massive files optimally and stash references in SQLite.
    
    Optimization: Hashing runs in parallel across 4 threads, but DB writes are
    sequential to prevent SQLite "database is locked" errors under heavy load.
    """
    def __init__(self, root_dir: str, db: 'MetadataDB' = None):
        self.root_dir = os.path.abspath(root_dir)
        self.vault_dir = os.path.join(self.root_dir, "Global_Vault")
        self.db_path = os.path.join(self.root_dir, ".backend", "metadata.sqlite")
        self.db = db or MetadataDB(self.db_path)
        
        # Extensions we care about tracking
        self.valid_extensions = {".safetensors", ".pt", ".ckpt", ".bin"}
        
    def _calculate_hash(self, file_path: str) -> str:
        """Fast calculation of sha256. For massive files (like 6GB checkpoints), 
           we read in chunks."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in 4MB chunks to prevent memory bloat on heavy models
                for chunk in iter(lambda: f.read(4096 * 1024), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logging.error(f"Failed to hash {file_path}: {e}")
            return None

    def _hash_file(self, root: str, filename: str):
        """Hash a single file and return (filename, category, hash) or None.
        Pure CPU work — safe to parallelize."""
        if not any(filename.endswith(ext) for ext in self.valid_extensions):
            return None
            
        file_path = os.path.join(root, filename)
        
        # Ensure we skip ignored files
        if os.path.exists(os.path.join(root, ".manager_ignore")):
             return None
             
        # Determine category based on the immediate folder inside Global_Vault
        rel_path = os.path.relpath(file_path, self.vault_dir)
        category = rel_path.split(os.sep)[0] if os.sep in rel_path else "misc"
        
        logging.info(f"Hashing new file: {filename}...")
        file_hash = self._calculate_hash(file_path)
        if file_hash:
            return (filename, category, file_hash)
        return None

    def crawl(self):
        logging.info(f"Starting Vault Crawl in {self.vault_dir}")
        if not os.path.exists(self.vault_dir):
            logging.warning("Vault directory missing; nothing to crawl.")
            return

        tracked_files = self.db.get_all_filenames()
        
        # Collect files needing hashing
        files_to_hash = []
        for root, _, files in os.walk(self.vault_dir):
            for file in files:
                if file not in tracked_files:
                    files_to_hash.append((root, file))
        
        if not files_to_hash:
            logging.info("Vault Crawl Complete — no new files.")
            return
        
        logging.info(f"Found {len(files_to_hash)} new files to index.")
        
        # Phase 1: Hash in parallel (CPU-bound, safe to parallelize)
        hash_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self._hash_file, root, file) for root, file in files_to_hash]
            for future in futures:
                result = future.result()
                if result:
                    hash_results.append(result)
        
        # Phase 2: Write to DB sequentially (prevents "database is locked" errors)
        for filename, category, file_hash in hash_results:
            try:
                self.db.insert_or_update_model(
                    filename=filename,
                    vault_category=category,
                    file_hash=file_hash
                )
                logging.info(f"Registered {filename} [{file_hash[:8]}] in database.")
            except Exception as e:
                logging.error(f"Failed to register {filename}: {e}")

        # Update vault size cache for dashboard
        try:
            vault_size = 0
            for root, _, files in os.walk(self.vault_dir):
                for f in files:
                    try:
                        vault_size += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
            # Write to the shared cache used by server.py handle_server_status
            if hasattr(sys.modules.get('server', None), '_vault_size_cache'):
                sys.modules['server']._vault_size_cache["size"] = vault_size
                sys.modules['server']._vault_size_cache["expires"] = time.time() + 300
        except Exception:
            pass  # Non-critical — dashboard will compute its own fallback

        logging.info(f"Vault Crawl Complete. Indexed {len(hash_results)} new files.")

if __name__ == "__main__":
    crawler = VaultCrawler(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    crawler.crawl()
