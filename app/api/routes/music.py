# app/api/routes/music.py  — POST /music
# Gemini auto-selects the best vibe from captions.
# Generates or fetches music, returns AI-chosen vibe + alternatives.

import os
from fastapi import APIRouter, HTTPException
from app.models.schemas import MusicRequest, MusicResponse, TrackSuggestion
from app.services import db_service, file_service
from app.config import settings

router = APIRouter()

VALID_VIBES = ["calm", "romantic", "rock", "happy", "sad", "motivational"]

@router.post("/music", response_model=MusicResponse)
async def get_music(body: MusicRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # --- Gemini auto-picks vibe if none specified ---
    vibe = body.vibe
    ai_suggested_vibe = None

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
            print(f"⚠️  Gemini vibe suggestion failed: {e}")

        if not vibe:
            vibe = "calm"  # fallback

    if vibe not in VALID_VIBES:
        vibe = "calm"

    output_dir   = file_service.get_project_output_dir(body.project_id)
    music_path   = None
    suggestions  = []
    source       = body.source or "ai"

    if source == "ai":
        try:
            from ai.audio import generate_music
            music_path = generate_music(vibe, output_dir)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Music generation failed: {str(e)}")

        # Generate alternatives with different vibes
        alt_vibes = [v for v in VALID_VIBES if v != vibe][:3]
        for alt in alt_vibes:
            try:
                alt_path = generate_music(alt, output_dir, filename=f"alt_{alt}.wav")
                suggestions.append(TrackSuggestion(
                    name=f"{alt.title()} vibes",
                    path=file_service.relative_path(alt_path),
                    vibe=alt,
                ))
            except:
                pass

    elif source == "library":
        try:
            music_path, suggestions = _fetch_from_freesound(vibe, output_dir)
        except Exception:
            try:
                from ai.audio import generate_music
                music_path = generate_music(vibe, output_dir)
            except Exception:
                raise HTTPException(status_code=503, detail="Music unavailable.")
    else:
        raise HTTPException(status_code=400, detail="source must be 'ai' or 'library'.")

    rel_path = file_service.relative_path(music_path) if music_path else ""
    db_service.save_music(body.project_id, vibe, source, rel_path)
    db_service.update_project_status(body.project_id, "music_ready")

    return MusicResponse(
        project_id=body.project_id,
        music_path=rel_path,
        suggestions=suggestions,
        ai_suggested_vibe=ai_suggested_vibe or vibe,
    )


def _fetch_from_freesound(vibe: str, output_dir: str):
    """Call Freesound API and download top 3 matching tracks."""
    import requests

    api_key = settings.FREESOUND_API_KEY
    if not api_key or api_key == "your_freesound_key_here":
        raise Exception("Freesound API key not configured.")

    resp = requests.get(
        "https://freesound.org/apiv2/search/text/",
        params={
            "query":     vibe,
            "filter":    "duration:[10 TO 120]",
            "fields":    "id,name,previews",
            "token":     api_key,
            "page_size": 3,
        },
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])

    if not results:
        raise Exception("No tracks found on Freesound.")

    suggestions = []
    main_path = None

    for i, track in enumerate(results):
        preview_url = track["previews"]["preview-lq-mp3"]
        track_name  = track["name"]
        filename    = f"freesound_{vibe}_{i+1}.mp3"
        local_path  = os.path.join(output_dir, filename)

        audio_resp = requests.get(preview_url, timeout=15)
        with open(local_path, "wb") as f:
            f.write(audio_resp.content)

        if i == 0:
            main_path = local_path

        suggestions.append(TrackSuggestion(
            name=track_name,
            path=file_service.relative_path(local_path),
            vibe=vibe,
        ))

    return main_path, suggestions
