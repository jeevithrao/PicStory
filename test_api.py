import os
import sys
from google import genai

client = genai.Client(api_key=GEMINI_API_KEY)
try:
    response = client.models.generate_content(model='gemini-2.0-flash', contents='hi')
    print("SUCCESS")
    print(response.text)
except Exception as e:
    print('ERROR_IS:', str(e))
    sys.exit(1)
