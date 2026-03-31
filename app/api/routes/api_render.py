# app/api/routes/api_render.py
# POST /api/render — Phase 3 of the 5-step pipeline (ZIP flow only).
#
# AWARENESS MODE  (awareness_narration has exactly 1 item):
#   → Generates ONE single voiceover from the awareness message.
#   → Images slide through at equal intervals while narration plays uninterrupted.
#
# STANDARD MODE:
#   → Generates one voiceover segment per image (existing per-image flow).

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import file_service, db_service

router = APIRouter()


class ImageCaption(BaseModel):
    url: str        # e.g. "/uploads/uuid/photo.jpg"
    caption: str    # User-edited caption text


class RenderRequest(BaseModel):
    projectId: str
    images: list[ImageCaption]
    language: str = "English"
    audio: str = "calm"
    awareness_narration: list[str] = []   # len==1 → awareness mode, else standard mode


@router.post("/api/render")
async def render(req: RenderRequest):
    """
    Step 4-5: Edit → Download.
    Takes the user's edited image order and captions,
    runs TTS → music → video assembly, returns videoUrl.
    """
    try:
        project_id = req.projectId

        # Validate project exists
        project = db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        # Resolve absolute image paths and collect captions
        project_dir = file_service.get_project_upload_dir(project_id)
        image_paths = []
        filenames = []
        captions = []

        for item in req.images:
            fname = os.path.basename(item.url)
            abs_path = os.path.join(project_dir, fname)

            if not os.path.exists(abs_path):
                raise HTTPException(
                    status_code=400, detail=f"Image not found: {fname}"
                )

            image_paths.append(abs_path)
            filenames.append(fname)
            captions.append(item.caption)

        if not image_paths:
            raise HTTPException(status_code=400, detail="No images provided.")

        # Save the new ordering to DB
        all_project_images = [
            os.path.basename(p) for p in file_service.list_project_images(project_id)
        ]
        removed = [f for f in all_project_images if f not in filenames]
        db_service.apply_image_edits(project_id, filenames, removed)

        # ─── DETECT MODE ─────────────────────────────────────────────────────────
        # Awareness mode  → awareness_narration has exactly 1 item (single message)
        # Standard mode   → per-image flow (0 or many items)
        is_awareness_mode = (
            req.awareness_narration and len(req.awareness_narration) == 1
        )

        db_service.update_project_status(project_id, "narrating")
        output_dir = file_service.get_project_output_dir(project_id)

        from ai.audio import generate_voiceover, generate_per_image_voiceovers
        from ai.video import assemble_video as build_video

        # ─── NARRATION + VIDEO ASSEMBLY ──────────────────────────────────────────
        if is_awareness_mode:
            # ── AWARENESS: one voiceover plays while images slide through ──────────
            narration_text = req.awareness_narration[0]
            print(
                f"[awareness] Single-narration mode — "
                f"1 voiceover for {len(image_paths)} images"
            )

            # Generate ONE voiceover for the entire video
            narration_path = generate_voiceover(
                script=narration_text,
                language=req.language,
                output_dir=output_dir,
            )

            db_service.save_narration(
                project_id, narration_text, narration_path, req.language
            )
            db_service.update_project_status(project_id, "narration_ready")

            # Music
            vibe = _resolve_vibe(req.audio)
            music_path = _generate_music(vibe, output_dir)

            db_service.save_music(project_id, vibe, "ai",
                                  file_service.relative_path(music_path) if music_path else "")
            db_service.update_project_status(project_id, "music_ready")

            # Video: legacy single-voiceover mode — images slide evenly across narration
            db_service.update_project_status(project_id, "assembling")
            video_path = build_video(
                images=image_paths,
                voiceover=narration_path,   # single audio → images distributed evenly
                music=music_path,
                output_dir=output_dir,
                voiceover_segments=None,    # explicitly no per-image segments
            )

        else:
            # ── STANDARD: per-image voiceovers ───────────────────────────────────
            narration_segments = captions
            if req.awareness_narration and len(req.awareness_narration) > 0:
                narration_segments = req.awareness_narration[: len(captions)]
                print(
                    f"[awareness] Per-image narration mode — "
                    f"{len(narration_segments)} segments"
                )
            else:
                print("[standard] Caption-based narration")

            per_image_results = generate_per_image_voiceovers(
                narration_segments=narration_segments,
                language=req.language,
                output_dir=output_dir,
            )

            narration_text = "\n\n".join(narration_segments)
            narration_path = generate_voiceover(
                script=narration_text,
                language=req.language,
                output_dir=output_dir,
            )

            db_service.save_narration(
                project_id, narration_text, narration_path, req.language
            )
            db_service.update_project_status(project_id, "narration_ready")

            per_image_narrations = [
                {
                    "path": seg["path"],
                    "duration": seg["duration"],
                    "text": narration_segments[i] if i < len(narration_segments) else "",
                }
                for i, seg in enumerate(per_image_results)
            ]

            # Music
            vibe = _resolve_vibe(req.audio)
            music_path = _generate_music(vibe, output_dir)

            db_service.save_music(project_id, vibe, "ai",
                                  file_service.relative_path(music_path) if music_path else "")
            db_service.update_project_status(project_id, "music_ready")

            # Video: per-image segments — each image shown for its segment duration
            db_service.update_project_status(project_id, "assembling")
            video_path = build_video(
                images=image_paths,
                voiceover=None,
                music=music_path,
                output_dir=output_dir,
                voiceover_segments=per_image_narrations,
            )

        db_service.update_project_status(project_id, "completed")
        video_url = "/" + file_service.relative_path(video_path).replace("\\", "/")
        return {"videoUrl": video_url}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Render error: {str(e)}")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _resolve_vibe(audio: str) -> str:
    """Normalise the audio vibe string to one of the known MusicGen options."""
    vibe = audio.lower() if audio else "calm"
    valid = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
    return vibe if vibe in valid else "calm"


def _generate_music(vibe: str, output_dir: str) -> str:
    """Generate background music, returning path or empty string on failure."""
    try:
        from ai.audio import generate_music
        return generate_music(vibe, output_dir)
    except Exception as e:
        print(f"[music] Generation failed ({e}), skipping background music.")
        return ""
