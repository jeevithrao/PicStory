# ai/audio.py
# STUB — Person 5 replaces this with real Edge TTS + MusicGen.
# Contract: same function signatures must be kept.

import os

def generate_voiceover(script: str, language: str, output_dir: str) -> str:
    """
    Input:  narration script text, language code, output directory path
    Output: file path to the generated voiceover MP3
    """
    # --- STUB: creates an empty placeholder MP3 ---
    # Person 5: replace with real Edge TTS call
    path = os.path.join(output_dir, "narration.mp3")
    open(path, "wb").close()   # Empty file placeholder
    return path


def detect_mood(script: str) -> str:
    """
    Input:  narration script text
    Output: vibe string (calm | romantic | rock | happy | sad | motivational)
    """
    # --- STUB ---
    return "calm"


def generate_music(vibe: str, output_dir: str) -> str:
    """
    Input:  vibe string, output directory path
    Output: file path to the generated music MP3
    """
    # --- STUB: creates an empty placeholder MP3 ---
    # Person 5: replace with real MusicGen inference
    path = os.path.join(output_dir, f"music_{vibe}.mp3")
    open(path, "wb").close()
    return path
