# ai/audio.py
# Indic Parler-TTS voiceover + MusicGen background music.
# Indic Parler-TTS: multilingual offline model for Indic languages.
# Edge TTS remains as fallback.
# MusicGen: AI music generation from vibe prompts via model_manager.

import os
import asyncio
import edge_tts
import numpy as np
import scipy.io.wavfile
from mutagen import File as MutagenFile

# Mapping of language codes AND display names → Edge TTS voice names
EDGE_TTS_VOICES = {
    # Short codes
    "en":  "en-US-AriaNeural",
    "hi":  "hi-IN-SwaraNeural",
    "bn":  "bn-IN-TanishaaNeural",
    "ta":  "ta-IN-PallaviNeural",
    "te":  "te-IN-ShrutiNeural",
    "mr":  "mr-IN-AarohiNeural",
    "gu":  "gu-IN-DhwaniNeural",
    "kn":  "kn-IN-SapnaNeural",
    "ml":  "ml-IN-SobhanaNeural",
    "pa":  "pa-IN-GurpreetNeural",
    "ur":  "ur-PK-UzmaNeural",
    "as":  "as-IN-PriyomNeural",
    "or":  "or-IN-SubhasiniNeural",
    "ne":  "ne-NP-HemkalaNeural",
    "sd":  "ur-PK-UzmaNeural", # Sindhi uses Perso-Arabic or Devnagari; Urdu is often a better phonetic match
    "sa":  "hi-IN-SwaraNeural",
    "ks":  "ur-PK-UzmaNeural", # Kashmiri uses Perso-Arabic script; Urdu voice is a much better proxy than Hindi
    "kok": "hi-IN-SwaraNeural",
    "mai": "hi-IN-SwaraNeural",
    "mni": "bn-IN-TanishaaNeural",
    "sat": "bn-IN-TanishaaNeural",
    "brx": "hi-IN-SwaraNeural",
    "doi": "hi-IN-SwaraNeural",
    # Display names
    "English":    "en-US-AriaNeural",
    "Hindi":      "hi-IN-SwaraNeural",
    "Bengali":    "bn-IN-TanishaaNeural",
    "Tamil":      "ta-IN-PallaviNeural",
    "Telugu":     "te-IN-ShrutiNeural",
    "Marathi":    "mr-IN-AarohiNeural",
    "Gujarati":   "gu-IN-DhwaniNeural",
    "Kannada":    "kn-IN-SapnaNeural",
    "Malayalam":  "ml-IN-SobhanaNeural",
    "Punjabi":    "pa-IN-GurpreetNeural",
    "Urdu":       "ur-PK-UzmaNeural",
    "Assamese":   "as-IN-PriyomNeural",
    "Odia":       "or-IN-SubhasiniNeural",
    "Nepali":     "ne-NP-HemkalaNeural",
    "Sindhi":     "ur-PK-UzmaNeural",
    "Sanskrit":   "hi-IN-SwaraNeural",
    "Kashmiri":   "ur-PK-UzmaNeural",
    "Konkani":    "hi-IN-SwaraNeural",
    "Maithili":   "hi-IN-SwaraNeural",
    "Manipuri":   "bn-IN-TanishaaNeural",
    "Santali":    "bn-IN-TanishaaNeural",
    "Bodo":       "hi-IN-SwaraNeural",
    "Dogri":      "hi-IN-SwaraNeural",
}

LANGUAGE_ALIASES = {
    "english": "en", "hindi": "hi", "konkani": "kok", "kannada": "kn", "dogri": "doi",
    "bodo": "brx", "urdu": "ur", "tamil": "ta", "kashmiri": "ks", "assamese": "as",
    "bengali": "bn", "marathi": "mr", "sindhi": "sd", "maithili": "mai", "punjabi": "pa",
    "malayalam": "ml", "manipuri": "mni", "telugu": "te", "sanskrit": "sa", "nepali": "ne",
    "santali": "sat", "gujarati": "gu", "odia": "or",
}

INDIC_DESCRIPTION_BY_LANG = {
    "en": "Mary speaks with a clear Indian English accent...",
    "hi": "Rohit speaks in a clear Hindi voice...",
    "as": "Amit speaks in a clear Assamese voice...",
    "bn": "Arjun speaks in a clear Bengali voice...",
    "brx": "Bikram speaks in a clear Bodo voice...",
    "doi": "Karan speaks in a clear Dogri voice...",
    "gu": "Yash speaks in a clear Gujarati voice...",
    "kn": "Suresh speaks in a clear Kannada voice...",
    "ml": "Anjali speaks in a clear Malayalam voice...",
    "mni": "Laishram speaks in a clear Manipuri voice...",
    "mr": "Sanjay speaks in a clear Marathi voice...",
    "ne": "Amrita speaks in a clear Nepali voice...",
    "or": "Manas speaks in a clear Odia voice...",
    "pa": "Divjot speaks in a clear Punjabi voice...",
    "sa": "Aryan speaks in a clear Sanskrit voice...",
    "sd": "A Sindhi speaker speaks clearly...",
    "ta": "Jaya speaks in a clear Tamil voice...",
    "te": "Prakash speaks in a clear Telugu voice...",
    "ur": "An Urdu speaker speaks clearly...",
    "kok": "A Konkani speaker speaks clearly...",
    "mai": "A Maithili speaker speaks clearly...",
    "sat": "A Santali speaker speaks clearly...",
    "ks": "A Kashmiri speaker speaks clearly...",
}

VIBE_PROMPTS = {
    "calm":          "soft calm ambient relaxing background music, peaceful piano",
    "romantic":      "romantic gentle love song, soft guitar and strings",
    "rock":          "energetic rock instrumental, electric guitar and drums",
    "happy":         "upbeat cheerful happy background music, bright and positive",
    "sad":           "melancholic sad emotional background music, slow piano",
    "motivational":  "inspiring motivational cinematic background music, epic and uplifting",
}

# TTS Support Categories
NORMAL_TTS_LANGS = [
    "hi", "ta", "te", "kn", "ml", "bn", "mr", "gu", "as", "or", "ur", 
    "sa", "sd", "mai", "doi", "brx", "sat", "ne", "kok", "mni"
]
WEAK_TTS_LANGS = ["pa"]  # Punjabi: Attempt native -> fallback Hindi
ROBOTIC_TTS_LANGS = ["ks"]  # Kashmiri: Robotic/Unofficial but allowed

# Status codes for UI
TTS_STATUS_OK = "audio_ok"        # 🔊 Full support
TTS_STATUS_WEAK = "audio_weak"    # ⚠️ Approximate pronunciation
TTS_STATUS_FALLBACK = "audio_fb"  # ⚠️ Fallback to another language
TTS_STATUS_ROBOTIC = "audio_rob"  # 📝 "Robotic/Broken"
TTS_STATUS_TEXT = "text_only"     # 📝 No audio
TTS_STATUS_CONVERTED = "audio_conv" # 🔊 Transliterated for proxy

def _batch_prepare_tts_text(segments: list[str], language_code: str) -> list[str]:
    """
    Transliterate multiple segments at once via Gemini to save API quota.
    """
    needs_conversion = ["ks", "sd", "mni", "sat"]
    if language_code not in needs_conversion or not segments:
        return segments

    pairing = {"ks": "Urdu script", "sd": "Urdu script", "mni": "Bengali script", "sat": "Bengali script"}
    target_script = pairing.get(language_code)
    
    from app.services.gemini_service import call_gemini_with_retry
    import json
    
    # Bundle segments into a numbered list
    bundle = "\n".join([f"{i+1}. {s}" for i, s in enumerate(segments)])
    prompt = (
        f"Transliterate (convert script ONLY, do not translate meaning) the following {language_code} segments into {target_script}.\n"
        "Output ONLY a valid JSON list of strings, in the same order. No preamble, no explanation, no markdown.\n\n"
        f"Segments:\n{bundle}"
    )
    
    try:
        response = call_gemini_with_retry(prompt)
        # Attempt to parse as JSON list
        try:
            # Strip markdown code blocks if present
            clean_res = response.strip().replace("```json", "").replace("```", "").strip()
            converted_list = json.loads(clean_res)
            if isinstance(converted_list, list) and len(converted_list) == len(segments):
                print(f"[Audio] Batch transliterated {len(segments)} segments for {language_code}.")
                return [str(s) for s in converted_list]
        except:
            print("[Audio] Failed to parse batch transliteration JSON fallback to individual.")
            pass
    except Exception as e:
        print(f"[Audio] Batch transliteration failed: {e}")
    
    return segments


def _prepare_tts_text(text: str, language_code: str) -> str:
    """
    If the language is one of the 'Rare 9' using a proxy voice,
    transliterate the script to the proxy's script (e.g. Kashmiri -> Urdu script).
    """
    # Languages that need script conversion for their proxy voices
    # Kashmiri (ks) and Sindhi (sd) use Perso-Arabic; Urdu voice Uzma is perfect.
    # Manipuri (mni) and Santali (sat) often use Meitei/Ol Chiki; Bengali voice is proxy.
    # Sanskrit (sa), Konkani (kok), Dogri (doi), Maithili (mai), Bodo (brx) are already Devnagari.
    
    needs_conversion = ["ks", "sd", "mni", "sat"]
    if language_code not in needs_conversion:
        return text

    # Define the pairing
    pairing = {
        "ks":  "Urdu script",
        "sd":  "Urdu script",
        "mni": "Bengali script",
        "sat": "Bengali script"
    }
    target_script = pairing.get(language_code)
    
    from app.services.gemini_service import call_gemini_with_retry
    import time
    time.sleep(1.5) # Preventative delay to stay under Gemini Free Tier RPM limits
    prompt = (
        f"Transliterate (convert script ONLY, do not translate meaning) the following {language_code} text into {target_script}.\n"
        "Output ONLY the converted text. No preamble, no explanation, no bold markers, no markdown.\n"
        "Example for Santali to Bengali: 'ᱥᱟᱹᱜᱩᱱ ᱫᱟᱨᱟᱢ' -> 'সাঁগুন দারাম'.\n\n"
        f"Text: {text}"
    )
    try:
        converted = call_gemini_with_retry(prompt)
        if converted:
            # 1. Strip markdown and common filler
            converted = converted.strip().replace("**", "").replace("`", "").strip()
            # 2. Extract target script if Gemini includes conversational preamble/separators
            for sep in [":", "=", " - ", " is "]:
                if sep in converted:
                    parts = converted.split(sep)
                    # Result is usually at the end: "Word = Conversion"
                    for p in reversed(parts):
                        p_clean = p.strip()
                        if any("\u0600" <= c <= "\u06ff" or "\u0980" <= c <= "\u09ff" for c in p_clean):
                            converted = p_clean
                            break
                    break

        # FINAL VALIDATION & FALLBACK: Ensure we have a script the voice engine can read
        target_ranges = {"Bengali script": ("\u0980", "\u09ff"), "Urdu script": ("\u0600", "\u06ff")}
        tr = target_ranges.get(target_script, (None, None))
        
        has_target = False
        if tr[0] and converted:
            has_target = any(tr[0] <= c <= tr[1] for c in converted)
        
        # If primary script conversion failed (echoed original or failed), try phonetic English fallback
        if not has_target and language_code in ["sat", "mni"]:
            print(f"[Audio] Primary transliteration for {language_code} failed. Trying phonetic English fallback...")
            prompt_fallback = (
                f"Convert the following {language_code} text into phonetic English characters (Roman script). "
                "Output ONLY the phonetic text. No preamble, no explanation.\n\n"
                f"Text: {text}"
            )
            try:
                fallback_res = call_gemini_with_retry(prompt_fallback)
                if fallback_res and fallback_res != text:
                    converted = fallback_res.strip().replace("**", "").replace("`", "")
            except:
                pass

        print(f"[Audio] Transliterated {language_code} for TTS ({target_script}).")
        return converted or text
    except:
        return text


def generate_voiceover(script: str, language: str, output_dir: str) -> dict:
    """
    Generate an MP3/WAV voiceover from the script using Parler-TTS or falling back.
    Returns: dict with {"path": str, "status": str}
    """
    lang_code = _normalize_language(language)
    from app.config import settings

    status = TTS_STATUS_OK
    if lang_code in ROBOTIC_TTS_LANGS: status = TTS_STATUS_ROBOTIC
    if lang_code in WEAK_TTS_LANGS:    status = TTS_STATUS_WEAK

    # Use Parler-TTS if in Local mode OR if natively supported
    use_parler = settings.USE_LOCAL_MODELS or lang_code in NORMAL_TTS_LANGS or lang_code in WEAK_TTS_LANGS or lang_code in ROBOTIC_TTS_LANGS
    
    if use_parler:
        output_path = os.path.join(output_dir, "narration.wav")
        try:
            print(f"⏳ Attempting Indic Parler-TTS for {lang_code}...")
            _generate_indic_parler_tts(script=script, language_code=lang_code, output_path=output_path)
            return {"path": output_path, "status": status}
        except Exception as e:
            print(f"⚠️ Local TTS failed: {e}. Trying fallback options...")
            # Fallback 1: Try Hindi in Parler
            if lang_code in WEAK_TTS_LANGS or lang_code in ROBOTIC_TTS_LANGS:
                try:
                    _generate_indic_parler_tts(script=script, language_code="hi", output_path=output_path)
                    return {"path": output_path, "status": TTS_STATUS_FALLBACK}
                except: pass
            
            # Fallback 2: Edge TTS (Robust)
            output_path_mp3 = os.path.join(output_dir, "narration.mp3")
            try:
                print("🌐 Falling back to Edge TTS...")
                # Use transliterated text for proxy voices
                tts_text = _prepare_tts_text(script, lang_code)
                _generate_edge_tts(script=tts_text, language=language, output_path=output_path_mp3)
                return {"path": output_path_mp3, "status": TTS_STATUS_OK}
            except: pass

            # Fallback 3: Silence
            _write_silence_wav(output_path, seconds=3.0)
            return {"path": output_path, "status": TTS_STATUS_TEXT}


def generate_per_image_voiceovers(narration_segments: list[str], language: str, output_dir: str) -> list[dict]:
    lang_code = _normalize_language(language)
    from app.config import settings
    
    use_parler = settings.USE_LOCAL_MODELS or lang_code in NORMAL_TTS_LANGS or lang_code in WEAK_TTS_LANGS or lang_code in ROBOTIC_TTS_LANGS
    results = []

    # BATCH PREPARE TRANSLITERATION (to save API quota)
    tts_segments = narration_segments
    if not use_parler:
        tts_segments = _batch_prepare_tts_text(narration_segments, lang_code)

    for i, segment_text in enumerate(narration_segments):
        # The visual caption stays native
        visual_text = segment_text.strip() or "..."
        # The audio text might be transliterated
        audio_text = tts_segments[i] if i < len(tts_segments) else visual_text
        
        status = TTS_STATUS_OK
        if lang_code in ROBOTIC_TTS_LANGS: status = TTS_STATUS_ROBOTIC
        if lang_code in WEAK_TTS_LANGS:    status = TTS_STATUS_WEAK

        ext = "wav" if use_parler else "mp3"
        output_path = os.path.join(output_dir, f"narration_segment_{i}.{ext}")
        generated_ok = False

        if use_parler:
            try:
                _generate_indic_parler_tts(script=segment_text, language_code=lang_code, output_path=output_path)
                generated_ok = True
            except Exception:
                if lang_code in WEAK_TTS_LANGS or lang_code in ROBOTIC_TTS_LANGS:
                    try:
                        _generate_indic_parler_tts(script=segment_text, language_code="hi", output_path=output_path)
                        generated_ok = True
                        status = TTS_STATUS_FALLBACK
                    except: pass

        if not generated_ok:
            # TRY EDGE TTS as last working resort before silence
            output_path = os.path.join(output_dir, f"narration_segment_{i}.mp3")
            try:
                # Use the batched transliteration text
                _generate_edge_tts(script=audio_text, language=language, output_path=output_path)
                generated_ok = True
                status = TTS_STATUS_OK
            except: pass

        if not generated_ok:
            status = TTS_STATUS_TEXT
            output_path = os.path.join(output_dir, f"narration_segment_{i}.wav")
            _write_silence_wav(output_path)

        try:
            audio = MutagenFile(output_path)
            duration = float(audio.info.length) if audio and audio.info else 3.0
        except:
            duration = 3.0

        results.append({"path": output_path, "duration": duration, "status": status})

    return results


def _normalize_language(language: str) -> str:
    if not language: return "hi"
    lower = str(language).strip().lower()
    return LANGUAGE_ALIASES.get(lower, lower)


def _indic_description(language_code: str) -> str:
    return INDIC_DESCRIPTION_BY_LANG.get(language_code, "A clear voice with moderate pace...")


def _generate_indic_parler_tts(script: str, language_code: str, output_path: str, timeout: int = 120) -> None:
    import threading
    import torch
    import scipy.io.wavfile
    from app.services.model_manager import load_indic_parler_tts

    exception_holder = []

    def _worker():
        try:
            model, prompt_tokenizer, description_tokenizer = load_indic_parler_tts()
            description = _indic_description(language_code)

            description_inputs = description_tokenizer(description, return_tensors="pt").to(model.device)
            prompt_inputs = prompt_tokenizer(script, return_tensors="pt").to(model.device)

            with torch.no_grad():
                gen = model.generate(
                    input_ids=description_inputs["input_ids"],
                    attention_mask=description_inputs.get("attention_mask"),
                    prompt_input_ids=prompt_inputs["input_ids"],
                    prompt_attention_mask=prompt_inputs.get("attention_mask"),
                )

            audio = gen.cpu().numpy().squeeze()
            audio = np.clip(audio, -1.0, 1.0)
            scipy.io.wavfile.write(output_path, int(model.config.sampling_rate), (audio * 32767).astype(np.int16))
        except Exception as e:
            exception_holder.append(e)

    t = threading.Thread(target=_worker)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive(): raise RuntimeError("TTS Timeout")
    if exception_holder: raise exception_holder[0]


def _generate_edge_tts(script: str, language: str, output_path: str, timeout: int = 60) -> None:
    voice = EDGE_TTS_VOICES.get(language, EDGE_TTS_VOICES.get(_normalize_language(language), EDGE_TTS_VOICES["hi"]))
    
    async def _gen():
        comm = edge_tts.Communicate(script, voice)
        await comm.save(output_path)

    import asyncio
    try:
        # Check if we are already in an event loop (e.g. running under FastAPI/uvicorn)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are already in a loop, we need to carefully run this co-routine
            # Using asgiref (if available) or nested-asyncio logic
            import nest_asyncio
            nest_asyncio.apply()
            loop.run_until_complete(_gen())
        else:
            loop.run_until_complete(_gen())
    except Exception:
        # Final fallback: just try asyncio.run if nothing else worked
        try:
            asyncio.run(_gen())
        except:
             # If all else fails, this indicates a serious environment issue
             print("[Audio] ERROR: Could not run Edge TTS async loop.")
             raise

def _write_silence_wav(path: str, seconds: float = 3.0, sample_rate: int = 24000) -> None:
    silent = np.zeros(int(seconds * sample_rate), dtype=np.int16)
    scipy.io.wavfile.write(path, sample_rate, silent)

def detect_mood(script: str) -> str:
    script_lower = script.lower()
    mood_keywords = {
        "sad": ["sad", "cry", "tears"], "romantic": ["love", "heart"],
        "happy": ["joy", "smile"], "motivational": ["inspire", "dream"],
        "rock": ["energy", "wild"], "calm": ["peace", "calm"]
    }
    for mood, keywords in mood_keywords.items():
        if any(kw in script_lower for kw in keywords): return mood
    return "calm"

def generate_music(vibe: str, output_dir: str, filename: str = None) -> str:
    from app.services.model_manager import load_musicgen, unload_musicgen
    model, processor = load_musicgen()
    prompt = VIBE_PROMPTS.get(vibe, VIBE_PROMPTS["calm"])
    inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(model.device)
    audio_values = model.generate(**inputs, max_new_tokens=256)
    audio_np = audio_values[0, 0].cpu().numpy()
    output_path = os.path.join(output_dir, filename or f"music_{vibe}.wav")
    scipy.io.wavfile.write(output_path, model.config.audio_encoder.sampling_rate, (audio_np * 32767).astype(np.int16))
    unload_musicgen()
    return output_path
