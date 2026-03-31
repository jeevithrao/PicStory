import os
from dotenv import load_dotenv
from google import genai
import sys

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

with open("test_keys_output.txt", "w") as f:
    if not api_key:
        f.write("NO API KEY\n")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    models_to_test = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"]
    for m in models_to_test:
        try:
            response = client.models.generate_content(model=m, contents="hello")
            f.write(f"Model {m}: SUCCESS\n")
        except Exception as e:
            f.write(f"Model {m}: FAILED - {str(e)}\n")
