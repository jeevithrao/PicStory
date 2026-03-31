# ai/story.py
# Gemini-powered narration script generator.
# Produces emotional, short-film voiceover style narration from captions.

from google import genai
from app.config import settings

# Language display names for prompt engineering
LANG_NAMES = {
    "hi": "Hindi", "kok": "Konkani", "kn": "Kannada", "doi": "Dogri",
    "brx": "Bodo", "ur": "Urdu", "ta": "Tamil", "ks": "Kashmiri",
    "as": "Assamese", "bn": "Bengali", "mr": "Marathi", "sd": "Sindhi",
    "mai": "Maithili", "pa": "Punjabi", "ml": "Malayalam", "mni": "Manipuri",
    "te": "Telugu", "sa": "Sanskrit", "ne": "Nepali", "sat": "Santali",
    "gu": "Gujarati", "or": "Odia",
}

from app.services.gemini_service import call_gemini_with_retry

def generate_narration_script(captions: list[str], language: str) -> str:
    """emotional short-film voiceover style narration from captions."""
    lang_name = LANG_NAMES.get(language, "English")
    numbered_captions = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))

    prompt = f"""You are a voiceover artist for an award-winning short film. You are given vivid image descriptions from a personal photo slideshow.

Write a deeply emotional, cinematic narration script that weaves all the images into one flowing story. This is NOT a list of descriptions — it is a STORY told from the heart.

Image descriptions:
{numbered_captions}

Style guide:
- Write in {lang_name} language.
- Sound like a narrator from a Humans of Bombay story or a wedding film voiceover.
- Each image gets 2-3 sentences of narration that flow naturally into the next.
- Output ONLY the narration text, nothing else.
"""

    try:
        return call_gemini_with_retry(prompt, model="gemini-flash-latest")
    except Exception as e:
        print(f"⚠️  Gemini narration failed: {e}")
        joined = " ".join(captions)
        return f"Welcome to this story. {joined} Thank you for watching."

def generate_per_image_narration(captions: list[str], language: str) -> list[str]:
    """Generate a separate narration segment for EACH image."""
    lang_name = LANG_NAMES.get(language, "English")
    numbered_captions = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))

    prompt = f"""You are a voiceover artist for an award-winning short film. You are given vivid image descriptions from a personal photo slideshow.

For EACH image, write a separate narration segment (2-3 sentences). 

Style guide:
- Write ALL narration in {lang_name} language.
- Output EXACTLY {len(captions)} segments, numbered 1 through {len(captions)}.
- One segment per line, numbered like: 1. [narration segment]
- Output ONLY the numbered segments, nothing else.
"""

    try:
        raw = call_gemini_with_retry(prompt, model="gemini-flash-latest")
        if not raw: return captions

        import re
        lines = re.findall(r'\d+\.\s*(.+)', raw)

        if len(lines) >= len(captions):
            return lines[:len(captions)]
        elif len(lines) > 0:
            while len(lines) < len(captions):
                lines.append(captions[len(lines)] if len(lines) < len(captions) else "...")
            return lines
        else:
            return captions
    except Exception as e:
        print(f"⚠️  Gemini per-image narration failed: {e}")
        return captions

def suggest_music_vibe(captions: list[str]) -> str:
    """Analyze captions and return the best music vibe for this project."""
    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))
    prompt = f"""Analyze these image descriptions and decide the single best background music mood for a video slideshow:

{numbered}

Choose EXACTLY ONE from this list:
calm, romantic, rock, happy, sad, motivational

Reply with ONLY the one word — nothing else."""

    try:
        vibe = call_gemini_with_retry(prompt, model="gemini-flash-latest").lower().replace('"', '').replace("'", "")
        valid = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
        return vibe if vibe in valid else "calm"
    except Exception:
        return "calm"
