# app/api/routes/api_prepare.py
# POST /api/prepare — Phase 1 of the 5-step pipeline.
# ZIP flow:    extracts images, runs BLIP captioning, returns images+captions for editing.
# Prompt flow: placeholder for Nano Banana integration (TODO).

import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services import file_service, db_service

router = APIRouter()


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
                mode="upload", language=language, context=zip_desc
            )

            try:
                image_paths = file_service.extract_zip(zip_bytes, project_id)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            filenames = [os.path.basename(p) for p in image_paths]
            db_service.save_images(project_id, filenames)
            db_service.update_project_status(project_id, "uploaded")

            # --- Run BLIP captioning immediately ---
            db_service.update_project_status(project_id, "captioning")
            from ai.captioning import generate_captions as blip_caption

            enhanced_captions = blip_caption(
                image_paths, language=language, context=zip_desc
            )

            # Save captions to DB
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

            # Build response: image URLs paired with their captions
            image_urls = [
                "/" + file_service.relative_path(p) for p in image_paths
            ]

            images_with_captions = [
                {"url": image_urls[i], "caption": enhanced_captions[i]}
                for i in range(len(image_paths))
            ]

            return {
                "mode": "zip",
                "projectId": project_id,
                "images": images_with_captions,
                "context": zip_desc,
                "language": language,
                "audio": audio,
            }

        # ── PROMPT (AWARENESS) FLOW ──────────────────────────────────
        elif prompt.strip():
            from app.services.translation_service import translate_to_english

            project_id = db_service.create_project(
                mode="awareness", language=language, prompt=prompt
            )
            db_service.update_project_status(project_id, "generating")

            english_prompt = translate_to_english(prompt, language)

            # --- Generate images with Gemini Imagen 3 ---
            from google import genai
            from google.genai import types
            from PIL import Image
            import io

            client = genai.Client()

            image_paths = []
            result = client.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=english_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=4,
                    output_mime_type="image/jpeg",
                    aspect_ratio="16:9",
                ),
            )

            for i, generated_image in enumerate(result.generated_images):
                img_bytes = generated_image.image.image_bytes
                img = Image.open(io.BytesIO(img_bytes))
                fname = f"generated_{i+1}.jpg"
                path = file_service.save_generated_image(img, fname, project_id)
                image_paths.append(path)

            filenames = [os.path.basename(p) for p in image_paths]
            db_service.save_images(project_id, filenames)
            db_service.update_project_status(project_id, "uploaded")

            # --- Run BLIP captioning ---
            db_service.update_project_status(project_id, "captioning")
            from ai.captioning import generate_captions as blip_caption

            enhanced_captions = blip_caption(
                image_paths, language=language, context=prompt
            )

            db_service.update_project_status(project_id, "captioned")

            # --- TTS narration ---
            output_dir = file_service.get_project_output_dir(project_id)

            from ai.audio import generate_per_image_voiceovers, generate_voiceover

            per_image_results = generate_per_image_voiceovers(
                narration_segments=enhanced_captions,
                language=language,
                output_dir=output_dir,
            )

            narration_text = "\n\n".join(enhanced_captions)
            narration_path = generate_voiceover(
                script=narration_text,
                language=language,
                output_dir=output_dir,
            )

            db_service.save_narration(project_id, narration_text, narration_path, language)
            db_service.update_project_status(project_id, "narration_ready")

            per_image_narrations = []
            for i, seg in enumerate(per_image_results):
                per_image_narrations.append({
                    "path": seg["path"],
                    "duration": seg["duration"],
                    "text": enhanced_captions[i] if i < len(enhanced_captions) else "",
                })

            # --- Music ---
            vibe = audio.lower() if audio else "calm"
            valid_vibes = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
            if vibe not in valid_vibes:
                vibe = "calm"

            try:
                from ai.audio import generate_music
                music_path = generate_music(vibe, output_dir)
            except Exception:
                music_path = ""

            # --- Video Assembly ---
            db_service.update_project_status(project_id, "assembling")

            from ai.video import assemble_video as build_video
            video_path = build_video(
                images=image_paths,
                voiceover=None,
                music=music_path,
                output_dir=output_dir,
                voiceover_segments=per_image_narrations,
            )

            db_service.update_project_status(project_id, "completed")
            video_url = "/" + file_service.relative_path(video_path).replace("\\", "/")

            return {
                "mode": "prompt",
                "projectId": project_id,
                "videoUrl": video_url,
            }

        else:
            raise HTTPException(
                status_code=400, detail="Please provide a ZIP file or a prompt."
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prepare error: {str(e)}")
