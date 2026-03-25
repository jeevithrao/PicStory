# app/api/routes/generate.py  — POST /generate  (Mode 2 only)
# Translates prompt → English, generates images via Stable Diffusion 1.5.
import os

from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateRequest, GenerateResponse
from app.services import file_service, db_service
from app.services.translation_service import translate_to_english

router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
async def generate_images(body: GenerateRequest):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # Create project record
    project_id = db_service.create_project(
        mode="awareness",
        language=body.language,
        prompt=body.prompt,
    )
    db_service.update_project_status(project_id, "generating")

    # Translate prompt to English for SD
    english_prompt = translate_to_english(body.prompt, body.language)

    # Generate images using Stable Diffusion
    try:
        from app.services.model_manager import load_stable_diffusion, unload_stable_diffusion
        pipeline = load_stable_diffusion()

        image_paths = []
        num_images  = 5  # Generate 5 images per awareness topic

        for i in range(num_images):
            result = pipeline(english_prompt, num_inference_steps=25)
            img    = result.images[0]
            fname  = f"generated_{i+1}.png"
            path   = file_service.save_generated_image(img, fname, project_id)
            image_paths.append(path)

        unload_stable_diffusion()  # Free VRAM immediately

    except Exception as e:
        db_service.update_project_status(project_id, "error")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

    filenames = [os.path.basename(p) for p in image_paths]
    db_service.save_images(project_id, filenames)
    db_service.update_project_status(project_id, "uploaded")

    return GenerateResponse(
        project_id=project_id,
        image_count=len(image_paths),
        image_paths=[file_service.relative_path(p) for p in image_paths],
    )
