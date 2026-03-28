# run.py
# Start the PicStory backend server.
# Usage: python run.py

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,          # Auto-reload on code changes during development
        log_level="info",
    )
