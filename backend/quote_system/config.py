# config.py

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, Extra
from typing import Optional

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables and .env file.
    """
    # Allow loading from a .env file
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra fields from environment/dotenv
    )

    # Pricing Configuration
    markup_factor: float = Field(default=1.5, description="Multiplier for base cost to get customer price (>= 1.0)")

    # External Tool Paths
    # If None, the slicer module will attempt auto-detection.
    slicer_path_override: Optional[str] = Field(default=None, alias='PRUSA_SLICER_PATH', description="Optional override path for PrusaSlicer executable.")

    # LLM API Keys (Optional)
    gemini_api_key: Optional[str] = Field(default=None, alias='GEMINI_API_KEY')
    openai_api_key: Optional[str] = Field(default=None, alias='OPENAI_API_KEY')
    anthropic_api_key: Optional[str] = Field(default=None, alias='ANTHROPIC_API_KEY')

    # Logging Configuration
    log_level: str = Field(default='INFO', alias='LOG_LEVEL', description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # Validators
    @validator('markup_factor')
    def markup_must_be_at_least_one(cls, v):
        if v < 1.0:
            raise ValueError('markup_factor must be greater than or equal to 1.0')
        return v

    @validator('log_level')
    def log_level_must_be_valid(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()

# --- Singleton Instance ---
# Create a single instance of the settings to be imported across the application
try:
    settings = Settings()
    # Configure root logger based on settings
    logging.basicConfig(level=settings.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"Configuration loaded successfully. Log level: {settings.log_level}, Markup: {settings.markup_factor}")
    if settings.slicer_path_override:
        logger.info(f"Using Slicer Path Override: {settings.slicer_path_override}")
    # Log if API keys are present without exposing the keys themselves
    if settings.gemini_api_key: logger.info("Gemini API Key detected.")
    if settings.openai_api_key: logger.info("OpenAI API Key detected.")
    if settings.anthropic_api_key: logger.info("Anthropic API Key detected.")

except Exception as e:
    logging.basicConfig(level='INFO', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Default logger
    logger.error(f"CRITICAL: Failed to load application configuration: {e}", exc_info=True)
    # Depending on severity, you might want to exit or provide default settings
    # For now, let's allow continuation with defaults where possible, but log critical error
    settings = Settings() # Attempt to load with defaults
    logger.warning("Continuing with default settings due to configuration load failure.") 