import time
from google import genai
from app.config import settings

_client = None
_current_key = None

def get_client():
    """Get or create the modern Gemini client, re-initializing if the key changes."""
    global _client, _current_key
    
    new_key = settings.GEMINI_API_KEY
    if not new_key or new_key == "your_gemini_key_here":
        raise ValueError("GEMINI_API_KEY is not set in .env")
        
    if _client is None or _current_key != new_key:
        print(f"[Gemini] Initializing client with key: {new_key[:8]}...")
        _client = genai.Client(api_key=new_key)
        _current_key = new_key
        
    return _client


def call_gemini_with_retry(prompt: str, model: str = "gemini-flash-latest", contents=None, config=None, max_retries: int = 5, return_raw: bool = False) -> any:
    """Helper to call Gemini with exponential backoff for transient errors."""
    client = get_client()
    
    # If contents is provided (for images/multimodal), use it, otherwise use prompt
    final_contents = contents if contents is not None else prompt
    
    for attempt in range(max_retries):
        try:
            # We use **kwargs style or explicit mapping
            kwargs = {}
            if config: kwargs['config'] = config
            
            response = client.models.generate_content(model=model, contents=final_contents, **kwargs)
            if return_raw:
                return response
            return (response.text or "").strip()
        except Exception as e:
            err_text = str(e)
            # Common transient errors for Gemini Free Tier
            is_transient = any(msg in err_text for msg in ["RESOURCE_EXHAUSTED", "429", "503", "500", "504", "UNAVAILABLE"])
            
            if is_transient and attempt < max_retries - 1:
                # Cooldown strategy (Free tier often resets every 60s)
                # Wait times: 5, 15, 35, 65, 95
                wait_time = [5, 15, 35, 65, 95][attempt]
                print(f"[Gemini API] Rate Limit/Error ({err_text}). Cooling down for {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            # If not transient or last attempt, re-raise with more context
            if "RESOURCE_EXHAUSTED" in err_text or "429" in err_text:
                raise RuntimeError(
                    "Gemini quota exceeded. Reached daily or per-minute limit on the Free Tier. "
                    "Wait 60 seconds and try again, or consider using a different API key."
                ) from e
            raise e
    return ""
