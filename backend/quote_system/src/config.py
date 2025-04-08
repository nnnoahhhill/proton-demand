# src/config.py

import os
import logging
from dotenv import load_dotenv
from typing import Optional

logger = logging.getLogger(__name__)

# --- Environment Loading --- #

def load_environment(env_file: Optional[str] = ".env") -> bool:
    """
    Loads environment variables from a .env file.

    Searches for the file in the current directory or parent directories.

    Args:
        env_file: The name of the environment file (e.g., ".env", ".env.local").

    Returns:
        True if a .env file was found and loaded, False otherwise.
    """
    # find_dotenv will search current dir and parent dirs
    env_path = find_dotenv(filename=env_file, raise_error_if_not_found=False)
    if env_path:
        logger.info(f"Loading environment variables from: {env_path}")
        return load_dotenv(dotenv_path=env_path, verbose=True)
    else:
        logger.warning(f"No '{env_file}' file found. Relying on system environment variables.")
        return False

# Load environment on import (call the function)
# We need find_dotenv for this pattern
# As find_dotenv is not available, we'll try a simpler approach:
# Look for .env in the current working directory or the script's directory
def load_env_simple(filename=".env"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # Assuming config.py is in src/
    env_path_project = os.path.join(project_root, filename)
    env_path_cwd = os.path.join(os.getcwd(), filename)

    loaded = False
    if os.path.exists(env_path_project):
        logger.info(f"Loading environment variables from: {env_path_project}")
        loaded = load_dotenv(dotenv_path=env_path_project, verbose=True)
    elif os.path.exists(env_path_cwd):
         logger.info(f"Loading environment variables from: {env_path_cwd}")
         loaded = load_dotenv(dotenv_path=env_path_cwd, verbose=True)
    else:
        logger.warning(f"No '{filename}' file found in project root ({project_root}) or CWD ({os.getcwd()}). Relying on system environment variables.")

    return loaded

ENV_LOADED = load_env_simple()

# --- Application Settings --- #

class AppSettings:
    """Holds application-wide configuration settings."""
    # General
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # API specific
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    # Set a secret key for security features if needed (e.g., JWT)
    # SECRET_KEY: str = os.getenv("SECRET_KEY", "a_default_insecure_secret_key")

    # File Handling
    TEMP_DIR: str = os.getenv("TEMP_DIR", tempfile.gettempdir())
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # Slicer configuration (Example - adjust based on actual slicer needs)
    # Path can be absolute or relative (searched in PATH)
    PRUSA_SLICER_PATH: Optional[str] = os.getenv("PRUSA_SLICER_PATH")
    # CURA_ENGINE_PATH: Optional[str] = os.getenv("CURA_ENGINE_PATH") # Example for Cura

    # Add other configurations as needed
    # e.g., DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    # e.g., EXTERNAL_SERVICE_API_KEY: Optional[str] = os.getenv("EXTERNAL_SERVICE_API_KEY")

    def __init__(self):
        # Validate or process settings after loading if necessary
        self._validate_log_level()

    def _validate_log_level(self):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL not in valid_levels:
            logger.warning(f"Invalid LOG_LEVEL '{self.LOG_LEVEL}' specified. Defaulting to INFO.")
            self.LOG_LEVEL = "INFO"

    @property
    def slicer_path(self) -> Optional[str]:
        """Returns the first configured slicer path found."""
        # Prioritize PrusaSlicer if set, add others as needed
        if self.PRUSA_SLICER_PATH:
            return self.PRUSA_SLICER_PATH
        # if self.CURA_ENGINE_PATH:
        #     return self.CURA_ENGINE_PATH
        logger.warning("No specific slicer path configured in environment (e.g., PRUSA_SLICER_PATH).")
        return None

# --- Singleton Instance --- #
# Create a single instance of the settings to be imported across the application
settings = AppSettings()

# --- Helper Function (Optional) --- #
def get_settings() -> AppSettings:
    """Returns the singleton settings instance."""
    return settings

# Need these imports for the code above
import tempfile
from dotenv import find_dotenv # Requires python-dotenv to be installed 