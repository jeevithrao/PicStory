# app/api/routes/api_prepare.py
# POST /api/prepare — Phase 1 of the 5-step pipeline.
# ZIP flow:    extracts images, runs BLIP captioning, returns images+captions for editing.
# Prompt flow: placeholder for Nano Banana integration (TODO).

import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services import file_service, db_service
from app.config import settings

router = APIRouter()


def _map_language_to_code(language_name: str) -> str:
    """Maps language display names to ISO 639-1/639-3 language codes."""
    language_map = {
        "English": "en",
        "Hindi": "hi",
        "Konkani": "kok",
        "Kannada": "kn",
        "Dogri": "doi",
        "Bodo": "brx",
        "Urdu": "ur",
        "Tamil": "ta",
        "Kashmiri": "ks",
        "Assamese": "as",
        "Bengali": "bn",
        "Marathi": "mr",
        "Sindhi": "sd",
        "Maithili": "mai",
        "Punjabi": "pa",
        "Malayalam": "ml",
        "Manipuri": "mni",
        "Telugu": "te",
        "Sanskrit": "sa",
        "Nepali": "ne",
        "Santali": "sat",
        "Gujarati": "gu",
        "Odia": "or",
    }
    return language_map.get(language_name, language_name.lower()[:2])  # Default to first 2 chars if not found


@router.post("/api/prepare")
async def prepare(
    zip: UploadFile = File(default=None),
    zip_desc: str = Form(default=""),
    prompt: str = Form(default=""),
    language: str = Form(default="English"),
    audio: str = Form(default="calm"),
):
    """
    Step 1-3: Upload/Prompt → Select Language → Select Audio.

    ZIP Mode  → extracts images, generates captions via BLIP + Gemini,
                returns image URLs + editable captions for Step 4.
    Prompt Mode → (TODO) Nano Banana video generation.
    """
    try:
        # ── ZIP UPLOAD FLOW ──────────────────────────────────────────
        if zip is not None:
            if not zip.filename.endswith(".zip"):
                raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

            zip_bytes = await zip.read()
            project_id = db_service.create_project(
                mode="upload", language=language, audio_vibe=audio, context=zip_desc
            )
            db_service.save_zip_blob(project_id, zip_bytes)

            try:
                image_paths = file_service.extract_zip(zip_bytes, project_id)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            filenames = [os.path.basename(p) for p in image_paths]
            db_service.save_images(project_id, filenames)
            db_service.save_image_blobs(project_id, image_paths)
            db_service.update_project_status(project_id, "uploaded")

            # --- Run Gemini Vision captioning (Always in English first) ---
            db_service.update_project_status(project_id, "captioning")
            from ai.captioning import generate_captions as vision_caption
            from app.services.translation_service import translate_batch

            # 1. Generate English captions first
            try:
                captions_en = vision_caption(
                    image_paths, language="en", context=zip_desc
                )
            except Exception as e:
                print(f"[Prepare] vision_caption failed in ZIP mode: {e}. Using generic captions.")
                captions_en = [f"Photo {i+1} of the story" for i in range(len(filenames))]

            # 2. If target language is not English, translate them
            language_code = _map_language_to_code(language)
            if language_code != "en":
                try:
                    captions_translated = translate_batch(captions_en, language_code)
                except Exception as e:
                    print(f"[Prepare] translate_batch failed in ZIP mode: {e}. Using English fallbacks.")

                    captions_translated = captions_en
            else:
                captions_translated = captions_en

            # Save captions to DB
            caption_data = [
                {
                    "image_filename": filenames[i],
                    "caption_en": captions_en[i],
                    "caption_translated": captions_translated[i],
                }
                for i in range(len(filenames))
            ]
            db_service.save_captions(project_id, caption_data)
            db_service.update_project_status(project_id, "captioned")

            # --- AI Music Recommendation ---
            from ai.audio import recommend_music_vibe
            recommended_vibe = recommend_music_vibe(zip_desc, captions_en)

            # Build response: image URLs paired with their captions
            image_urls = [
                "/" + file_service.relative_path(p) for p in image_paths
            ]

            images_with_captions = [
                {"url": image_urls[i], "caption": captions_translated[i]}
                for i in range(len(image_paths))
            ]

            return {
                "mode": "zip",
                "projectId": project_id,
                "images": images_with_captions,
                "context": zip_desc,
                "language": language,
                "audio": audio,
                "recommended_audio": recommended_vibe,
            }



        else:
            raise HTTPException(
                status_code=400, detail="Please provide a ZIP file. Awareness prompt mode is no longer supported."
            )


    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prepare error: {str(e)}")
