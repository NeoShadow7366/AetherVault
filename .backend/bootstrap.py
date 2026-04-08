import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    logging.info("Executing Python bootstrap step...")
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logging.info(f"Project root identified as: {root_dir}")
    
    # Initialize all Global Vault subdirectories
    vault_dirs = [
        "checkpoints", "loras", "vaes", "controlnet",
        "unet", "clip", "text_encoders", "embeddings",
        "upscalers", "motion", "hypernetworks", "misc"
    ]
    for d in vault_dirs:
        target_dir = os.path.join(root_dir, "Global_Vault", d)
        os.makedirs(target_dir, exist_ok=True)
        logging.info(f"Initialized vault directory: {target_dir}")
    
    # Initialize cache directory for thumbnails
    cache_dir = os.path.join(root_dir, ".backend", "cache", "thumbnails")
    os.makedirs(cache_dir, exist_ok=True)
    logging.info(f"Initialized cache directory: {cache_dir}")
    
    # Initialize packages directory
    packages_dir = os.path.join(root_dir, "packages")
    os.makedirs(packages_dir, exist_ok=True)
    logging.info(f"Initialized packages directory: {packages_dir}")
    
    # Initialize database (creates tables if missing)
    try:
        sys.path.insert(0, os.path.join(root_dir, ".backend"))
        from metadata_db import MetadataDB
        db_path = os.path.join(root_dir, ".backend", "metadata.sqlite")
        MetadataDB(db_path)
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        
    logging.info("Project directory mapping initialized successfully.")

if __name__ == "__main__":
    main()
