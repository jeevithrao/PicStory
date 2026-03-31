# ai/audio.py
# Edge TTS voiceover + MusicGen background music.
# Edge TTS: async text-to-speech in 22+ Indian languages (free, no API key).
# MusicGen: AI music generation from vibe prompts via model_manager.

import os
import asyncio
from gtts import gTTS
from mutagen.mp3 import MP3

# Mapping of language codes AND display names → Edge TTS voice names
EDGE_TTS_VOICES = {
    # Short codes
    "en":  "en-US-AriaNeural",
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
    "sd":  "sd-IN-SwaraNeural",
    "sa":  "hi-IN-SwaraNeural",
    "ks":  "hi-IN-SwaraNeural",
    "kok": "hi-IN-SwaraNeural",
    "mai": "hi-IN-SwaraNeural",
    "mni": "hi-IN-SwaraNeural",
    "sat": "hi-IN-SwaraNeural",
    "brx": "hi-IN-SwaraNeural",
    "doi": "hi-IN-SwaraNeural",
    # Display names (sent by the frontend)
    "English":    "en-US-AriaNeural",
    "Hindi":      "hi-IN-SwaraNeural",
    "Bengali":    "bn-IN-TanishaaNeural",
    "Tamil":      "ta-IN-PallaviNeural",
    "Telugu":     "te-IN-ShrutiNeural",
    "Marathi":    "mr-IN-AarohiNeural",
    "Gujarati":   "gu-IN-DhwaniNeural",
    "Kannada":    "kn-IN-SapnaNeural",
    "Malayalam":  "ml-IN-SobhanaNeural",
    "Punjabi":    "pa-IN-GurpreetNeural",
    "Urdu":       "ur-PK-UzmaNeural",
    "Assamese":   "as-IN-PriyomNeural",
    "Odia":       "or-IN-SubhasiniNeural",
    "Nepali":     "ne-NP-HemkalaNeural",
    "Sindhi":     "sd-IN-SwaraNeural",
    "Sanskrit":   "hi-IN-SwaraNeural",
    "Kashmiri":   "hi-IN-SwaraNeural",
    "Konkani":    "hi-IN-SwaraNeural",
    "Maithili":   "hi-IN-SwaraNeural",
    "Manipuri":   "hi-IN-SwaraNeural",
    "Santali":    "hi-IN-SwaraNeural",
    "Bodo":       "hi-IN-SwaraNeural",
    "Dogri":      "hi-IN-SwaraNeural",
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
    """Generates voiceover using Google TTS instead of Edge TTS."""
    print(f"🎙️ Generating voiceover in {language}...")

    # Default to English if the language code isn't supported by gTTS
    supported_langs = ['hi', 'kn', 'ta', 'te', 'mr', 'bn', 'gu', 'ml', 'ur', 'en']
    tts_lang = language if language in supported_langs else 'en'

    filepath = os.path.join(output_dir, "narration.mp3")

    # Generate and save the audio
    tts = gTTS(text=script, lang=tts_lang, slow=False)
    tts.save(filepath)

    print("✅ Voiceover saved!")
    return filepath


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










def generate_per_image_voiceovers(narration_segments: list, language: str, output_dir: str):
    """
    Takes a list of text captions and generates an individual MP3 for each one.
    This allows the video assembler to perfectly sync images with the audio.
    """
    print(f"🎙️ Generating {len(narration_segments)} individual voiceovers in '{language}'...")
    
    # Fallback to English if the language isn't supported by gTTS
    supported_langs = ['hi', 'kn', 'ta', 'te', 'mr', 'bn', 'gu', 'ml', 'ur', 'en']
    tts_lang = language if language in supported_langs else 'en'
    
    results = []
    
    for i, text in enumerate(narration_segments):
        # Handle empty captions gracefully
        if not text or not text.strip():
            continue
            
        filename = f"scene_{i}_audio.mp3"
        filepath = os.path.join(output_dir, filename)
        
        try:
            # Generate and save the audio file
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(filepath)
            
            # --- NEW CODE: Calculate how long this audio file is ---
            audio_file = MP3(filepath)
            audio_length = audio_file.info.length
            
            # Store the data including the new duration key!
            results.append({
                "path": filepath,
                "text": text,
                "duration": audio_length  # <-- This fixes the KeyError!
            })
        except Exception as e:
            print(f"⚠️ Failed to generate audio for scene {i}: {e}")
            
    print("✅ All scene voiceovers generated!")
    return results