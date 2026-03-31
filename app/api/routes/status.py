# app/api/routes/status.py  — GET /status/{project_id}
# Polling endpoint — frontend calls this repeatedly to update the UI.
# Also includes /caption-stream for real-time caption streaming

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import StatusResponse
from app.services import db_service
import json

router = APIRouter()

STATUS_MESSAGES = {
    "uploaded":        "Images received and ready for captioning.",
    "generating":      "Stable Diffusion is generating your images...",
    "captioning":      "BLIP is analyzing and describing your images...",
    "captioned":       "Captions ready! Select a music vibe to continue.",
    "music_ready":     "Background music selected. Ready to generate narration.",
    "narration_ready": "Voiceover ready. Review and edit your image order.",
    "editing":         "Image arrangement saved. Ready to assemble video.",
    "assembling":      "Assembling your final video... this may take a minute.",
    "completed":       "Your video is ready for download!",
    "error":           "Something went wrong. Please check the logs.",
}

@router.get("/status/{project_id}", response_model=StatusResponse)
async def get_status(project_id: str):
    project = db_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    status  = project["status"]
    message = STATUS_MESSAGES.get(status, "Processing...")

    return StatusResponse(
        project_id=project_id,
        status=status,
        message=message,
    )


@router.get("/caption-stream/{project_id}/{language}")
async def caption_stream(project_id: str, language: str):
    """
    Server-Sent Events (SSE) endpoint for streaming captions in real-time.
    Frontend connects to this endpoint to receive caption updates as they're generated.
    """
    
    project = db_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    images = db_service.get_images(project_id)
    if not images:
        raise HTTPException(status_code=400, detail="No images found for project")

    async def generate_stream():
        """Generator function that yields SSE events."""
        from ai.captioning import generate_captions as vision_caption
        from app.services import file_service
        import os
        
        try:
            # Stream initial image info
            for img in images:
                filename = img["filename"]
                # Construct the image path
                project_dir = file_service.get_project_upload_dir(project_id)
                img_path = os.path.join(project_dir, filename)
                img_url = file_service.relative_path(img_path)
                
                event = json.dumps({
                    "type": "image",
                    "filename": filename,
                    "url": img_url
                })
                yield f"data: {event}\n\n"
            
            # Get the context from project
            context = project.get("context", "") or project.get("prompt", "")
            
            # Convert language display names to code
            from app.api.routes.api_prepare import _map_language_to_code
            language_code = _map_language_to_code(language)
            
            # Get image paths for captioning
            project_dir = file_service.get_project_upload_dir(project_id)
            image_paths = [
                os.path.join(project_dir, img["filename"]) 
                for img in images
            ]
            
            # Send progress event
            yield f"data: {json.dumps({'type': 'progress', 'filename': 'Starting caption generation...'})}\n\n"
            
            # Generate captions
            captions = vision_caption(image_paths, language=language_code, context=context)
            
            # Save captions to DB and stream them
            caption_data = []
            for i, img in enumerate(images):
                if i < len(captions):
                    caption_text = captions[i]
                    
                    caption_data.append({
                        "image_filename": img["filename"],
                        "caption_en": caption_text,
                        "caption_translated": caption_text,
                    })
                    
                    # Stream the caption event to frontend
                    event = json.dumps({
                        "type": "caption",
                        "filename": img["filename"],
                        "caption_en": caption_text,
                        "caption_translated": caption_text
                    })
                    yield f"data: {event}\n\n"
            
            # Save all captions to DB
            db_service.save_captions(project_id, caption_data)
            db_service.update_project_status(project_id, "captioned")
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'done', 'message': 'Captions generation complete'})}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"Caption generation failed: {str(e)}"
            print(f"⚠️ {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )
