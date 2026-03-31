import os
import sys

# THE PATH CLEANER
# Remove Anaconda paths from the process environment to stop it from leaking DLLs
path = os.environ.get("PATH", "")
paths = path.split(os.pathsep)
clean_paths = [p for p in paths if "anaconda" not in p.lower()]
os.environ["PATH"] = os.path.join(os.getcwd(), "venv", "Scripts") + os.pathsep + os.pathsep.join(clean_paths)

print(f"Cleaned PATH: {os.environ['PATH'][:200]}...")

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
        await comm.save("test_final_path.mp3")
        
    async_to_sync(test)()
    print("Edge TTS + Asgiref: SUCCESS")
except Exception as e:
    print(f"Edge TTS + Asgiref: FAILED - {e}")
