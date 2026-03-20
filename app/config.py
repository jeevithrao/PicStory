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

    # File Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")
    MAX_IMAGES:  int = int(os.getenv("MAX_IMAGES_PER_ZIP", 20))

    # Supported Indian language codes (ISO 639-1 / BCP-47)
    SUPPORTED_LANGUAGES: list = [
        "as",   # Assamese
        "bn",   # Bengali
        "gu",   # Gujarati
        "hi",   # Hindi
        "kn",   # Kannada
        "ks",   # Kashmiri
        "kok",  # Konkani
        "mai",  # Maithili
        "ml",   # Malayalam
        "mni",  # Manipuri
        "mr",   # Marathi
        "ne",   # Nepali
        "or",   # Odia
        "pa",   # Punjabi
        "sa",   # Sanskrit
        "sat",  # Santali
        "sd",   # Sindhi
        "si",   # Sinhala
        "ta",   # Tamil
        "te",   # Telugu
        "ur",   # Urdu
        "brx",  # Bodo
    ]

settings = Settings()
