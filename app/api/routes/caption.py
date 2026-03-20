# app/api/routes/caption.py  — POST /caption
# Runs BLIP on all project images → English captions → translates via IndicTrans2.

from fastapi import APIRouter, HTTPException
from app.models.schemas import CaptionRequest, CaptionResponse, CaptionItem
from app.services import db_service, file_service
from app.services.translation_service import translate_batch
from app.config import settings

router = APIRouter()

@router.post("/caption", response_model=CaptionResponse)
async def generate_captions(body: CaptionRequest):
    # Validate project exists
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    # Validate language
    if body.language not in settings.SUPPORTED_LANGUAGES and body.language != "en":
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.language}")

    db_service.update_project_status(body.project_id, "captioning")

    # Get image paths
    images       = db_service.get_images(body.project_id)
    project_dir  = file_service.get_project_upload_dir(body.project_id)
    image_paths  = [f"{project_dir}/{img['filename']}" for img in images]
    filenames    = [img["filename"] for img in images]

    # --- Call teammate's BLIP module ---
    try:
        from ai.captioning import generate_captions as blip_caption
        english_captions = blip_caption(image_paths)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at captioning: {str(e)}")

    # Translate captions to chosen language
    translated_captions = translate_batch(english_captions, body.language)

    # Save to DB
    caption_data = [
        {
            "image_filename":      filenames[i],
            "caption_en":          english_captions[i],
            "caption_translated":  translated_captions[i],
        }
        for i in range(len(filenames))
    ]
    db_service.save_captions(body.project_id, caption_data)
    db_service.update_project_status(body.project_id, "captioned")

    return CaptionResponse(
        project_id=body.project_id,
        captions=[
            CaptionItem(
                image_name=d["image_filename"],
                caption_en=d["caption_en"],
                caption_translated=d["caption_translated"],
            ) for d in caption_data
        ]
    )
