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
                print(f"⚠️ vision_caption failed in ZIP mode: {e}. Using generic captions.")
                captions_en = [f"Photo {i+1} of the story" for i in range(len(filenames))]

            # 2. If target language is not English, translate them
            language_code = _map_language_to_code(language)
            if language_code != "en":
                try:
                    captions_translated = translate_batch(captions_en, language_code)
                except Exception as e:
                    print(f"⚠️ translate_batch failed in ZIP mode: {e}. Using English fallbacks.")
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
            }

        # ── PROMPT (AWARENESS) FLOW ──────────────────────────────────
        elif prompt.strip():
            from app.services.translation_service import translate_to_english

            project_id = db_service.create_project(
                mode="awareness", language=language, audio_vibe=audio, prompt=prompt
            )
            db_service.update_project_status(project_id, "generating")

            english_prompt = translate_to_english(prompt, language)

            from app.services.gemini_service import call_gemini_with_retry
            from google.genai import types
            from PIL import Image
            import io

            # Scene variations so each image is visually distinct
            scene_prompts = [
                f"Scene 1 of a visual story: {english_prompt}. Opening scene, wide establishing shot.",
                f"Scene 2 of a visual story: {english_prompt}. Middle of the story, close-up detail.",
                f"Scene 3 of a visual story: {english_prompt}. Emotional climax, dramatic lighting.",
                f"Scene 4 of a visual story: {english_prompt}. Final scene, hopeful and uplifting.",
            ]

            image_paths = []
            for i, scene_prompt in enumerate(scene_prompts):
                config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
                try:
                    response = call_gemini_with_retry(
                        prompt=scene_prompt,
                        model="gemini-2.0-flash-exp-image-generation",
                        config=config,
                        return_raw=True
                    )
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                            img = Image.open(io.BytesIO(part.inline_data.data))
                            fname = f"generated_{i+1}.jpg"
                            path = file_service.save_generated_image(img, fname, project_id)
                            image_paths.append(path)
                            print(f"✅ Generated image {i+1}/4")
                            break
                except Exception as e:
                    print(f"⚠️ Failed to generate image {i+1}: {e}")
                    # Try once more with a simpler prompt on failure
                    try:
                        response = call_gemini_with_retry(
                            prompt=english_prompt,
                            model="gemini-2.0-flash-exp-image-generation",
                            config=config,
                            return_raw=True
                        )
                        for part in response.candidates[0].content.parts:
                            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                                img = Image.open(io.BytesIO(part.inline_data.data))
                                fname = f"generated_{i+1}.jpg"
                                path = file_service.save_generated_image(img, fname, project_id)
                                image_paths.append(path)
                                print(f"✅ Generated image {i+1}/4 (retry ok)")
                                break
                    except Exception as e2:
                        print(f"❌ Image {i+1} retry also failed: {e2}")

            if not image_paths:
                raise HTTPException(
                    status_code=500,
                    detail="Image generation failed for all 4 scenes. Check your GEMINI_API_KEY and ensure it is a valid Google AI Studio key from https://aistudio.google.com/app/apikey"
                )

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
                    image_paths, language="en", context=prompt
                )
            except Exception as e:
                print(f"⚠️ Vision Captioning failed: {e}. Using prompt segments as fallback...")
                # Fallback: Just split the original prompt if vision fails
                captions_en = [f"Part {i+1}: " + prompt[:100] for i in range(4)]

            # 2. If target language is not English, translate them
            language_code = _map_language_to_code(language)
            if language_code != "en":
                captions_translated = translate_batch(captions_en, language_code)
            else:
                captions_translated = captions_en

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

            # --- TTS narration ---
            output_dir = file_service.get_project_output_dir(project_id)

            from ai.audio import generate_per_image_voiceovers, generate_voiceover

            per_image_results = generate_per_image_voiceovers(
                narration_segments=captions_translated,
                language=language,
                output_dir=output_dir,
            )

            narration_text = "\n\n".join(captions_translated)
            narration_res = generate_voiceover(
                script=narration_text,
                language=language,
                output_dir=output_dir,
            )
            narration_path = narration_res["path"]
            narration_status = narration_res["status"]

            db_service.save_narration(project_id, narration_text, narration_path, language)
            db_service.save_narration_blob(project_id, narration_path)
            db_service.update_project_status(project_id, "narration_ready")

            per_image_narrations = []
            for i, seg in enumerate(per_image_results):
                per_image_narrations.append({
                    "path": seg["path"],
                    "duration": seg["duration"],
                    "text": captions_translated[i] if i < len(captions_translated) else "",
                    "status": seg.get("status", "audio_ok")
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
