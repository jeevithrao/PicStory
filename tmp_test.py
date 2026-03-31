from google import genai
from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    
    # Create a tiny dummy image
    img = Image.new('RGB', (100, 100), color = 'red')
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[img, "What color is this?"]
    )
    print("SUCCESS:", response.text)
except Exception as e:
    import traceback
    traceback.print_exc()
