# app/api/routes/wrapper_endpoints.py
# Frontend-facing endpoints that wrap the internal /api/prepare and /api/render
# This allows the frontend to continue using familiar endpoint names
# while we use the new awareness-aware internal endpoints.

import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from app.services import file_service, db_service

router = APIRouter()


class ImageCaption(BaseModel):
    url: str
    caption: str


class VideoRequest(BaseModel):
    project_id: str
    music_path: str
    per_image_narrations: list[dict] = None
    awareness_narration: list[str] = None  # NEW: awareness narration segments


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    language: str = Form(default="hi"),
    context: str = Form(default=""),
):
    """
    Wrapper for /api/prepare ZIP mode.
    Frontend calls this to upload a ZIP file and get images + captions.
    Now also returns awarenessLecture and awarenessNarration if context contains "awareness".
    """
    from app.api.routes.api_prepare import prepare
    
    try:
        result = await prepare(zip=file, zip_desc=context, language=language)
        
        # Build response that includes awareness data if present
        response = {
            "project_id": result["projectId"],
            "image_count": len(result["images"]),
            
            "image_paths": [img["url"] for img in result["images"]],
        }
        
        # Include awareness data if available
        if result.get("isAwarenessMode"):
            response["isAwarenessMode"] = True
        
        if result.get("awarenessLecture"):
            response["awarenessLecture"] = result["awarenessLecture"]
        
        if result.get("awarenessNarration"):
            response["awarenessNarration"] = result["awarenessNarration"]
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@router.post("/video")
async def assemble_video(req: VideoRequest):
    """
    Wrapper for /api/render.
    Frontend calls this to assemble the final video.
    Now accepts awareness_narration for cinematic PSA-style voiceovers.
    """
    from app.api.routes.api_render import render
    from app.models.schemas import ImageCaption as SchemaImageCaption
    from app.models.schemas import RenderRequest as SchemaRenderRequest
    
    try:
        # Get the project to fetch current image order
        project = db_service.get_project(req.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")
        
        # Get current images and captions
        project_images = db_service.get_images(req.project_id)
        project_captions = db_service.get_captions(req.project_id)
        
        if not project_images:
            raise HTTPException(status_code=400, detail="No images found for project.")
        
        # Build caption map by filename
        caption_map = {c["image_filename"]: c.get("caption_translated", c.get("caption_en", "")) for c in project_captions}
        
        # Reconstruct image list with captions in proper order
        images = []
        for img in project_images:
            img_filename = img.get("filename", "")
            caption = caption_map.get(img_filename, "")
            url = f"/uploads/{req.project_id}/{img_filename}"
            images.append(SchemaImageCaption(url=url, caption=caption))
        
        # Create RenderRequest with awareness_narration if provided
        render_req = SchemaRenderRequest(
            projectId=req.project_id,
            images=images,
            language=project.get("language", "hi"),
            audio=project.get("audio", "calm"),
            awareness_narration=req.awareness_narration or [],
        )
        
        result = await render(render_req)
        
        return {
            "project_id": req.project_id,
            "video_path": result["videoUrl"],
            "message": "Video assembled successfully!",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Video assembly error: {str(e)}")
