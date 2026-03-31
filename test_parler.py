import os
import sys
import traceback

# Setup environment exactly like run.py
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
if os.name == 'nt':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    torch_lib = os.path.join(base_dir, "venv", "Lib", "site-packages", "torch", "lib")
    if os.path.exists(torch_lib):
        print(f"DEBUG: Adding DLL dir {torch_lib}")
        try:
            os.add_dll_directory(torch_lib)
        except Exception as e:
            print(f"DEBUG: add_dll_directory failed: {e}")

try:
    print("DEBUG: Importing torch...")
    import torch
    print(f"DEBUG: Torch version: {torch.__version__}")
    print(f"DEBUG: Torch path: {torch.__file__}")
    
    print("DEBUG: Importing ParlerTTS...")
    from parler_tts import ParlerTTSForConditionalGeneration
    print("DEBUG: ParlerTTS Import SUCCESS")
except Exception:
    print("DEBUG: IMPORT FAILED!")
    traceback.print_exc()
