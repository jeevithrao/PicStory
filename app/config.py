# app/config.py
# Loads all environment variables from .env
# Access settings anywhere via: from app.config import settings

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file automatically

class Settings:
    # Database
    DB_HOST: str     = os.getenv("DB_HOST", "localhost")
    DB_PORT: int     = int(os.getenv("DB_PORT", 3306))
    DB_USER: str     = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str     = os.getenv("DB_NAME", "picstory")

    # API Keys
    GEMINI_API_KEY:    str = os.getenv("GEMINI_API_KEY", "")
    FREESOUND_API_KEY: str = os.getenv("FREESOUND_API_KEY", "")

    # Mode
    USE_LOCAL_MODELS: bool = os.getenv("USE_LOCAL_MODELS", "false").lower() == "true"

    # File Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")
    MAX_IMAGES:  int = int(os.getenv("MAX_IMAGES_PER_ZIP", 8))

    # 22 Scheduled Indian languages
    SUPPORTED_LANGUAGES: list = [
        "hi",   # Hindi
        "kok",  # Konkani
        "kn",   # Kannada
        "doi",  # Dogri
        "brx",  # Bodo
        "ur",   # Urdu
        "ta",   # Tamil
        "ks",   # Kashmiri
        "as",   # Assamese
        "bn",   # Bengali
        "mr",   # Marathi
        "sd",   # Sindhi
        "mai",  # Maithili
        "pa",   # Punjabi
        "ml",   # Malayalam
        "mni",  # Manipuri
        "te",   # Telugu
        "sa",   # Sanskrit
        "ne",   # Nepali
        "sat",  # Santali
        "gu",   # Gujarati
        "or",   # Odia
    ]

settings = Settings()