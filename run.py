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

# Force venv site-packages to the front of sys.path to avoid Anaconda conflicts
venv_site_packages = os.path.join(sys.prefix, "Lib", "site-packages")
if venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)
else:
    # If it's already there but at the end, move it to the front
    sys.path.remove(venv_site_packages)
    sys.path.insert(0, venv_site_packages)

# Ensure the subprocesses spawned by uvicorn (reload=True) use the same path
os.environ["PYTHONPATH"] = venv_site_packages + os.pathsep + os.getcwd()

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
        log_level="info",
    )
