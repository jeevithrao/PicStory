# app/services/db_service.py
# All database read/write operations in one place.
# Routes and services import functions from here — no raw SQL anywhere else.
import os
import uuid
from app.db.connection import get_connection


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def create_project(mode: str, language: str, audio_vibe: str = "calm", prompt: str = None, context: str = None) -> str:
    """Insert a new project row. Returns the new project_id (UUID)."""
    project_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO projects (id, mode, prompt, context, language, audio_vibe, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (project_id, mode, prompt, context, language, audio_vibe, "uploaded")
        )
        conn.commit()
    finally:
        conn.close()
    return project_id


def get_project(project_id: str) -> dict | None:
    """Return project row as dict, or None if not found."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        return cur.fetchone()
    finally:
        conn.close()


def update_project_status(project_id: str, status: str):
    """Update the pipeline status of a project."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE projects SET status = %s WHERE id = %s", (status, project_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def save_images(project_id: str, filenames: list[str]):
    """Insert image rows for a project (initial order = list index)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        rows = [(project_id, fname, idx) for idx, fname in enumerate(filenames)]
        cur.executemany(
            "INSERT INTO images (project_id, filename, display_order) VALUES (%s, %s, %s)",
            rows
        )
        conn.commit()
    finally:
        conn.close()


def get_images(project_id: str) -> list[dict]:
    """Return all non-removed images for a project, ordered by display_order."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM images WHERE project_id = %s AND is_removed = 0 ORDER BY display_order",
            (project_id,)
        )
        return cur.fetchall()
    finally:
        conn.close()


def apply_image_edits(project_id: str, ordered_images: list[str], removed_images: list[str]):
    """Save user's drag-and-drop edits: update order + mark removed images."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Mark removed images
        for fname in removed_images:
            cur.execute(
                "UPDATE images SET is_removed = 1 WHERE project_id = %s AND filename = %s",
                (project_id, fname)
            )
        # Update display order
        for idx, fname in enumerate(ordered_images):
            cur.execute(
                "UPDATE images SET display_order = %s WHERE project_id = %s AND filename = %s",
                (idx, project_id, fname)
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------

def save_captions(project_id: str, captions: list[dict]):
    """
    Save captions for all images.
    Each dict: { image_filename, caption_en, caption_translated }
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        rows = [(project_id, c["image_filename"], c["caption_en"], c["caption_translated"]) for c in captions]
        cur.executemany(
            "INSERT INTO captions (project_id, image_filename, caption_en, caption_translated) VALUES (%s, %s, %s, %s)",
            rows
        )
        conn.commit()
    finally:
        conn.close()


def get_captions(project_id: str) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM captions WHERE project_id = %s", (project_id,))
        return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Narrations
# ---------------------------------------------------------------------------

def save_narration(project_id: str, narration_text: str, narration_path: str, language: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO narrations (project_id, narration_text, narration_path, language) VALUES (%s, %s, %s, %s)",
            (project_id, narration_text, narration_path, language)
        )
        conn.commit()
    finally:
        conn.close()


def get_narration(project_id: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM narrations WHERE project_id = %s ORDER BY id DESC LIMIT 1", (project_id,))
        return cur.fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Music
# ---------------------------------------------------------------------------

def save_music(project_id: str, vibe: str, source: str, music_path: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO music (project_id, vibe, source, music_path) VALUES (%s, %s, %s, %s)",
            (project_id, vibe, source, music_path)
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def save_output(project_id: str, video_path: str, caption: str, hashtags: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO outputs (project_id, video_path, caption, hashtags) VALUES (%s, %s, %s, %s)",
            (project_id, video_path, caption, hashtags)
        )
        conn.commit()
    finally:
        conn.close()


def get_output(project_id: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM outputs WHERE project_id = %s ORDER BY id DESC LIMIT 1", (project_id,))
        return cur.fetchone()
    finally:
        conn.close()


def save_video_output(project_id: str, video_path: str):
    """Upsert video path into outputs (in case social ran first or ran concurrently)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM outputs WHERE project_id = %s", (project_id,))
        if cur.fetchone():
            cur.execute("UPDATE outputs SET video_path = %s WHERE project_id = %s", (video_path, project_id))
        else:
            cur.execute(
                "INSERT INTO outputs (project_id, video_path, caption, hashtags) VALUES (%s, %s, %s, %s)",
                (project_id, video_path, "", "")
            )
        conn.commit()
    finally:
        conn.close()


def save_video_blob(project_id: str, local_file_path: str):
    """Reads a local binary file and saves it to the video_blob column."""
    with open(local_file_path, "rb") as f:
        blob_data = f.read()

    conn = get_connection()
    try:
        cur = conn.cursor()
        # Ensure row exists first
        cur.execute("SELECT id FROM outputs WHERE project_id = %s", (project_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO outputs (project_id, video_path, video_blob, caption, hashtags) VALUES (%s, %s, %s, %s, %s)",
                (project_id, "", blob_data, "", "")
            )
        else:
            cur.execute("UPDATE outputs SET video_blob = %s WHERE project_id = %s", (blob_data, project_id))
        conn.commit()
    finally:
        conn.close()


def save_image_blobs(project_id: str, image_paths: list[str]):
    conn = get_connection()
    try:
        cur = conn.cursor()
        for path in image_paths:
            if not os.path.exists(path): continue
            with open(path, "rb") as f:
                blob_data = f.read()
            fname = os.path.basename(path)
            cur.execute("UPDATE images SET image_blob = %s WHERE project_id = %s AND filename = %s", (blob_data, project_id, fname))
        conn.commit()
    finally:
        conn.close()


def save_narration_blob(project_id: str, local_file_path: str):
    if not local_file_path or not os.path.exists(local_file_path): return
    with open(local_file_path, "rb") as f:
        blob_data = f.read()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE narrations SET narration_blob = %s WHERE project_id = %s", (blob_data, project_id))
        conn.commit()
    finally:
        conn.close()


def save_music_blob(project_id: str, local_file_path: str):
    if not local_file_path or not os.path.exists(local_file_path): return
    with open(local_file_path, "rb") as f:
        blob_data = f.read()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE music SET music_blob = %s WHERE project_id = %s", (blob_data, project_id))
        conn.commit()
    finally:
        conn.close()


def save_zip_blob(project_id: str, zip_data: bytes):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE projects SET zip_blob = %s WHERE id = %s", (zip_data, project_id))
        conn.commit()
    finally:
        conn.close()