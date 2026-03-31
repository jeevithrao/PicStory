# app/api/routes/social.py  — POST /social
# Generates social media captions + hashtags via Gemini API.

import requests
from fastapi import APIRouter, HTTPException
from app.models.schemas import SocialRequest, SocialResponse
from app.services import db_service
from app.config import settings

router = APIRouter()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

@router.post("/social", response_model=SocialResponse)
async def generate_social(body: SocialRequest):
    project = db_service.get_project(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Check your project_id.")

    # Fetch captions for context
    captions_rows = db_service.get_captions(body.project_id)
    captions_text = " ".join([row["caption_en"] for row in captions_rows])
    topic         = project.get("context") or captions_text[:200]

    # Build Gemini prompt
    prompt = f"""
You are a social media expert. Generate a ready-to-post social media caption and hashtags for a {body.platform} post.

Topic/Story: {topic}
Language for caption: {body.language}
Platform: {body.platform}

Requirements:
- Write the caption in the specified language ({body.language})
- Caption should be engaging, emotional, and relevant to the topic
- Generate exactly 18 hashtags: mix of niche (specific) and trending (popular) ones
- Hashtags should be in English

Respond in this exact JSON format:
{{
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", ...]
}}
"""

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": settings.GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        raw     = resp.json()
        content = raw["candidates"][0]["content"]["parts"][0]["text"]

        # Parse JSON response from Gemini
        import json, re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            raise ValueError("Could not parse Gemini response as JSON.")
        result   = json.loads(json_match.group())
        caption  = result.get("caption", "")
        hashtags = result.get("hashtags", [])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error at social copy: {str(e)}")

    # Save to DB
    hashtags_str = ",".join(hashtags)
    narration    = db_service.get_narration(body.project_id)
    output       = db_service.get_output(body.project_id)
    if output:
        pass  # Already saved from /video
    else:
        db_service.save_output(body.project_id, "", caption, hashtags_str)

    return SocialResponse(caption=caption, hashtags=hashtags)
