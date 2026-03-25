# app/api/routes/caption.py  — POST /caption
# Runs BLIP on all project images → enhances with Gemini directly in target language.
# Streams progress to the frontend via SSE.

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import CaptionRequest, CaptionResponse, CaptionItem
from app.services import db_service, file_service
from app.config import settings
import json
import asyncio

router = APIRouter()

@router.post("/caption", response_model=CaptionResponse)
async def generate_captions(body: CaptionRequest):
    # Backward compatibility endpoint. We now use /caption-stream via GET.
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

    # Get user context from project
    context = project.get("context", "") or ""

    # --- Call BLIP + Gemini captioning (now outputs in target language) ---
    try:
        from ai.captioning import generate_captions as blip_caption
        enhanced_captions = blip_caption(image_paths, language=body.language, context=context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at captioning: {str(e)}")

    # Save to DB — caption_translated holds the language-native Gemini output
    caption_data = [
        {
            "image_filename":      filenames[i],
            "caption_en":          enhanced_captions[i],  # Same as translated for now
            "caption_translated":  enhanced_captions[i],
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

@router.get("/caption-stream/{project_id}/{language}")
async def stream_captions(project_id: str, language: str):
    """
    Server-Sent Events (SSE) endpoint for live progressive reveal.
    Yields JSON events for each image as it is captioned.
    Gemini outputs descriptions directly in the target language.
    """
    project = db_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if language not in settings.SUPPORTED_LANGUAGES and language != "en":
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    images       = db_service.get_images(project_id)
    project_dir  = file_service.get_project_upload_dir(project_id)
    filenames    = [img["filename"] for img in images]
    image_paths  = [f"{project_dir}/{fname}" for fname in filenames]

    # Get user context from project
    context = project.get("context", "") or ""

    db_service.update_project_status(project_id, "captioning")

    async def event_stream():
        # First, send all images so the frontend can display the grid immediately
        for fname in filenames:
            rel_path = file_service.relative_path(f"{project_dir}/{fname}")
            data = {"type": "image", "filename": fname, "url": rel_path}
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.1) # small delay for UI effect

        # Now, load BLIP model
        try:
            from app.services.model_manager import load_blip, unload_blip
            model, processor = load_blip()
        except Exception as e:
            error_data = {"type": "error", "message": f"Failed to load model: {str(e)}"}
            yield f"data: {json.dumps(error_data)}\n\n"
            return

        from PIL import Image
        import torch

        english_captions = []
        # Process image by image to stream progress
        for i, path in enumerate(image_paths):
            fname = filenames[i]
            caption = "A photo."
            try:
                raw_image = Image.open(path).convert("RGB")
                inputs = processor(raw_image, return_tensors="pt").to(model.device)
                output_ids = model.generate(**inputs, max_new_tokens=50)
                caption = processor.decode(output_ids[0], skip_special_tokens=True).strip()
            except Exception as e:
                print(f"⚠️  BLIP failed on {path}: {e}")

            english_captions.append(caption)
            # Send raw caption event (shows progress before emotional enhancement)
            progress_data = {"type": "progress", "filename": fname, "caption": caption}
            yield f"data: {json.dumps(progress_data)}\n\n"
            await asyncio.sleep(0.01)

        unload_blip()
        
        # Now enhance with Gemini — directly in the target language
        from ai.captioning import LANG_NAMES
        lang_name = LANG_NAMES.get(language, language.upper())
        progress_data = {"type": "info", "message": f"Enhancing descriptions in {lang_name}..."}
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        from ai.captioning import _enhance_captions_with_gemini
        enhanced_captions = _enhance_captions_with_gemini(
            english_captions, language=language, context=context
        )
        
        # Gemini already outputs in the target language — no translation needed
        db_captions = []
        for i, fname in enumerate(filenames):
            en_cap = enhanced_captions[i]
            
            db_captions.append({
                "image_filename":      fname,
                "caption_en":          english_captions[i],  # Keep raw English BLIP caption
                "caption_translated":  en_cap,               # Gemini-enhanced in target language
            })
            
            caption_data = {
                "type": "caption",
                "filename": fname,
                "caption_en": english_captions[i],
                "caption_translated": en_cap
            }
            yield f"data: {json.dumps(caption_data)}\n\n"
            await asyncio.sleep(0.2) # Staggered reveal
            
        # Save to DB
        db_service.save_captions(project_id, db_captions)
        db_service.update_project_status(project_id, "captioned")
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
