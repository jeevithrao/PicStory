import os
from dotenv import load_dotenv
from google import genai
import sys

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

with open("test_flash_output.txt", "w") as f:
    if not api_key:
        f.write("NO API KEY\n")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    # Test gemini-flash-latest
    try:
        response = client.models.generate_content(model="gemini-flash-latest", contents="hello")
        f.write("Model gemini-flash-latest: SUCCESS\n")
    except Exception as e:
        f.write(f"Model gemini-flash-latest: FAILED - {str(e)}\n")
        
    # Test gemini-2.5-flash again to see current limit state
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents="hello")
        f.write("Model gemini-2.5-flash: SUCCESS\n")
    except Exception as e:
        f.write(f"Model gemini-2.5-flash: FAILED - {str(e)}\n")
