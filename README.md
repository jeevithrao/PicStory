<<<<<<< HEAD
# PicStory Backend — Setup & Run Guide

**Team T1 | COMP301 | Project ID: Sec2_P8 | Backend Owner: Jeevith**

---

## Prerequisites

- Python 3.10+
- MySQL 8.0+ running locally
- NVIDIA GPU with 4GB VRAM (for SD + BLIP + MusicGen)
- Git

---

## Step 1 — Clone & enter the project

```bash
git clone <your-repo-url>
cd AI_PROJECT
```

---

## Step 2 — Create virtual environment

```bash
python -m venv venv

# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ This will take a few minutes — torch + transformers are large packages.

---

## Step 4 — Create your `.env` file

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=picstory

GEMINI_API_KEY=your_gemini_key
FREESOUND_API_KEY=your_freesound_key
```

> Get a free Gemini API key at: https://aistudio.google.com/app/apikey
> Get a free Freesound key at: https://freesound.org/apiv2/apply/

---

## Step 5 — Create the MySQL database

MySQL must be running. The server auto-creates the `picstory` database and all 6 tables on first start — you don't need to run any SQL manually.

Just make sure MySQL is up:
```bash
# Mac (Homebrew):
brew services start mysql

# Linux:
sudo systemctl start mysql

# Windows: start MySQL from Services or MySQL Workbench
```

---

## Step 6 — Start the server

```bash
python run.py
```

You should see:
```
✅ Database and all tables ready.
🚀 Starting PicStory backend...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 7 — Verify it's working

Open your browser:

| URL | What you should see |
|-----|---------------------|
| http://localhost:8000/ | `{"status": "ok", "version": "2.0.0"}` |
| http://localhost:8000/docs | Interactive Swagger UI with all 9 endpoints |

---

## Running Tests

```bash
pip install pytest httpx
pytest tests/test_routes.py -v
```

---

## Project Structure

```
AI_PROJECT/
├── app/
│   ├── main.py              ← FastAPI app + router registration
│   ├── config.py            ← Settings loaded from .env
│   ├── api/routes/          ← One file per endpoint
│   │   ├── upload.py        ← POST /upload
│   │   ├── generate.py      ← POST /generate (Mode 2)
│   │   ├── caption.py       ← POST /caption
│   │   ├── music.py         ← POST /music
│   │   ├── narration.py     ← POST /narration
│   │   ├── edit.py          ← POST /edit
│   │   ├── video.py         ← POST /video
│   │   ├── social.py        ← POST /social
│   │   └── status.py        ← GET /status/{project_id}
│   ├── models/schemas.py    ← All Pydantic request/response models
│   ├── services/
│   │   ├── db_service.py    ← All MySQL read/write operations
│   │   ├── file_service.py  ← ZIP extraction, file I/O
│   │   ├── model_manager.py ← GPU model load/unload (VRAM safety)
│   │   └── translation_service.py ← IndicTrans2 wrapper
│   └── db/connection.py     ← MySQL pool + init_db()
├── ai/                      ← Teammate AI modules (plug in here)
│   ├── captioning.py        ← Person 3: BLIP (stub until delivered)
│   ├── story.py             ← Person 4: Gemini narration (stub)
│   ├── audio.py             ← Person 5: TTS + MusicGen (stub)
│   └── video.py             ← Person 6: MoviePy assembly (stub)
├── static/                  ← Frontend HTML/CSS/JS
├── uploads/                 ← Extracted/generated images (gitignored)
├── outputs/                 ← Audio, music, video files (gitignored)
├── tests/test_routes.py     ← Pytest smoke tests
├── run.py                   ← Server entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## API Quick Reference

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload ZIP of photos → get project_id |
| POST | `/generate` | Type awareness prompt → AI generates images |
| POST | `/caption` | Run BLIP → get captions in chosen language |
| POST | `/music` | Get background music (AI or library) |
| POST | `/narration` | Generate voiceover script + audio |
| POST | `/edit` | Save drag-and-drop image reordering |
| POST | `/video` | Assemble final MP4 |
| POST | `/social` | Generate captions + hashtags |
| GET | `/status/{id}` | Poll pipeline progress |

Full interactive docs at: **http://localhost:8000/docs**

---

## For Teammates — Plugging In Your AI Module

Each person delivers **one Python file** inside the `ai/` folder.
The function signatures are fixed — do not change parameter names or return types.

### Person 3 — BLIP Captioning (`ai/captioning.py`)
```python
def generate_captions(image_paths: list[str]) -> list[str]:
    # image_paths: absolute paths to images
    # returns: English caption per image, same order
```

### Person 4 — Narration Script (`ai/story.py`)
```python
def generate_narration_script(captions: list[str], language: str, model: str) -> str:
    # returns: single narration script string
```

### Person 5 — TTS + Music (`ai/audio.py`)
```python
def generate_voiceover(script: str, language: str, output_dir: str) -> str:
    # returns: path to MP3 file

def generate_music(vibe: str, output_dir: str) -> str:
    # returns: path to MP3 file

def detect_mood(script: str) -> str:
    # returns: vibe string
```

### Person 6 — Video Assembly (`ai/video.py`)
```python
def assemble_video(images: list[str], voiceover: str, music: str, output_dir: str) -> str:
    # returns: path to final MP4
```

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Database connection error` | Check MySQL is running + `.env` credentials are correct |
| `No module named 'app'` | Make sure you're running `python run.py` from the `AI_PROJECT/` root |
| `CUDA out of memory` | Only one GPU model at a time — model_manager handles this automatically |
| `Only ZIP files are accepted` | Frontend must send a `.zip` file to `/upload` |
| `ImportError: ai.captioning` | Teammate hasn't delivered their module yet — stub is active |

---

## Git Workflow

```bash
# Never commit .env or model weights
git add .
git commit -m "your message"
git push
```

The `.gitignore` already excludes `.env`, `uploads/`, `outputs/`, and `venv/`.
=======
# PicStory
AI Story Video Generator is a web-based application that automatically transforms a collection of photos or videos into a narrated story video. The system uses artificial intelligence to analyze uploaded media, generate meaningful descriptions, create a coherent storyline, convert the story into voice narration, and produce a final shareable video.
>>>>>>> e0a7bec62cfa75bb2541badccd194ff48b1d49d5
