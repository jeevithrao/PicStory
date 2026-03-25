# ai/audio.py
# Edge TTS voiceover + MusicGen background music.
# Edge TTS: async text-to-speech in 22+ Indian languages (free, no API key).
# MusicGen: AI music generation from vibe prompts via model_manager.

import os
import asyncio
import edge_tts

# Mapping of our language codes → Edge TTS voice names
EDGE_TTS_VOICES = {
    "hi":  "hi-IN-SwaraNeural",
    "bn":  "bn-IN-TanishaaNeural",
    "ta":  "ta-IN-PallaviNeural",
    "te":  "te-IN-ShrutiNeural",
    "mr":  "mr-IN-AarohiNeural",
    "gu":  "gu-IN-DhwaniNeural",
    "kn":  "kn-IN-SapnaNeural",
    "ml":  "ml-IN-SobhanaNeural",
    "pa":  "pa-IN-GurpreetNeural",
    "ur":  "ur-PK-UzmaNeural",
    "as":  "as-IN-PriyomNeural",
    "or":  "or-IN-SubhasiniNeural",
    "ne":  "ne-NP-HemkalaNeural",
    "sd":  "sd-IN-SwaraNeural",           # Sindhi — falls back to Hindi voice
    "sa":  "hi-IN-SwaraNeural",           # Sanskrit — no dedicated voice, use Hindi
    "ks":  "hi-IN-SwaraNeural",           # Kashmiri — use Hindi fallback
    "kok": "hi-IN-SwaraNeural",           # Konkani — use Hindi fallback
    "mai": "hi-IN-SwaraNeural",           # Maithili — use Hindi fallback
    "mni": "hi-IN-SwaraNeural",           # Manipuri — use Hindi fallback
    "sat": "hi-IN-SwaraNeural",           # Santali — use Hindi fallback
    "brx": "hi-IN-SwaraNeural",           # Bodo — use Hindi fallback
    "doi": "hi-IN-SwaraNeural",           # Dogri — use Hindi fallback
    # Languages without a dedicated Edge TTS voice use Hindi
}

# Mood prompts for MusicGen
VIBE_PROMPTS = {
    "calm":          "soft calm ambient relaxing background music, peaceful piano",
    "romantic":      "romantic gentle love song, soft guitar and strings",
    "rock":          "energetic rock instrumental, electric guitar and drums",
    "happy":         "upbeat cheerful happy background music, bright and positive",
    "sad":           "melancholic sad emotional background music, slow piano",
    "motivational":  "inspiring motivational cinematic background music, epic and uplifting",
}


def generate_voiceover(script: str, language: str, output_dir: str) -> str:
    """
    Generate an MP3 voiceover from the narration script using Edge TTS.
    Input:  narration script text, language code, output directory path
    Output: file path to the generated voiceover MP3
    """
    voice = EDGE_TTS_VOICES.get(language, EDGE_TTS_VOICES.get("hi"))
    output_path = os.path.join(output_dir, "narration.mp3")

    async def _generate():
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(output_path)

    # Run async Edge TTS in a separate thread to avoid event loop conflicts
    import threading
    exception_holder = []

    def _run_in_thread():
        try:
            asyncio.run(_generate())
        except Exception as e:
            exception_holder.append(e)

    t = threading.Thread(target=_run_in_thread)
    t.start()
    t.join(timeout=120)

    if exception_holder:
        raise exception_holder[0]

    print(f"✅ Voiceover generated: {output_path}")
    return output_path


def generate_per_image_voiceovers(
    narration_segments: list[str],
    language: str,
    output_dir: str,
) -> list[dict]:
    """
    Generate one MP3 voiceover per image narration segment using Edge TTS.
    Input:  list of narration text segments (one per image), language code, output dir
    Output: list of dicts with {path, duration} for each segment
    """
    from mutagen.mp3 import MP3

    voice = EDGE_TTS_VOICES.get(language, EDGE_TTS_VOICES.get("hi"))
    results = []

    for i, segment_text in enumerate(narration_segments):
        segment_text = segment_text.strip()
        if not segment_text:
            segment_text = "..."  # Minimal text for empty segments

        output_path = os.path.join(output_dir, f"narration_segment_{i}.mp3")

        async def _generate(text, path):
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(path)

        # Run async Edge TTS in a separate thread
        import threading
        exception_holder = []

        def _run_in_thread(text=segment_text, path=output_path):
            try:
                asyncio.run(_generate(text, path))
            except Exception as e:
                exception_holder.append(e)

        t = threading.Thread(target=_run_in_thread)
        t.start()
        t.join(timeout=60)

        if exception_holder:
            print(f"⚠️  TTS failed for segment {i}: {exception_holder[0]}")
            # Create a short silence as fallback
            results.append({"path": None, "duration": 3.0})
            continue

        # Get duration from the MP3 file
        try:
            audio = MP3(output_path)
            duration = audio.info.length
        except Exception:
            duration = 3.0  # Default 3 seconds if we can't read duration

        results.append({"path": output_path, "duration": duration})
        print(f"✅ Segment {i} voiceover: {output_path} ({duration:.1f}s)")

    return results


def detect_mood(script: str) -> str:
    """
    Simple keyword-based mood detection from the narration script.
    """
    script_lower = script.lower()
    mood_keywords = {
        "sad":           ["sad", "cry", "tears", "loss", "miss", "grief", "sorrow"],
        "romantic":      ["love", "heart", "romance", "together", "kiss", "passion"],
        "happy":         ["happy", "joy", "smile", "laugh", "fun", "celebrate", "cheerful"],
        "motivational":  ["inspire", "dream", "achieve", "strong", "power", "success", "courage"],
        "rock":          ["rock", "energy", "fire", "wild", "thunder", "bold"],
        "calm":          ["peace", "calm", "quiet", "gentle", "soft", "serene", "nature"],
    }
    for mood, keywords in mood_keywords.items():
        if any(kw in script_lower for kw in keywords):
            return mood
    return "calm"  # Default


def generate_music(vibe: str, output_dir: str, filename: str = None) -> str:
    """
    Generate background music using MusicGen-small.
    Input:  vibe string, output directory path
    Output: file path to the generated music WAV
    """
    from app.services.model_manager import load_musicgen, unload_musicgen
    import scipy.io.wavfile
    import numpy as np

    model, processor = load_musicgen()

    prompt = VIBE_PROMPTS.get(vibe, VIBE_PROMPTS["calm"])
    inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(model.device)

    # Generate ~15 seconds of audio (256 tokens ≈ 15s at MusicGen's default sample rate)
    audio_values = model.generate(**inputs, max_new_tokens=256)

    # Convert to numpy and save as WAV
    audio_np = audio_values[0, 0].cpu().numpy()
    sample_rate = model.config.audio_encoder.sampling_rate
    output_path = os.path.join(output_dir, filename or f"music_{vibe}.wav")

    # Normalize to int16 range
    audio_int16 = (audio_np * 32767).astype(np.int16)
    scipy.io.wavfile.write(output_path, sample_rate, audio_int16)

    unload_musicgen()  # Free VRAM
    print(f"✅ Music generated: {output_path}")
    return output_path
