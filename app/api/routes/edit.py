# app/api/routes/edit.py  — POST /edit
# Saves user's drag-and-drop image edits (reorder, remove, add).

from fastapi import APIRouter, HTTPException
from app.models.schemas import EditRequest, EditResponse
from app.services import db_service

router = APIRouter()

@router.post("/edit", response_model=EditResponse)
async def save_edits(body: EditRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    # Apply edits to DB (update order + mark removed)
    db_service.apply_image_edits(
        project_id=body.project_id,
        ordered_images=body.ordered_images,
        removed_images=body.removed_images,
    )
    db_service.update_project_status(body.project_id, "editing")

    final_count = len(body.ordered_images)

    return EditResponse(
        project_id=body.project_id,
        final_image_count=final_count,
        message=f"Image arrangement saved. {final_count} images in final order.",
    )