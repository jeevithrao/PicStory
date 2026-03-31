# ai/story.py
# Gemini-powered narration script generator.
# Produces emotional, short-film voiceover style narration from captions.
# Can generate per-image narration segments for synced slideshow video.

import google.generativeai as genai
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

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_key_here":
            raise ValueError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=api_key)
        _configured = True


def generate_narration_script(captions: list[str], language: str, model: str = "gemini") -> str:
    """
    Input:  captions (list of strings — can be in any language), language code, model name
    Output: single narration script string — emotional short-film voiceover style
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, "English")
    numbered_captions = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))

    prompt = f"""You are a voiceover artist for an award-winning short film. You are given vivid image descriptions from a personal photo slideshow.

Write a deeply emotional, cinematic narration script that weaves all the images into one flowing story. This is NOT a list of descriptions — it is a STORY told from the heart.

Image descriptions:
{numbered_captions}

Style guide:
- Write in {lang_name} language.
- Sound like a narrator from a Humans of Bombay story or a wedding film voiceover.
- Use sensory, poetic language — describe not just what's seen, but what it FEELS like.
- Evoke specific emotions: nostalgia, joy, hope, love, pride, warmth, bittersweet beauty.
- Use pauses (…) and rhetorical questions to create rhythm.
- Each image gets 2-3 sentences of narration that flow naturally into the next.
- Start with a hook that pulls the listener in. End with a line that lingers.
- Do NOT include stage directions, timestamps, image numbers, or speaker labels.
- Output ONLY the narration text, nothing else.

Example tone:
"Some moments don't need a calendar to remind you… they live in the way light fell across a room, in the echo of a laugh you'd recognize anywhere. This is one of those stories."
"""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️  Gemini narration failed: {e}")
        joined = " ".join(captions)
        return f"Welcome to this story. {joined} Thank you for watching."


def generate_per_image_narration(captions: list[str], language: str) -> list[str]:
    """
    Generate a separate narration segment for EACH image.
    Returns a list of narration strings, one per image.
    Each segment is 2-3 sentences designed for voiceover.
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, "English")
    numbered_captions = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))

    prompt = f"""You are a voiceover artist for an award-winning short film. You are given vivid image descriptions from a personal photo slideshow.

For EACH image, write a separate narration segment (2-3 sentences). These segments will be read aloud one at a time over each image in a slideshow video.

Image descriptions:
{numbered_captions}

Style guide:
- Write ALL narration in {lang_name} language.
- Sound like a narrator from a Humans of Bombay story or a wedding film voiceover.
- Use sensory, poetic language — describe not just what's seen, but what it FEELS like.
- Each segment should flow naturally from the previous one, telling a coherent story.
- The first segment should hook the listener. The last should leave a lingering feeling.
- Do NOT include stage directions, timestamps, or speaker labels.

Output format:
- Output EXACTLY {len(captions)} segments, numbered 1 through {len(captions)}.
- One segment per line, numbered like: 1. [narration segment]
- Each segment should be 2-3 sentences.
- Output ONLY the numbered segments, nothing else.
"""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        raw = response.text.strip()

        import re
        lines = re.findall(r'\d+\.\s*(.+)', raw)

        if len(lines) >= len(captions):
            return lines[:len(captions)]
        elif len(lines) > 0:
            # Pad with generic segments
            while len(lines) < len(captions):
                lines.append(captions[len(lines)] if len(lines) < len(captions) else "...")
            return lines
        else:
            # Fallback: use captions directly
            return captions

    except Exception as e:
        print(f"⚠️  Gemini per-image narration failed: {e}")
        return captions


def suggest_music_vibe(captions: list[str]) -> str:
    story_context = " ".join(captions)
    
    # Update the prompt so Gemini knows it has more choices now
    prompt = f"""
    Based on these image descriptions: '{story_context}'
    Pick exactly ONE word from this list that best fits the mood: 
    calm, romantic, happy, sad, motivational, cinematic, 
    rock, hip-hop, cultural, electric, lo-fi, emotional.
    Return only the word, nothing else.
    """
    _ensure_configured()

    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))
    prompt = f"""Analyze these image descriptions and decide the single best background music mood for a video slideshow:

{numbered}

Choose EXACTLY ONE from this list:
calm, romantic, rock, happy, sad, motivational

Reply with ONLY the one word — nothing else."""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        vibe = response.text.strip().lower().replace('"', '').replace("'", "")
        valid = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
        return vibe if vibe in valid else "calm"
    except Exception:
        return "calm"