# app/services/model_manager.py
# Manages model loading and unloading.
# Auto-detects CUDA GPU; falls back to CPU if unavailable.
# Only ONE large model loaded at a time to conserve memory.

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
_sd_pipeline   = None   # Stable Diffusion
_blip_model    = None   # BLIP captioning model
_blip_processor= None
_musicgen      = None   # MusicGen


def _clear_gpu():
    """Force-free all GPU memory after unloading a model."""
    if TORCH_AVAILABLE:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()


# ---------------------------------------------------------------------------
# Stable Diffusion 1.5
# ---------------------------------------------------------------------------

def load_stable_diffusion():
    """Load SD 1.5. Uses GPU with float16 if available, else CPU with float32."""
    global _sd_pipeline
    if _sd_pipeline is not None:
        return _sd_pipeline

    unload_all()

    from diffusers import StableDiffusionPipeline
    import torch

    _sd_pipeline = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=DTYPE,
        safety_checker=None,
    )
    _sd_pipeline = _sd_pipeline.to(DEVICE)
    if DEVICE == "cuda":
        _sd_pipeline.enable_attention_slicing()
    print(f"✅ Stable Diffusion loaded on {DEVICE.upper()}.")
    return _sd_pipeline


def unload_stable_diffusion():
    global _sd_pipeline
    if _sd_pipeline is not None:
        del _sd_pipeline
        _sd_pipeline = None
        _clear_gpu()
        print("🗑️  Stable Diffusion unloaded.")


# ---------------------------------------------------------------------------
# BLIP Image Captioning
# ---------------------------------------------------------------------------

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
        torch_dtype=DTYPE,
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
# Unload everything (called before loading any model)
# ---------------------------------------------------------------------------

def unload_all():
    unload_stable_diffusion()
    unload_blip()
    unload_musicgen()
