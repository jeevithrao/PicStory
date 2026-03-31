import os
import sys
import ctypes

# ---------------------------------------------------------------------------
# WINDOWS DLL FIX (WinError 127 / libiomp5md.dll conflicts)
# ---------------------------------------------------------------------------
# We MUST force-load the correct OpenMP DLL from the venv before anything else.
if os.name == 'nt':
    # Use sys.prefix to find the current environment's lib folder (works even if not named 'venv')
    torch_lib = os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib")
    
    if os.path.exists(torch_lib):
        # 1. Add directory to search path for Python 3.8+
        try:
            os.add_dll_directory(torch_lib)
        except Exception: pass
        
        # 2. Force load the critical DLLs
        dlls = ["libiomp5md.dll", "libiompstubs5md.dll"]
        for dll in dlls:
            dll_path = os.path.join(torch_lib, dll)
            if os.path.exists(dll_path):
                try:
                    print(f"🔧 Forcing DLL: {dll_path}")
                    ctypes.CDLL(dll_path)
                except Exception as e:
                    print(f"⚠️ DLL Load Warning ({dll}): {e}")

# ---------------------------------------------------------------------------
# Environment Setup
# ---------------------------------------------------------------------------
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )