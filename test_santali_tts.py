import asyncio
import os
import edge_tts
from dotenv import load_dotenv

load_dotenv()

async def test_santali_tts():
    # Example Santali text (in Bengali script as the code currently does)
    # "Hello how are you" in Santali (Bengali script) is roughly "জুহার, চেত ল্যকা মেনাম আ?"
    text = "জুহার, চেত ল্যকা মেনাম আ?"
    
    # Current proxy voice for Santali in ai/audio.py
    voice = "hi-IN-SwaraNeural" 
    
    print(f"Testing TTS with voice: {voice}")
    print(f"Text: {text}")
    
    output_path = "test_santali.mp3"
    comm = edge_tts.Communicate(text, voice)
    try:
        await comm.save(output_path)
        print(f"✅ Success! Saved to {output_path}")
        # Check file size
        if os.path.exists(output_path):
             print(f"File size: {os.path.getsize(output_path)} bytes")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_santali_tts())
