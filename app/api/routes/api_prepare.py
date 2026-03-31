# app/api/routes/api_prepare.py
# POST /api/prepare — Phase 1 of the 5-step pipeline.
# ZIP flow:    extracts images, runs BLIP captioning (standard) OR
#              generates a single generic awareness caption (awareness mode).
# Awareness mode is triggered any time the word "awareness" appears in zip_desc.

import os
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services import file_service, db_service

router = APIRouter()


@router.post("/api/prepare")
async def prepare(
    zip: UploadFile = File(default=None),
    zip_desc: str = Form(default=""),
    language: str = Form(default="English"),
    audio: str = Form(default="calm"),
):
    """
    Step 1-3: Upload/Prompt → Select Language → Select Audio.

    ZIP Mode (Standard)   → extracts images, runs BLIP + Gemini per-image captioning.
    ZIP Mode (Awareness)  → detects 'awareness' keyword, SKIPS BLIP entirely,
                            generates ONE generic awareness message applied to all images.
    """
    try:
        # ── ZIP UPLOAD FLOW ──────────────────────────────────────────────────────
        if zip is not None:
            if not zip.filename.endswith(".zip"):
                raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

            zip_bytes = await zip.read()
            project_id = db_service.create_project(
                mode="upload", language=language, context=zip_desc
            )

            try:
                image_paths = file_service.extract_zip(zip_bytes, project_id)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            filenames = [os.path.basename(p) for p in image_paths]
            db_service.save_images(project_id, filenames)
            db_service.update_project_status(project_id, "uploaded")

            # ─── DETECT AWARENESS MODE ──────────────────────────────────────────
            # Triggered whenever the word "awareness" appears anywhere in the prompt
            is_awareness_mode = "awareness" in zip_desc.strip().lower()

            enhanced_captions = []
            awareness_narration = []

            if is_awareness_mode:
                # ── AWARENESS MODE ───────────────────────────────────────────────
                # Per-image BLIP captioning is completely SKIPPED.
                # Extract topic: everything after "awareness" keyword
                topic_match = re.search(
                    r'awareness[\s:\-–on]*(.*)', zip_desc.strip(), re.IGNORECASE
                )
                if topic_match and topic_match.group(1).strip():
                    topic = topic_match.group(1).strip()
                else:
                    topic = zip_desc.strip()

                print(f"[awareness] Mode ON — topic='{topic}' — BLIP skipped")
                db_service.update_project_status(project_id, "captioning")

                # Generate N DIFFERENT narrations — one per image — each covering a
                # different angle of the topic. We pass neutral placeholders instead of
                # actual image captions so Gemini focuses 100% on the awareness message.
                from ai.story import generate_per_image_narration
                num_images = len(image_paths)
                placeholder_captions = [
                    f"Awareness image {i + 1} of {num_images}"
                    for i in range(num_images)
                ]

                narration_segments = generate_per_image_narration(
                    placeholder_captions, language, awareness_topic=topic
                )

                # These narrations are both the displayed "caption" and the voiceover
                enhanced_captions = narration_segments
                # N items → render layer uses per-image voiceover mode
                awareness_narration = narration_segments

            else:
                # ── STANDARD MODE ────────────────────────────────────────────────
                # Run per-image BLIP + Gemini captioning as normal
                print("[standard] Running per-image BLIP + Gemini captioning")
                db_service.update_project_status(project_id, "captioning")
                from ai.captioning import generate_captions as blip_caption

                enhanced_captions = blip_caption(
                    image_paths, language=language, context=zip_desc
                )

                # Generate poetic per-image narration from the captions
                from ai.story import generate_per_image_narration
                awareness_narration = generate_per_image_narration(
                    enhanced_captions, language, awareness_topic=None
                )

            # ── Save captions to DB ───────────────────────────────────────────────
            caption_data = [
                {
                    "image_filename": filenames[i],
                    "caption_en": enhanced_captions[i],
                    "caption_translated": enhanced_captions[i],
                }
                for i in range(len(filenames))
            ]
            db_service.save_captions(project_id, caption_data)
            db_service.update_project_status(project_id, "captioned")

            # ── Build response ────────────────────────────────────────────────────
            image_urls = [
                "/" + file_service.relative_path(p) for p in image_paths
            ]

            images_with_captions = [
                {
                    "url": image_urls[i],
                    "caption": enhanced_captions[i] if i < len(enhanced_captions) else "",
                }
                for i in range(len(image_paths))
            ]

            response = {
                "mode": "zip",
                "projectId": project_id,
                "images": images_with_captions,
                "context": zip_desc,
                "language": language,
                "audio": audio,
                "isAwarenessMode": is_awareness_mode,
            }

            if is_awareness_mode:
                # The single awareness message as a lecture text
                response["awarenessLecture"] = enhanced_captions[0] if enhanced_captions else ""
                # One narration segment per image (all identical in awareness mode)
                response["awarenessNarration"] = awareness_narration

            return response

        else:
            raise HTTPException(
                status_code=400, detail="Please provide a ZIP file."
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prepare error: {str(e)}")
