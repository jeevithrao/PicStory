import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

langs = ["Bodo", "Maithili", "Dogri", "Manipuri", "Santali", "Sindhi"]
test_text = "The quick brown fox jumps over the lazy dog."

print("Testing Gemini translation for special languages:")
for lang in langs:
    prompt = f"Translate the following English text into {lang}. Output ONLY the translated text, nothing else.\n\nText: {test_text}"
    try:
        response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        print(f"[{lang}]: {(response.text or '').strip()}")
    except Exception as e:
        print(f"[{lang}]: FAILED - {e}")
