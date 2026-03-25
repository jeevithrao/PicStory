# app/services/translation_service.py
# Translation service using Gemini API.
# Translates between English and 22 Indian languages.
# No local model downloads needed — uses the same GEMINI_API_KEY already in .env.

import google.generativeai as genai
from app.config import settings

# Language display names
LANG_NAMES = {
    "hi": "Hindi", "kok": "Konkani", "kn": "Kannada", "doi": "Dogri",
    "brx": "Bodo", "ur": "Urdu", "ta": "Tamil", "ks": "Kashmiri",
    "as": "Assamese", "bn": "Bengali", "mr": "Marathi", "sd": "Sindhi",
    "mai": "Maithili", "pa": "Punjabi", "ml": "Malayalam", "mni": "Manipuri",
    "te": "Telugu", "sa": "Sanskrit", "ne": "Nepali", "sat": "Santali",
    "gu": "Gujarati", "or": "Odia",
}

_configured = False


def _ensure_configured():
    """Configure the Gemini SDK once."""
    global _configured
    if not _configured:
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_key_here":
            raise ValueError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=api_key)
        _configured = True


def translate_text(text: str, target_language: str) -> str:
    """
    Translate a single English string to the target Indian language.
    Falls back to original English if translation fails.
    """
    if target_language == "en" or not text.strip():
        return text

    lang_name = LANG_NAMES.get(target_language)
    if not lang_name:
        print(f"⚠️  Unknown language code '{target_language}'. Returning English.")
        return text

    try:
        _ensure_configured()
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"Translate the following English text into {lang_name}. Output ONLY the translated text, nothing else.\n\nText: {text}"
        response = model.generate_content(prompt)
        translated = response.text.strip()
        return translated if translated else text
    except Exception as e:
        print(f"⚠️  Translation error: {e}. Returning English.")
        return text


def translate_batch(texts: list[str], target_language: str) -> list[str]:
    """Translate a list of English strings to the target language."""
    if target_language == "en":
        return texts

    lang_name = LANG_NAMES.get(target_language, "Hindi")

    try:
        _ensure_configured()
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Batch all captions in one API call for efficiency
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        prompt = f"""Translate each of the following English sentences into {lang_name}.
Keep the numbered format. Output ONLY the translated sentences with their numbers, nothing else.

{numbered}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Parse numbered lines
        import re
        lines = re.findall(r'\d+\.\s*(.+)', raw)

        if len(lines) == len(texts):
            return lines
        else:
            # Fallback: translate one by one
            return [translate_text(t, target_language) for t in texts]

    except Exception as e:
        print(f"⚠️  Batch translation failed: {e}. Returning English.")
        return texts


def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate from an Indian language to English.
    Used in Mode 2 to normalize the user's prompt before SD generation.
    """
    if source_language == "en" or not text.strip():
        return text

    lang_name = LANG_NAMES.get(source_language)
    if not lang_name:
        print(f"⚠️  Unknown language code '{source_language}'. Returning original text.")
        return text

    try:
        _ensure_configured()
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"Translate the following {lang_name} text into English. Output ONLY the English translation, nothing else.\n\nText: {text}"
        response = model.generate_content(prompt)
        translated = response.text.strip()
        print(f"🌐 Translated '{text}' → '{translated}'")
        return translated if translated else text
    except Exception as e:
        print(f"⚠️  Translation to English failed: {e}. Returning original text.")
        return text
