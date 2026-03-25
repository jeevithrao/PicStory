# app/api/routes/narration.py  — POST /narration
# Generates per-image narration segments via Gemini, then TTS via Edge TTS.
# Each image gets its own narration segment for synced slideshow video.

from fastapi import APIRouter, HTTPException
from app.models.schemas import NarrationRequest, NarrationResponse
from app.services import db_service, file_service
from app.config import settings

router = APIRouter()

@router.post("/narration", response_model=NarrationResponse)
async def generate_narration(body: NarrationRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    # Fetch captions to build the narration from
    captions_rows = db_service.get_captions(body.project_id)
    if not captions_rows:
        raise HTTPException(status_code=404, detail="No captions found. Run /caption first.")

    # Use the translated captions (which are now in the target language) for narration
    captions_for_narration = [row["caption_translated"] for row in captions_rows]
    output_dir = file_service.get_project_output_dir(body.project_id)

    # --- Generate per-image narration segments ---
    try:
        from ai.story import generate_per_image_narration, generate_narration_script
        narration_segments = generate_per_image_narration(
            captions=captions_for_narration,
            language=body.language,
        )
        # Also generate the full narration script for display
        narration_text = "\n\n".join(narration_segments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at narration: {str(e)}")

    # --- Generate per-image TTS voiceovers ---
    try:
        from ai.audio import generate_per_image_voiceovers, generate_voiceover
        per_image_results = generate_per_image_voiceovers(
            narration_segments=narration_segments,
            language=body.language,
            output_dir=output_dir,
        )
        # Also generate a combined voiceover for preview playback
        narration_path = generate_voiceover(
            script=narration_text,
            language=body.language,
            output_dir=output_dir,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at TTS: {str(e)}")

    # Build per_image_narrations list with text included
    per_image_narrations = []
    for i, seg in enumerate(per_image_results):
        per_image_narrations.append({
            "path": seg["path"],
            "duration": seg["duration"],
            "text": narration_segments[i] if i < len(narration_segments) else "",
        })

    db_service.save_narration(body.project_id, narration_text, narration_path, body.language)
    db_service.update_project_status(body.project_id, "narration_ready")

    return NarrationResponse(
        project_id=body.project_id,
        narration_text=narration_text,
        narration_path=narration_path,
        per_image_narrations=per_image_narrations,
    )
