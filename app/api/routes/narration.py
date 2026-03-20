# app/api/routes/narration.py  — POST /narration
# Generates narration script via Gemini, then TTS via Edge TTS.

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

    english_captions = [row["caption_en"] for row in captions_rows]
    output_dir       = file_service.get_project_output_dir(body.project_id)

    # --- Call teammate's LLM narration module ---
    try:
        from ai.story import generate_narration_script
        narration_text = generate_narration_script(
            captions=english_captions,
            language=body.language,
            model="gemini",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at narration: {str(e)}")

    # --- Call teammate's TTS module ---
    try:
        from ai.audio import generate_voiceover
        narration_path = generate_voiceover(
            script=narration_text,
            language=body.language,
            output_dir=output_dir,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at TTS: {str(e)}")

    db_service.save_narration(body.project_id, narration_text, narration_path, body.language)
    db_service.update_project_status(body.project_id, "narration_ready")

    return NarrationResponse(
        project_id=body.project_id,
        narration_text=narration_text,
        narration_path=narration_path,
    )
