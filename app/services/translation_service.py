# app/services/translation_service.py
# Wraps IndicTrans2 for English → Indian language translation.
# Runs on CPU — no GPU needed for this model.

# NOTE: IndicTrans2 requires its own installation:
#   pip install git+https://github.com/AI4Bharat/IndicTrans2.git
# If not installed, falls back to returning the original English text.

# Language code mapping: our BCP-47 codes → IndicTrans2 language codes
LANG_CODE_MAP = {
    "as":  "asm_Beng",   # Assamese
    "bn":  "ben_Beng",   # Bengali
    "gu":  "guj_Gujr",   # Gujarati
    "hi":  "hin_Deva",   # Hindi
    "kn":  "kan_Knda",   # Kannada
    "ks":  "kas_Arab",   # Kashmiri
    "kok": "kok_Deva",   # Konkani
    "mai": "mai_Deva",   # Maithili
    "ml":  "mal_Mlym",   # Malayalam
    "mni": "mni_Mtei",   # Manipuri
    "mr":  "mar_Deva",   # Marathi
    "ne":  "npi_Deva",   # Nepali
    "or":  "ory_Orya",   # Odia
    "pa":  "pan_Guru",   # Punjabi
    "sa":  "san_Deva",   # Sanskrit
    "sat": "sat_Olck",   # Santali
    "sd":  "snd_Arab",   # Sindhi
    "ta":  "tam_Taml",   # Tamil
    "te":  "tel_Telu",   # Telugu
    "ur":  "urd_Arab",   # Urdu
    "brx": "brx_Deva",   # Bodo
    "si":  "sin_Sinh",   # Sinhala
    "en":  "eng_Latn",   # English (source)
}

_indic_model    = None
_indic_tokenizer = None


def _load_indic_trans():
    """Lazy-load IndicTrans2 on first use (CPU only)."""
    global _indic_model, _indic_tokenizer
    if _indic_model is not None:
        return True
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        _indic_tokenizer = AutoTokenizer.from_pretrained(
            "ai4bharat/indictrans2-en-indic-1B", trust_remote_code=True
        )
        _indic_model = AutoModelForSeq2SeqLM.from_pretrained(
            "ai4bharat/indictrans2-en-indic-1B", trust_remote_code=True
        )
        print("✅ IndicTrans2 loaded on CPU.")
        return True
    except Exception as e:
        print(f"⚠️  IndicTrans2 not available: {e}. Using English fallback.")
        return False


def translate_text(text: str, target_language: str) -> str:
    """
    Translate a single English string to the target Indian language.
    Falls back to original English if translation fails.
    """
    if target_language == "en":
        return text

    indic_lang = LANG_CODE_MAP.get(target_language)
    if not indic_lang:
        print(f"⚠️  Unknown language code '{target_language}'. Returning English.")
        return text

    if not _load_indic_trans():
        return text  # Fallback: return English if model not available

    try:
        inputs = _indic_tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            src_lang="eng_Latn",
            tgt_lang=indic_lang,
        )
        outputs = _indic_model.generate(**inputs, max_new_tokens=256)
        translated = _indic_tokenizer.batch_decode(outputs, skip_special_tokens=True)
        return translated[0] if translated else text
    except Exception as e:
        print(f"⚠️  Translation error: {e}. Returning English.")
        return text


def translate_batch(texts: list[str], target_language: str) -> list[str]:
    """Translate a list of English strings to the target language."""
    return [translate_text(t, target_language) for t in texts]


def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate from an Indian language to English.
    Used in Mode 2 to normalize the user's prompt before SD generation.
    """
    if source_language == "en":
        return text

    src_lang = LANG_CODE_MAP.get(source_language, "eng_Latn")

    if not _load_indic_trans():
        return text

    try:
        # Use the indic-en model (reverse direction)
        # NOTE: For full reverse support, ai4bharat/indictrans2-indic-en-1B should be used.
        # This is a placeholder — swap in the correct model if needed.
        return text  # Placeholder until reverse model is loaded
    except Exception as e:
        print(f"⚠️  Reverse translation error: {e}.")
        return text
