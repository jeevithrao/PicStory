import os
import sys

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def trace_import(name):
    print(f"Testing import: {name}...", end=" ", flush=True)
    try:
        __import__(name)
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED - {e}")

trace_import("torch")
trace_import("transformers")
trace_import("tokenizers")
trace_import("scipy")
trace_import("soundfile")
trace_import("parler_tts")
print("\nChecking for specific DLLs in paths...")
import subprocess
try:
    print("Checking for libiomp5md.dll:")
    result = subprocess.run(['where', 'libiomp5md.dll'], capture_output=True, text=True)
    print(result.stdout)
except:
    pass
