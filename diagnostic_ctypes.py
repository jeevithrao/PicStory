import os
import sys
import ctypes

# THE ULTIMATE DLL FORCING
# This manually loads the CORRECT OpenMP DLL from the venv before anything else can touch the wrong one.
try:
    dll_path = os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "torch", "lib", "libiomp5md.dll")
    if os.path.exists(dll_path):
        print(f"FORCING DLL LOAD: {dll_path}")
        ctypes.CDLL(dll_path)
    else:
        print(f"DLL NOT FOUND AT: {dll_path}")
except Exception as e:
    print(f"DLL FORCE LOAD FAILED: {e}")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    print("Indic Parler-TTS Import: SUCCESS")
except Exception as e:
    print(f"Indic Parler-TTS Import: FAILED - {e}")

try:
    from asgiref.sync import async_to_sync
    import asyncio
    import edge_tts
    
    async def test():
        voice = "en-US-AriaNeural"
        text = "Test."
        comm = edge_tts.Communicate(text, voice)
        await comm.save("test_ctypes.mp3")
        
    async_to_sync(test)()
    print("Edge TTS + Asgiref: SUCCESS")
except Exception as e:
    print(f"Edge TTS + Asgiref: FAILED - {e}")
