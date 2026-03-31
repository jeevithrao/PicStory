import os
import sys

# Apply the DLL fix immediately
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

print(f"Python: {sys.version}")
print(f"Path: {sys.executable}")

try:
    import torch
    print(f"Torch: {torch.__version__} (DLL Check: SUCCESS)")
    x = torch.zeros(1)
    print("Torch math operation: SUCCESS")
except Exception as e:
    print(f"Torch Check: FAILED - {e}")

try:
    from asgiref.sync import async_to_sync
    import asyncio
    import edge_tts
    
    async def test():
        voice = "en-US-AriaNeural"
        text = "Check."
        comm = edge_tts.Communicate(text, voice)
        await comm.save("test_asgiref.mp3")
        
    async_to_sync(test)()
    print("Edge TTS + Asgiref Check: SUCCESS")
except Exception as e:
    print(f"Asgiref Check: FAILED - {e}")

try:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    model_id = "ai4bharat/indic-parler-tts"
    # Just check tokenizers to avoid 3GB download in this test
    p_tok = AutoTokenizer.from_pretrained(model_id)
    print("Indic Parler Tokenizer Check: SUCCESS")
except Exception as e:
    print(f"Parler Check: FAILED - {e}")

print("\n--- ALL SYSTEMS READY ---")
