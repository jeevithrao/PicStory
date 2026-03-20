# ai/video.py
# STUB — Person 6 replaces this with real MoviePy video assembly.
# Contract: same function signature must be kept.

import os

def assemble_video(images: list[str], voiceover: str, music: str, output_dir: str) -> str:
    """
    Input:  ordered image paths, voiceover MP3 path, music MP3 path, output directory
    Output: file path to the final MP4
    """
    # --- STUB: creates an empty placeholder MP4 ---
    # Person 6: replace with real MoviePy + FFmpeg assembly
    path = os.path.join(output_dir, "final_video.mp4")
    open(path, "wb").close()
    return path
