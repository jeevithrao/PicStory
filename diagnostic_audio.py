import os
import sys

print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print(f"Current Path: {os.environ.get('PATH', '')[:500]}...")

try:
    import torch
    print(f"Torch version: {torch.__version__}")
    print(f"Torch CUDA: {torch.cuda.is_available()}")
    # Try a small torch operation to see if DLLs are OK
    x = torch.zeros(1)
    print("Torch operation: SUCCESS")
except Exception as e:
    print(f"Torch import/operation: FAILED - {e}")

try:
    import asyncio
    import edge_tts
    async def test_edge():
        voice = "en-US-AriaNeural"
        text = "Hello, this is a test."
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save("test_final.mp3")
        print("Edge TTS: SUCCESS")
    
    asyncio.run(test_edge())
except Exception as e:
    print(f"Edge TTS: FAILED - {e}")
