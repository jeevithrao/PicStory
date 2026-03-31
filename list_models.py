import os
from dotenv import load_dotenv
from google import genai
import sys

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

with open("available_models.txt", "w") as f:
    if not api_key:
        f.write("NO API KEY\n")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    try:
        models = client.models.list()
        for m in models:
            f.write(f"Model Name: {m.name}, Supported Actions: {m.supported_actions}\n")
    except Exception as e:
        f.write(f"Failed to list models: {str(e)}\n")
