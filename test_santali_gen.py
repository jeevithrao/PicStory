import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def test_santali_generation():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found")
        return
    
    client = genai.Client(api_key=api_key)
    
    prompt = "Write a one-sentence story in Santali language (native script)."
    
    try:
        response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        print(f"Generated text: {response.text}")
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    test_santali_generation()
