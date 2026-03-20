# app/api/routes/video.py  — POST /video
# Assembles final MP4 from images + narration + music using MoviePy/FFmpeg.

from fastapi import APIRouter, HTTPException
from app.models.schemas import VideoRequest, VideoResponse
from app.services import db_service, file_service

router = APIRouter()

@router.post("/video", response_model=VideoResponse)
async def assemble_video(body: VideoRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    db_service.update_project_status(body.project_id, "assembling")

    # Get final ordered image list
    images      = db_service.get_images(body.project_id)  # already filtered: is_removed=0, sorted by display_order
    project_dir = file_service.get_project_upload_dir(body.project_id)
    image_paths = [f"{project_dir}/{img['filename']}" for img in images]

    if not image_paths:
        raise HTTPException(status_code=400, detail="No images found for this project.")

    # Get narration audio path
    narration = db_service.get_narration(body.project_id)
    if not narration:
        raise HTTPException(status_code=404, detail="No narration found. Run /narration first.")

    output_dir = file_service.get_project_output_dir(body.project_id)

    # --- Call teammate's video assembly module ---
    try:
        from ai.video import assemble_video as build_video
        video_path = build_video(
            images=image_paths,
            voiceover=narration["narration_path"],
            music=body.music_path,
            output_dir=output_dir,
        )
    except Exception as e:
        db_service.update_project_status(body.project_id, "error")
        raise HTTPException(status_code=500, detail=f"Pipeline error at video assembly: {str(e)}")

    db_service.update_project_status(body.project_id, "completed")

    return VideoResponse(
        project_id=body.project_id,
        video_path=video_path,
        message="Video assembled successfully. Ready for download.",
    )
