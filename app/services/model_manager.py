# app/services/model_manager.py
# Manages model loading and unloading.
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Prioritize local torch DLLs on Windows to avoid Anaconda conflicts
if os.name == 'nt':
    # Fixed absolute path for model_manager (two levels up from venv root)
    torch_lib_path = os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "torch", "lib")
    if os.path.exists(torch_lib_path):
        try:
            os.add_dll_directory(torch_lib_path)
        except Exception:
            pass
import gc

# Try importing torch
try:
    import torch
    TORCH_AVAILABLE = True
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32
except ImportError:
    TORCH_AVAILABLE = False
    DEVICE = "cpu"
    DTYPE = None

print(f"🖥️  Model device: {DEVICE}")

# Global model references (only one should be non-None at any time)
_musicgen      = None   # MusicGen
_indic_parler  = None   # Indic Parler-TTS
_nllb_translator = None # NLLB-200-distilled-600M


def _clear_gpu():
    """Force-free all GPU memory after unloading a model."""
    if TORCH_AVAILABLE:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()


# ---------------------------------------------------------------------------
# MusicGen
# ---------------------------------------------------------------------------

def load_musicgen():
    """Load MusicGen small."""
    global _musicgen
    if _musicgen is not None:
        return _musicgen

    unload_all()

    from transformers import MusicgenForConditionalGeneration, AutoProcessor
    import torch

    processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
    model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
    model = model.to(DEVICE)
    _musicgen = (model, processor)
    print(f"✅ MusicGen loaded on {DEVICE.upper()}.")
    return _musicgen


def unload_musicgen():
    global _musicgen
    if _musicgen is not None:
        del _musicgen
        _musicgen = None
        _clear_gpu()
        print("🗑️  MusicGen unloaded.")


# ---------------------------------------------------------------------------
# Indic Parler-TTS
# ---------------------------------------------------------------------------

def load_indic_parler_tts():
    """Load Indic Parler-TTS model + tokenizers."""
    global _indic_parler
    if _indic_parler is not None:
        return _indic_parler

    unload_all()

    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    model_id = "ai4bharat/indic-parler-tts"
    model = ParlerTTSForConditionalGeneration.from_pretrained(model_id)
    model = model.to(DEVICE)
    model.eval()

    prompt_tokenizer = AutoTokenizer.from_pretrained(model_id)
    description_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)

    _indic_parler = (model, prompt_tokenizer, description_tokenizer)
    print(f"✅ Indic Parler-TTS loaded on {DEVICE.upper()}.")
    return _indic_parler


def unload_indic_parler_tts():
    global _indic_parler
    if _indic_parler is not None:
        del _indic_parler
        _indic_parler = None
        _clear_gpu()
        print("🗑️  Indic Parler-TTS unloaded.")


# ---------------------------------------------------------------------------
# NLLB-200 (Translator)
# ---------------------------------------------------------------------------

def load_nllb_translator():
    """Load NLLB-200 distilled 600M model + tokenizer."""
    global _nllb_translator
    if _nllb_translator is not None:
        return _nllb_translator

    unload_all()

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    model_id = "facebook/nllb-200-distilled-600M"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    model = model.to(DEVICE)
    model.eval()

    _nllb_translator = (model, tokenizer)
    print(f"✅ NLLB-200 loaded on {DEVICE.upper()}.")
    return _nllb_translator


def unload_nllb_translator():
    global _indic_translator
    if _indic_translator is not None:
        del _indic_translator
        _indic_translator = None
        _clear_gpu()
        print("🗑️  IndicTrans2 unloaded.")


# ---------------------------------------------------------------------------
# IndicTrans2 (EN-Indic Translator)
# ---------------------------------------------------------------------------

def load_indic_translator():
    """Load IndicTrans2 distilled 200M EN-Indic model."""
    global _indic_translator
    if _indic_translator is not None:
        return _indic_translator

    unload_all()

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    # Using the distilled version for speed (EN -> Indic)
    model_id = "ai4bharat/indictrans2-en-indic-dist-200m"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id, trust_remote_code=True)
    model = model.to(DEVICE)
    model.eval()

    _indic_translator = (model, tokenizer)
    print(f"✅ IndicTrans2 (200M) loaded on {DEVICE.upper()}.")
    return _indic_translator


def unload_indic_translator():
    global _nllb_translator
    if _nllb_translator is not None:
        del _nllb_translator
        _nllb_translator = None
        _clear_gpu()
        print("🗑️  NLLB-200 unloaded.")


# ---------------------------------------------------------------------------
# NLLB-200 (Translator)
# ---------------------------------------------------------------------------

def load_indic_translator():
    """Load NLLB-200 distilled 600M model (Open alternative to gated IndicTrans2)."""
    global _nllb_translator
    if _nllb_translator is not None:
        return _nllb_translator

    unload_all()

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    # Using NLLB-200 because it is OPEN and supports all 22 Indic languages
    model_id = "facebook/nllb-200-distilled-600M"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    model = model.to(DEVICE)
    model.eval()

    _nllb_translator = (model, tokenizer)
    print(f"✅ NLLB-200 (600M) loaded on {DEVICE.upper()}.")
    return _nllb_translator


def unload_nllb_translator():
    global _nllb_translator
    if _nllb_translator is not None:
        del _nllb_translator
        _nllb_translator = None
        _clear_gpu()
        print("🗑️  NLLB-200 unloaded.")

# ---------------------------------------------------------------------------
# BLIP Image Captioning (Restored)
# ---------------------------------------------------------------------------
_blip_model = None
_blip_processor = None

def load_blip():
    """Load BLIP model and processor."""
    global _blip_model, _blip_processor
    if _blip_model is not None:
        return _blip_model, _blip_processor

    unload_all()

    from transformers import BlipProcessor, BlipForConditionalGeneration
    import torch

    _blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    _blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        torch_dtype=DTYPE if DTYPE else torch.float32,
    ).to(DEVICE)
    print(f"✅ BLIP loaded on {DEVICE.upper()}.")
    return _blip_model, _blip_processor

def unload_blip():
    global _blip_model, _blip_processor
    if _blip_model is not None:
        del _blip_model
        del _blip_processor
        _blip_model = None
        _blip_processor = None
        _clear_gpu()
        print("🗑️  BLIP unloaded.")

# ---------------------------------------------------------------------------
# Unload everything (called before loading any model)
# ---------------------------------------------------------------------------

def unload_all():
    unload_musicgen()
    unload_indic_parler_tts()
    unload_indic_translator()