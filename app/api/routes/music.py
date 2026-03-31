# app/api/routes/music.py
import os
import shutil
from fastapi import APIRouter, HTTPException
from app.models.schemas import MusicRequest, MusicResponse
from app.services import db_service, file_service

router = APIRouter()

VALID_VIBES = ["calm", "romantic", "happy", "sad", "motivational", 
    "cinematic", "rock", "hip-hop", "cultural", "electric", 
    "lo-fi", "emotional"]

# Point to your new local music folder
LOCAL_MUSIC_DIR = os.path.join(os.getcwd(), "assets", "music")

@router.post("/music", response_model=MusicResponse)
async def get_music(body: MusicRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    vibe = body.vibe
    ai_suggested_vibe = None

    # --- 1. Gemini AI auto-picks vibe if frontend sends empty vibe ---
    if not vibe:
        try:
            captions_rows = db_service.get_captions(body.project_id)
            if captions_rows:
                from ai.story import suggest_music_vibe
                captions_text = [row["caption_en"] for row in captions_rows]
                ai_suggested_vibe = suggest_music_vibe(captions_text)
                vibe = ai_suggested_vibe
                print(f"🎵 Gemini suggested vibe: {vibe}")
        except Exception as e:
            print(f"⚠️ Gemini vibe suggestion failed: {e}")

    # Fallback if AI fails or vibe is invalid
    if vibe not in VALID_VIBES:
        vibe = "calm"

    # --- 2. Grab the local file ---
    source_file = os.path.join(LOCAL_MUSIC_DIR, f"{vibe}.mp3")
    
    # If you forgot to add the mp3 to the folder, fallback to calm
    if not os.path.exists(source_file):
        print(f"⚠️ Missing file {vibe}.mp3 in assets/music/. Falling back to calm.mp3")
        source_file = os.path.join(LOCAL_MUSIC_DIR, "calm.mp3")

    # --- 3. Copy to the user's project folder ---
    output_dir = file_service.get_project_output_dir(body.project_id)
    dest_file = os.path.join(output_dir, f"bgm_{vibe}.mp3")
    
    try:
        shutil.copy(source_file, dest_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy local music: {str(e)}")

    rel_path = file_service.relative_path(dest_file)
    db_service.save_music(body.project_id, vibe, "local", rel_path)
    db_service.update_project_status(body.project_id, "music_ready")

    return MusicResponse(
        project_id=body.project_id,
        music_path=rel_path,
        suggestions=[], # We don't need suggestions anymore since they chose from the UI
        ai_suggested_vibe=ai_suggested_vibe or vibe,
    )