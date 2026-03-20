# app/api/routes/music.py  — POST /music
# Generates or fetches background music based on mood/vibe.

import os
from fastapi import APIRouter, HTTPException
from app.models.schemas import MusicRequest, MusicResponse, TrackSuggestion
from app.services import db_service, file_service
from app.config import settings

router = APIRouter()

@router.post("/music", response_model=MusicResponse)
async def get_music(body: MusicRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    valid_vibes = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
    if body.vibe not in valid_vibes:
        raise HTTPException(status_code=400, detail=f"Invalid vibe. Choose from: {valid_vibes}")

    output_dir   = file_service.get_project_output_dir(body.project_id)
    music_path   = None
    suggestions  = []

    if body.source == "ai":
        # Generate music using MusicGen
        try:
            from ai.audio import generate_music
            music_path = generate_music(body.vibe, output_dir)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pipeline error at music generation: {str(e)}")

    elif body.source == "library":
        # Fetch from Freesound API
        try:
            music_path, suggestions = _fetch_from_freesound(body.vibe, output_dir)
        except Exception as e:
            # Graceful fallback to AI if Freesound is down
            try:
                from ai.audio import generate_music
                music_path  = generate_music(body.vibe, output_dir)
                suggestions = []
            except Exception as e2:
                raise HTTPException(status_code=503, detail="Music library unavailable. Switching to AI generation.")
    else:
        raise HTTPException(status_code=400, detail="source must be 'ai' or 'library'.")

    db_service.save_music(body.project_id, body.vibe, body.source, music_path)
    db_service.update_project_status(body.project_id, "music_ready")

    return MusicResponse(
        project_id=body.project_id,
        music_path=music_path,
        suggestions=suggestions,
    )


def _fetch_from_freesound(vibe: str, output_dir: str):
    """Call Freesound API and download top 3 matching tracks."""
    import requests

    api_key  = settings.FREESOUND_API_KEY
    if not api_key:
        raise Exception("Freesound API key not configured.")

    # Search for tracks matching the vibe
    resp = requests.get(
        "https://freesound.org/apiv2/search/text/",
        params={
            "query":    vibe,
            "filter":   "duration:[10 TO 120]",
            "fields":   "id,name,previews",
            "token":    api_key,
            "page_size": 3,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data     = resp.json()
    results  = data.get("results", [])

    if not results:
        raise Exception("No tracks found on Freesound.")

    suggestions = []
    main_path   = None

    for i, track in enumerate(results):
        preview_url  = track["previews"]["preview-lq-mp3"]
        track_name   = track["name"]
        filename     = f"freesound_{vibe}_{i+1}.mp3"
        local_path   = os.path.join(output_dir, filename)

        audio_resp = requests.get(preview_url, timeout=15)
        with open(local_path, "wb") as f:
            f.write(audio_resp.content)

        if i == 0:
            main_path = local_path  # First track is the default pick

        suggestions.append(TrackSuggestion(name=track_name, path=local_path))

    return main_path, suggestions
