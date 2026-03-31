import os
import sys

# PRIORITY FIX FOR WINDOWS DLL CONFLICT
if os.name == 'nt':
    # Explicitly find and add the torch lib directory to the DLL search path
    # This bypasses the Anaconda / Library / bin / libiomp5md.dll issue
    torch_lib = os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "torch", "lib")
    if os.path.exists(torch_lib):
        print(f"Adding DLL directory: {torch_lib}")
        os.add_dll_directory(torch_lib)
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    model_id = "ai4bharat/indic-parler-tts"
    # Testing tokenizer loading only (it imports the same modeling code)
    p_tok = AutoTokenizer.from_pretrained(model_id)
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
        await comm.save("test_final_ok.mp3")
        
    async_to_sync(test)()
    print("Edge TTS + Asgiref: SUCCESS")
except Exception as e:
    print(f"Edge TTS + Asgiref: FAILED - {e}")
