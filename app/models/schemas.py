# app/models/schemas.py
# All Pydantic request/response models for every endpoint.
# FastAPI uses these for automatic validation and /docs generation.

from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# /upload
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    project_id:   str
    image_count:  int
    image_paths:  List[str]


# ---------------------------------------------------------------------------
# /generate
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt:   str
    language: str

class GenerateResponse(BaseModel):
    project_id:  str
    image_count: int
    image_paths: List[str]


# ---------------------------------------------------------------------------
# /caption
# ---------------------------------------------------------------------------
class CaptionRequest(BaseModel):
    project_id: str
    language:   str

class CaptionItem(BaseModel):
    image_name:         str
    caption_en:         str
    caption_translated: str

class CaptionResponse(BaseModel):
    project_id: str
    captions:   List[CaptionItem]


# ---------------------------------------------------------------------------
# /music
# ---------------------------------------------------------------------------
class MusicRequest(BaseModel):
    project_id: str
    vibe:       str   # calm | romantic | rock | happy | sad | motivational
    source:     str   # ai | library

class TrackSuggestion(BaseModel):
    name: str
    path: str

class MusicResponse(BaseModel):
    project_id:  str
    music_path:  str
    suggestions: List[TrackSuggestion]


# ---------------------------------------------------------------------------
# /narration
# ---------------------------------------------------------------------------
class NarrationRequest(BaseModel):
    project_id: str
    language:   str

class NarrationResponse(BaseModel):
    project_id:      str
    narration_text:  str
    narration_path:  str


# ---------------------------------------------------------------------------
# /edit
# ---------------------------------------------------------------------------
class EditRequest(BaseModel):
    project_id:     str
    ordered_images: List[str]   # filenames in new order
    removed_images: List[str]   # filenames the user deleted

class EditResponse(BaseModel):
    project_id:        str
    final_image_count: int
    message:           str


# ---------------------------------------------------------------------------
# /video
# ---------------------------------------------------------------------------
class VideoRequest(BaseModel):
    project_id: str
    music_path: str

class VideoResponse(BaseModel):
    project_id: str
    video_path: str
    message:    str


# ---------------------------------------------------------------------------
# /social
# ---------------------------------------------------------------------------
class SocialRequest(BaseModel):
    project_id: str
    language:   str
    platform:   str   # instagram | youtube | general

class SocialResponse(BaseModel):
    caption:  str
    hashtags: List[str]


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------
class StatusResponse(BaseModel):
    project_id: str
    status:     str
    message:    Optional[str] = None


# ---------------------------------------------------------------------------
# / (health check)
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status:  str
    version: str
