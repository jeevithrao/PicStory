# ai/video.py
# MoviePy + FFmpeg video assembly.
# Creates a slideshow from images where each image stays on screen
# for the duration of its narration segment. Overlays narration + background music,
# adds a Ken Burns (zoom/pan) effect, and exports as MP4.

import os
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    concatenate_audioclips, CompositeAudioClip, CompositeVideoClip
)

# Target video resolution
WIDTH, HEIGHT = 1280, 720


def _ken_burns(clip, zoom_start=1.0, zoom_end=1.15):
    """Apply a slow zoom-in (Ken Burns) effect to an image clip."""
    duration = clip.duration

    def _resize(get_frame, t):
        progress = t / duration if duration > 0 else 0
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        frame = get_frame(t)
        from PIL import Image
        import numpy as np
        img = Image.fromarray(frame)
        w, h = img.size
        new_w, new_h = int(w * zoom), int(h * zoom)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Center-crop back to original size
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        img = img.crop((left, top, left + w, top + h))
        return np.array(img)

    return clip.fl(_resize)


def _fit_image(image_path: str) -> ImageClip:
    """Load an image and resize/pad it to fit the target resolution."""
    from PIL import Image
    import numpy as np

    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size

    # Calculate scale to fit within WIDTH x HEIGHT
    scale = min(WIDTH / img_w, HEIGHT / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Create a black background canvas
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    paste_x = (WIDTH - new_w) // 2
    paste_y = (HEIGHT - new_h) // 2
    canvas.paste(img, (paste_x, paste_y))

    return ImageClip(np.array(canvas))


def assemble_video(
    images: list[str],
    voiceover: str = None,
    music: str = None,
    output_dir: str = "",
    voiceover_segments: list[dict] = None,
) -> str:
    """
    Input:
      images:             ordered image paths
      voiceover:          single voiceover MP3 path (old style, for backward compat)
      music:              music MP3/WAV path
      output_dir:         output directory
      voiceover_segments: list of {path, duration} dicts — one per image
                          When provided, each image stays on screen for its segment duration.
    Output: file path to the final MP4
    """
    if not images:
        raise ValueError("No images provided for video assembly.")

    # --- Determine per-image durations ---
    if voiceover_segments and len(voiceover_segments) == len(images):
        # New flow: each image matches its narration segment duration perfectly
        final_clips = []
        
        for i, img_path in enumerate(images):
            seg = voiceover_segments[i]
            seg_path = seg.get("path")
            
            # 1. Load Audio Segment first (the source of truth for duration)
            audio_clip = None
            if seg_path and os.path.exists(seg_path):
                try:
                    audio_clip = AudioFileClip(seg_path)
                except Exception as e:
                    print(f"[Video] Could not load audio segment {seg_path}: {e}")

            
            # 2. Determine Duration
            duration = audio_clip.duration if audio_clip else 3.0
            if duration < 0.1: duration = 3.0 # Sanity check
            
            # 3. Create Image Clip with matching duration
            img_clip = _fit_image(img_path).set_duration(duration)
            img_clip = _ken_burns(img_clip)
            
            # 4. Attach audio to this specific image clip
            if audio_clip:
                img_clip = img_clip.set_audio(audio_clip)
            
            final_clips.append(img_clip)

        # Concatenate the synchronized clips
        video = concatenate_videoclips(final_clips, method="compose")
        narration_audio = video.audio # Extracted from the synchronized video

    elif voiceover:
        # Legacy flow: single voiceover, equal time per image
        narration_audio = AudioFileClip(voiceover)
        total_duration = narration_audio.duration
        per_image = max(total_duration / len(images), 2.0)

        clips = []
        for path in images:
            clip = _fit_image(path).set_duration(per_image)
            clip = _ken_burns(clip)
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")
        video = video.set_duration(min(video.duration, total_duration + 1.0))

    else:
        raise ValueError("Either voiceover or voiceover_segments must be provided.")

    # Build audio mix
    audio_tracks = []
    if narration_audio:
        audio_tracks.append(narration_audio)

    if music and os.path.exists(music) and os.path.getsize(music) > 0:
        try:
            music_audio = AudioFileClip(music)
            # Loop music if shorter than video, and lower volume
            if music_audio.duration < video.duration:
                from moviepy.editor import afx
                music_audio = afx.audio_loop(music_audio, duration=video.duration)
            else:
                music_audio = music_audio.subclip(0, video.duration)
            music_audio = music_audio.volumex(0.25)  # 25% volume for background
            audio_tracks.append(music_audio)
        except Exception as e:
            print(f"[Video] Could not load music track: {e}. Skipping background music.")


    # Combine audio tracks
    if audio_tracks:
        final_audio = CompositeAudioClip(audio_tracks)
        video = video.set_audio(final_audio)

    # Export
    output_path = os.path.join(output_dir, "final_video.mp4")
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar",
    )

    # Cleanup
    if narration_audio:
        narration_audio.close()
    video.close()

    print(f"[Video] Video assembled: {output_path}")

    return output_path
