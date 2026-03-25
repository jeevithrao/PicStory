# ai/captioning.py
# BLIP image captioning + Gemini emotional enhancement.
# Raw BLIP caption → Gemini expands into vivid, emotional description
# directly in the target language.

from PIL import Image

# Language display names for prompt engineering
LANG_NAMES = {
    "hi": "Hindi", "kok": "Konkani", "kn": "Kannada", "doi": "Dogri",
    "brx": "Bodo", "ur": "Urdu", "ta": "Tamil", "ks": "Kashmiri",
    "as": "Assamese", "bn": "Bengali", "mr": "Marathi", "sd": "Sindhi",
    "mai": "Maithili", "pa": "Punjabi", "ml": "Malayalam", "mni": "Manipuri",
    "te": "Telugu", "sa": "Sanskrit", "ne": "Nepali", "sat": "Santali",
    "gu": "Gujarati", "or": "Odia",
}


def generate_captions(image_paths: list[str], language: str = "en", context: str = "") -> list[str]:
    """
    Input:  list of absolute image file paths, target language code, optional context
    Output: list of emotionally enhanced caption strings in the target language
    """
    from app.services.model_manager import load_blip, unload_blip

    model, processor = load_blip()

    raw_captions = []
    for path in image_paths:
        try:
            raw_image = Image.open(path).convert("RGB")
            inputs = processor(raw_image, return_tensors="pt").to(model.device)
            output_ids = model.generate(**inputs, max_new_tokens=50)
            caption = processor.decode(output_ids[0], skip_special_tokens=True)
            raw_captions.append(caption.strip())
        except Exception as e:
            print(f"⚠️  BLIP failed on {path}: {e}")
            raw_captions.append("A photo.")

    unload_blip()  # Free memory for next model

    # Enhance with Gemini for emotional depth, directly in the target language
    enhanced = _enhance_captions_with_gemini(raw_captions, language=language, context=context)
    return enhanced


def _enhance_captions_with_gemini(
    raw_captions: list[str],
    language: str = "en",
    context: str = "",
) -> list[str]:
    """
    Pass each raw BLIP caption through Gemini for vivid emotional expansion.
    Outputs directly in the target language (no separate translation needed).
    If context is provided, Gemini uses it to guide the descriptions.
    """
    try:
        import google.generativeai as genai
        from app.config import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_key_here":
            print("⚠️  No Gemini key — returning raw BLIP captions")
            return raw_captions

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        lang_name = LANG_NAMES.get(language, "English")
        numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(raw_captions))

        # Build context instruction
        context_instruction = ""
        if context and context.strip():
            context_instruction = f"""
The user has provided this context about the images: "{context.strip()}"
Use this context to guide your descriptions — weave it into the emotional narrative naturally.
"""

        prompt = f"""You are a poetic visual storyteller. I will give you plain image descriptions.
For EACH description, rewrite it as an emotionally rich, vivid, cinematic description in 1-2 sentences.
Use sensory language — colors, textures, moods, feelings. Evoke nostalgia, warmth, wonder, or beauty.
{context_instruction}
Plain descriptions:
{numbered}

Rules:
- Write ALL descriptions in {lang_name} language.
- Output ONLY the rewritten descriptions, one per line, numbered the same way.
- Do NOT add headers, explanations, or markdown.
- Keep them concise but evocative (max 2 sentences each).
- Match the mood to contextual clues in each description.

Example (if language is English):
Input: "a group of people standing near a building"
Output: "A gathering of loved ones stands bathed in golden light, their laughter echoing off weathered stone walls — a moment frozen between hello and goodbye."
"""

        response = model.generate_content(prompt)
        lines = [l.strip() for l in response.text.strip().split("\n") if l.strip()]

        enhanced = []
        for line in lines:
            # Strip numbering like "1. " or "1) "
            import re
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
            if cleaned:
                enhanced.append(cleaned)

        # Ensure same count — pad with originals if Gemini returned fewer
        if len(enhanced) >= len(raw_captions):
            return enhanced[:len(raw_captions)]
        else:
            return enhanced + raw_captions[len(enhanced):]

    except Exception as e:
        print(f"⚠️  Gemini enhancement failed: {e}")
        return raw_captions
