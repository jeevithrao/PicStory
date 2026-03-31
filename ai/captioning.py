import json
import re
from PIL import Image

LANG_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kok": "Konkani",
    "kn": "Kannada",
    "doi": "Dogri",
    "brx": "Bodo",
    "ur": "Urdu",
    "ta": "Tamil",
    "ks": "Kashmiri",
    "as": "Assamese",
    "bn": "Bengali",
    "mr": "Marathi",
    "sd": "Sindhi",
    "mai": "Maithili",
    "pa": "Punjabi",
    "ml": "Malayalam",
    "mni": "Manipuri",
    "te": "Telugu",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "sat": "Santali",
    "gu": "Gujarati",
    "or": "Odia",
}

def generate_captions(image_paths: list[str], language: str = "en", context: str = "") -> list[str]:
    from app.services.gemini_service import call_gemini_with_retry

    language_code = _normalize_language_code(language)
    lang_name = LANG_NAMES.get(language_code, language_code)

    context_instruction = ""
    if context and context.strip():
        context_instruction = (
            f'IMPORTANT CONTEXT: The user says these images are part of a story about: "{context.strip()}". '
            "Use this context strictly and avoid hallucinations."
        )

    prompt = f"""You are a storyteller writing short captions for photo slides.
Look at the attached images and return ONLY a valid JSON list of strings.

Rules:
1) Write the captions strictly in {lang_name} (script/characters).
2) Make them short (8-12 words max).
3) No markdown, no extra text, JSON array ONLY.
{context_instruction}

There are exactly {len(image_paths)} images attached.
Return ONLY a JSON array with exactly that many string items, in image order.
Format: ["caption 1", "caption 2", ...]
"""

    images: list[Image.Image] = []
    for path in image_paths:
        if not path:
            raise RuntimeError("Empty image path encountered during captioning")
        img = Image.open(path)
        img.thumbnail((512, 512))
        images.append(img)

    response_text = call_gemini_with_retry(prompt, model="gemini-flash-latest", contents=[prompt, *images])
    
    return _parse_caption_array(response_text, len(image_paths))

def _parse_caption_array(raw_text: str, expected_len: int) -> list[str]:
    if not raw_text:
        raise RuntimeError("Gemini returned empty caption response.")

    cleaned = raw_text
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                data = None

    if not isinstance(data, list):
        raise RuntimeError(f"Gemini did not return a JSON list. Raw: {cleaned[:200]}")
    
    if len(data) != expected_len:
        if len(data) > expected_len:
            data = data[:expected_len]
        else:
            data.extend(["A specific image piece of the story."] * (expected_len - len(data)))

    return [str(item).strip() for item in data]

def _normalize_language_code(language: str) -> str:
    code = (language or "").strip().lower()
    if code in LANG_NAMES:
        return code
    name_to_code = {v.lower(): k for k, v in LANG_NAMES.items()}
    return name_to_code.get(code, code[:2] if code else "en")
