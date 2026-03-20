# app/api/routes/upload.py  — POST /upload
# Accepts a ZIP file, extracts images, saves to DB, returns project_id.

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.models.schemas import UploadResponse
from app.services import file_service, db_service

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_zip(
    file: UploadFile = File(...),
    language: str = Form(default="hi"),   # Default: Hindi
):
    # Validate file type
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

    zip_bytes = await file.read()

    # Create project record in DB first (get a project_id)
    project_id = db_service.create_project(mode="upload", language=language)

    # Extract images from ZIP
    try:
        image_paths = file_service.extract_zip(zip_bytes, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZIP extraction failed: {str(e)}")

    # Save image records to DB
    filenames = [file_service.relative_path(p) for p in image_paths]
    db_service.save_images(project_id, [p.split("/")[-1] for p in image_paths])
    db_service.update_project_status(project_id, "uploaded")

    return UploadResponse(
        project_id=project_id,
        image_count=len(image_paths),
        image_paths=filenames,
    )
