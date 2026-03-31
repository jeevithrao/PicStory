# app/api/routes/api_render.py
# POST /api/render — Phase 3 of the 5-step pipeline (ZIP flow only).
# Receives the user's edited image order + edited captions,
# then runs TTS narration, music generation, and video assembly.
# NO BLIP or Gemini story generation — captions come from the user.

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

        # --- TTS: Generate per-image voiceovers from user's captions ---
        db_service.update_project_status(project_id, "narrating")
        output_dir = file_service.get_project_output_dir(project_id)

        from ai.audio import generate_per_image_voiceovers, generate_voiceover

        per_image_results = generate_per_image_voiceovers(
            narration_segments=captions,
            language=req.language,
            output_dir=output_dir,
        )

        narration_text = "\n\n".join(captions)
        narration_path = generate_voiceover(
            script=narration_text,
            language=req.language,
            output_dir=output_dir,
        )

        db_service.save_narration(project_id, narration_text, narration_path, req.language)
        db_service.update_project_status(project_id, "narration_ready")

        per_image_narrations = []
        for i, seg in enumerate(per_image_results):
            per_image_narrations.append({
                "path": seg["path"],
                "duration": seg["duration"],
                "text": captions[i] if i < len(captions) else "",
            })

        # --- Music ---
        vibe = req.audio.lower() if req.audio else "calm"
        valid_vibes = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
        if vibe not in valid_vibes:
            vibe = "calm"

        try:
            from ai.audio import generate_music
            music_path = generate_music(vibe, output_dir)
        except Exception:
            music_path = ""

        rel_music_path = file_service.relative_path(music_path) if music_path else ""
        db_service.save_music(project_id, vibe, "ai", rel_music_path)
        db_service.update_project_status(project_id, "music_ready")

        # --- Video Assembly ---
        db_service.update_project_status(project_id, "assembling")

        from ai.video import assemble_video as build_video
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