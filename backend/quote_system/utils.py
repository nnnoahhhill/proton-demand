from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path # Use pathlib for easier path manipulation
import json
import os
import re

# Define logger if not already defined (assuming it's configured elsewhere)
import logging
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def get_base_quote_id_py(suffixed_quote_id: Optional[str]) -> Optional[str]:
    """Extracts the base quote ID from a potentially suffixed ID (Python version)."""
    if not suffixed_quote_id:
        return None
    parts = suffixed_quote_id.split('-')
    # Check if the last part looks like a single uppercase letter suffix
    if len(parts) > 2 and len(parts[-1]) == 1 and 'A' <= parts[-1] <= 'Z':
        return '-'.join(parts[:-1])
    # Otherwise, assume it's already the base ID
    return suffixed_quote_id

def find_order_folder_py(base_quote_id: str) -> Optional[str]:
    """Finds the order-specific subfolder in storage/models based on the base quote ID."""
    try:
        # Construct the expected base path
        # Ensure this matches the structure used in lib/storage.ts
        project_root = Path(__file__).resolve().parent.parent.parent # Go up 3 levels from backend/quote_system/utils.py
        models_dir = project_root / "storage" / "models"
        
        if not models_dir.is_dir():
            logger.error(f"Models directory not found at: {models_dir}")
            return None

        logger.info(f"Searching for order folder with base ID '{base_quote_id}' in {models_dir}")
        # Iterate through items in the models directory
        for item in models_dir.iterdir():
            # Check if it's a directory and starts with the base quote ID + hyphen
            if item.is_dir() and item.name.startswith(f"{base_quote_id}-"):
                logger.info(f"Found matching order folder: {item}")
                return str(item) # Return the full path as a string
        
        logger.warning(f"No existing order folder found for base quote ID: {base_quote_id}")
        # Optionally, create the folder here if it MUST exist?
        # For now, just return None if not found.
        return None

    except Exception as e:
        logger.error(f"Error finding order folder for {base_quote_id}: {e}", exc_info=True)
        return None 