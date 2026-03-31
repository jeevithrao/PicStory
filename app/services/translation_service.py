# app/services/translation_service.py
# Translation service using Gemini API.
# Translates between English and 22 Indian languages.

from google import genai
from app.config import settings
import os

# Language display names
LANG_NAMES = {
    "hi": "Hindi", "kok": "Konkani", "kn": "Kannada", "doi": "Dogri",
    "brx": "Bodo", "ur": "Urdu", "ta": "Tamil", "ks": "Kashmiri",
    "as": "Assamese", "bn": "Bengali", "mr": "Marathi", "sd": "Sindhi",
    "mai": "Maithili", "pa": "Punjabi", "ml": "Malayalam", "mni": "Manipuri",
    "te": "Telugu", "sa": "Sanskrit", "ne": "Nepali", "sat": "Santali",
    "gu": "Gujarati", "or": "Odia",
}

# NLLB-200 language codes for Indic Support
NLLB_LANG_CODES = {
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "kn": "kan_Knda",
    "ml": "mal_Mlym",
    "bn": "ben_Beng",
    "mr": "mar_Deva",
    "gu": "guj_Gujr",
    "pa": "pan_Guru",
    "or": "ory_Orya",
    "ur": "urd_Arab",
    "as": "asm_Beng",
    "kok": "gom_Deva",
    "ne": "npi_Deva",
    "sa": "san_Deva",
    "mai": "mai_Deva",
    "doi": "doi_Deva",
    "ks": "kas_Arab",
    "sd": "snd_Deva",
    "mni": "mni_Beng",
    "brx": "brx_Deva",
    "sat": "sat_Olck",
}

LANG_NAME_TO_CODE = {
    "english": "en",
    "hindi": "hi",
    "konkani": "kok",
    "kannada": "kn",
    "dogri": "doi",
    "bodo": "brx",
    "urdu": "ur",
    "tamil": "ta",
    "kashmiri": "ks",
    "assamese": "as",
    "bengali": "bn",
    "marathi": "mr",
    "sindhi": "sd",
    "maithili": "mai",
    "punjabi": "pa",
    "malayalam": "ml",
    "manipuri": "mni",
    "telugu": "te",
    "sanskrit": "sa",
    "nepali": "ne",
    "santali": "sat",
    "gujarati": "gu",
    "odia": "or",
}

from app.services.gemini_service import call_gemini_with_retry

def _normalize_lang_code(language: str) -> str:
    code = (language or "").strip().lower()
    if code in LANG_NAMES:
        return code
    return LANG_NAME_TO_CODE.get(code, code)

def _translate_local_indic(text: str, target_lang: str) -> str:
    """Translate text using local NLLB-200 model (EN -> Indic)."""
    from app.services.model_manager import load_indic_translator
    import torch
    
    model, tokenizer = load_indic_translator()
    
    src_code = "eng_Latn"
    tgt_code = NLLB_LANG_CODES.get(target_lang, "hin_Deva")
    
    # 1. Set identifiers on tokenizer
    if hasattr(tokenizer, 'src_lang'): tokenizer.src_lang = src_code
    if hasattr(tokenizer, 'tgt_lang'): tokenizer.tgt_lang = tgt_code
    
    # 2. Extract Lang ID from the tokenizer
    # NLLB usually expects the lang ID as the forced_decoder_ids[0][1]
    lang_id = None
    if hasattr(tokenizer, 'get_lang_id'):
        lang_id = tokenizer.get_lang_id(tgt_code)
    elif hasattr(tokenizer, 'lang_code_to_id'):
        lang_id = tokenizer.lang_code_to_id.get(tgt_code)
    else:
        # Fallback to manual convert
        lang_id = tokenizer.convert_tokens_to_ids(tgt_code)
    
    print(f"DEBUG: Translating to {tgt_code} (ID: {lang_id})")
    
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        # Corrected generate call for NLLB: decoder_start_token_id is more robust
        # for some transformers versions to avoid 'forced_decoder_ids' conflict warnings.
        generated_tokens = model.generate(
            **inputs,
            decoder_start_token_id=lang_id,
            num_beams=4,
            max_length=256
        )
    
    result = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
    return result

def translate_text(text: str, target_language: str) -> str:
    """Translate a single English string to the target Indian language using Gemini or IndicTrans2."""
    code = _normalize_lang_code(target_language)
    if code == "en" or not text.strip():
        return text

    lang_name = LANG_NAMES.get(code)
    if not lang_name:
        print(f"WARNING: Unknown language code '{target_language}'. Returning English.")
        return text

    try:
        # We only use local translation if explicitly requested via a NEW env var
        # otherwise we default to Gemini for much higher quality (as the user asked).
        use_local_trans = os.getenv("USE_LOCAL_TRANSLATION", "false").lower() == "true"
        
        if use_local_trans:
            return _translate_local_indic(text, code)
        
        prompt = f"Translate the following English text into natively written {lang_name}. Output ONLY the translated text, nothing else.\n\nText: {text}"
        translated = call_gemini_with_retry(prompt)
        return translated if translated else text
    except Exception as e:
        print(f"WARNING: Translation error for {lang_name}: {e}. Returning English.")
        return text

def translate_batch(texts: list[str], target_language: str) -> list[str]:
    """Translate a list of English strings to the target language using Gemini or IndicTrans2."""
    code = _normalize_lang_code(target_language)
    if code == "en" or not texts:
        return texts

    try:
        use_local_trans = os.getenv("USE_LOCAL_TRANSLATION", "false").lower() == "true"

        if use_local_trans:
            return [_translate_local_indic(t, code) for t in texts]

        lang_name = LANG_NAMES.get(code, "Hindi")
        # Batch all captions in one API call for efficiency
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        prompt = f"""Translate each of the following English sentences into natively written {lang_name}.
Keep the numbered format. Output ONLY the translated sentences with their numbers, nothing else.

{numbered}"""

        raw = call_gemini_with_retry(prompt)
        if not raw:
            return texts

        # Parse numbered lines
        import re
        lines = re.findall(r'\d+\.\s*(.+)', raw)

        if len(lines) == len(texts):
            return lines
        else:
            # Fallback: translate one by one
            return [translate_text(t, target_language) for t in texts]

    except Exception as e:
        print(f"WARNING: Batch translation failed for {code}: {e}. Returning English.")
        return texts

def translate_to_english(text: str, source_language: str) -> str:
    """Translate from an Indian language to English using Gemini (No local model for Indic->EN yet)."""
    source_code = _normalize_lang_code(source_language)
    if source_code == "en" or not text.strip():
        return text

    try:
        # IndicTrans2 200m dist is only EN -> Indic. 
        # For simplicity in this demo, we keep Gemini for Indic -> EN.
        
        lang_name = LANG_NAMES.get(source_code)
        if not lang_name:
            print(f"WARNING: Unknown language code '{source_language}'. Returning original text.")
            return text

        prompt = f"Translate the following {lang_name} text into English. Output ONLY the English translation, nothing else.\n\nText: {text}"
        translated = call_gemini_with_retry(prompt)
        return translated if translated else text
    except Exception as e:
        print(f"WARNING: Translation to English failed: {e}. Returning original text.")
        return text
