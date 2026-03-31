# app/api/routes/status.py  — GET /status/{project_id}
# Polling endpoint — frontend calls this repeatedly to update the UI.

from fastapi import APIRouter, HTTPException
from app.models.schemas import StatusResponse
from app.services import db_service

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