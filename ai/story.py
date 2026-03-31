# ai/story.py
# Gemini-powered narration script generator.
# Produces emotional, short-film voiceover style narration from captions.
# Can generate per-image narration segments for synced slideshow video.

import google.generativeai as genai
from app.config import settings

# Language display names for prompt engineering
LANG_NAMES = {
    "hi": "Hindi", "kok": "Konkani", "kn": "Kannada", "doi": "Dogri",
    "brx": "Bodo", "ur": "Urdu", "ta": "Tamil", "ks": "Kashmiri",
    "as": "Assamese", "bn": "Bengali", "mr": "Marathi", "sd": "Sindhi",
    "mai": "Maithili", "pa": "Punjabi", "ml": "Malayalam", "mni": "Manipuri",
    "te": "Telugu", "sa": "Sanskrit", "ne": "Nepali", "sat": "Santali",
    "gu": "Gujarati", "or": "Odia",
}

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_key_here":
            raise ValueError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=api_key)
        _configured = True


def generate_narration_script(captions: list[str], language: str, model: str = "gemini") -> str:
    """
    Input:  captions (list of strings — can be in any language), language code, model name
    Output: single narration script string — emotional short-film voiceover style
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, "English")
    numbered_captions = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))

    prompt = f"""You are a voiceover artist for an award-winning short film. You are given vivid image descriptions from a personal photo slideshow.

Write a deeply emotional, cinematic narration script that weaves all the images into one flowing story. This is NOT a list of descriptions — it is a STORY told from the heart.

Image descriptions:
{numbered_captions}

Style guide:
- Write in {lang_name} language.
- Sound like a narrator from a Humans of Bombay story or a wedding film voiceover.
- Use sensory, poetic language — describe not just what's seen, but what it FEELS like.
- Evoke specific emotions: nostalgia, joy, hope, love, pride, warmth, bittersweet beauty.
- Use pauses (…) and rhetorical questions to create rhythm.
- Each image gets 2-3 sentences of narration that flow naturally into the next.
- Start with a hook that pulls the listener in. End with a line that lingers.
- Do NOT include stage directions, timestamps, image numbers, or speaker labels.
- Output ONLY the narration text, nothing else.

Example tone:
"Some moments don't need a calendar to remind you… they live in the way light fell across a room, in the echo of a laugh you'd recognize anywhere. This is one of those stories."
"""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️  Gemini narration failed: {e}")
        joined = " ".join(captions)
        return f"Welcome to this story. {joined} Thank you for watching."


def generate_per_image_narration(captions: list[str], language: str, awareness_topic: str | None = None) -> list[str]:
    """
    Generate a separate narration segment for EACH image.
    Returns a list of narration strings, one per image.
    Each segment is 2-3 sentences designed for voiceover.
    
    If awareness_topic is provided, generates educational narration about the topic
    (what it is, how to prevent it, impact, solutions) — not just image descriptions.
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, "English")
    numbered_captions = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))

    if awareness_topic:
        # AWARENESS MODE: Generate unique narration per image, each covering a
        # different angle of the topic — building a logical PSA arc.
        prompt = f"""You are a professional PSA (Public Service Announcement) narrator.

Your awareness topic: {awareness_topic}

You must write EXACTLY {len(captions)} short narration segments — one for each image slide — that together tell a complete awareness story about {awareness_topic}.

Each segment must cover a DIFFERENT angle. Follow this arc:
- Segment 1: INTRODUCTION — What is {awareness_topic}? Why does it matter?
- Segment 2: THE PROBLEM — What dangers, harms, or consequences does it cause?
- Segment 3: REAL IMPACT — A real-world example, statistic, or human story showing its effect.
- Segment 4: PREVENTION / SOLUTIONS — What can people do? Specific, practical tips.
- Segment 5+: Additional tips, call to action, how to spread awareness, where to get help.

If there are fewer than 5 images, compress the arc to fit.
If there are more than 5, expand prevention/solutions and call-to-action sections.

Style rules:
- Write ALL segments in {lang_name} language.
- Each segment: 2-3 sentences. Clear. Powerful. Accessible to all ages.
- Do NOT describe the images — focus 100% on the awareness message.
- Sound like a trusted narrator giving a documentary-style PSA.
- Each segment must be MEANINGFULLY DIFFERENT from the others.

Output format — EXACTLY {len(captions)} numbered segments:
1. [segment text]
2. [segment text]
...
Output ONLY the numbered segments. Nothing else.
"""
    else:
        # STANDARD MODE: Generate personal/poetic narration
        prompt = f"""You are a voiceover artist for an award-winning short film. You are given vivid image descriptions from a personal photo slideshow.

For EACH image, write a separate narration segment (2-3 sentences). These segments will be read aloud one at a time over each image in a slideshow video.

Image descriptions:
{numbered_captions}

Style guide:
- Write ALL narration in {lang_name} language.
- Sound like a narrator from a Humans of Bombay story or a wedding film voiceover.
- Use sensory, poetic language — describe not just what's seen, but what it FEELS like.
- Each segment should flow naturally from the previous one, telling a coherent story.
- The first segment should hook the listener. The last should leave a lingering feeling.
- Do NOT include stage directions, timestamps, or speaker labels.

Output format:
- Output EXACTLY {len(captions)} segments, numbered 1 through {len(captions)}.
- One segment per line, numbered like: 1. [narration segment]
- Each segment should be 2-3 sentences.
- Output ONLY the numbered segments, nothing else.
"""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        raw = response.text.strip()

        import re
        lines = re.findall(r'\d+\.\s*(.+)', raw)

        if len(lines) >= len(captions):
            return lines[:len(captions)]
        elif len(lines) > 0:
            # Pad with generic segments
            while len(lines) < len(captions):
                if awareness_topic:
                    lines.append(f"Learn more about {awareness_topic} to protect yourself and your community.")
                else:
                    lines.append(captions[len(lines)] if len(lines) < len(captions) else "...")
            return lines
        else:
            # Fallback: use captions directly
            return captions

    except Exception as e:
        print(f"⚠️  Gemini per-image narration failed: {e}")
        return captions


def detect_awareness_topic(context: str) -> str | None:
    """
    Detect if a context describes an awareness or social cause topic.
    
    Layer 1: Fast keyword matching.
    Layer 2: Gemini LLM check (if needed for ambiguous cases).
    
    Returns: Topic name (e.g., "Cyber Security", "Road Safety") or None if not an awareness topic.
    """
    if not context or not context.strip():
        return None
    
    # Layer 1: Keyword matching (fast, no API call)
    awareness_keywords = {
        "cyber": "Cyber Security",
        "crime": "Crime Awareness",
        "cybercrime": "Cyber Crime",
        "safety": "Safety",
        "health": "Health",
        "pollution": "Environmental Awareness",
        "climate": "Climate Change",
        "violence": "Violence Prevention",
        "awareness": "Social Awareness",
        "social": "Social Cause",
        "campaign": "Social Campaign",
        "education": "Education",
        "poverty": "Poverty",
        "drug": "Drug Awareness",
        "abuse": "Abuse Prevention",
        "traffic": "Traffic Safety",
        "road": "Road Safety",
        "water": "Water Conservation",
        "sanitation": "Sanitation",
        "gender": "Gender Equality",
        "equality": "Equality",
        "rights": "Human Rights",
        "environment": "Environmental",
        "digital": "Digital Literacy",
        "fraud": "Fraud Prevention",
        "scam": "Scam Prevention",
    }
    
    context_lower = context.lower()
    for keyword, topic in awareness_keywords.items():
        if keyword in context_lower:
            print(f"[awareness] Topic detected (keyword): {topic}")
            return topic
    
    # Layer 2: Gemini LLM check (for ambiguous cases)
    try:
        _ensure_configured()
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""Is this context about a social awareness or public cause campaign (like cybercrime, road safety, health, climate, etc.)?

Context: "{context}"

Reply with ONLY "YES" or "NO"."""
        
        response = gen_model.generate_content(prompt)
        answer = response.text.strip().upper()
        
        if "YES" in answer:
            print(f"[awareness] Topic detected (Gemini): {context[:40]}")
            return "Awareness Campaign"
        else:
            print("[awareness] Not an awareness topic — using captions as narration")
            return None
    except Exception as e:
        print(f"[awareness] Gemini check failed ({e}), defaulting to keyword detection only")
        return None


def generate_awareness_caption(topic: str, language: str) -> str:
    """
    Generate a single, short, generic awareness message for the detected topic.

    This is used in Awareness mode where per-image captioning is SKIPPED entirely.
    The same message is applied to ALL images as both caption AND narration.

    Example output for 'Cyber Security' (English):
    "Cybersecurity means protecting your personal information and devices from online
    threats. Always use strong passwords, avoid clicking unknown links, and never share
    OTPs or private data. Stay alert online—one small mistake can lead to data theft
    or hacking."
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, language if language else "English")

    prompt = f"""You are an awareness campaign writer creating a Public Service Announcement (PSA).

Write a short, powerful awareness message about: {topic}

Requirements:
- Explain what {topic} is in clear, simple terms (1 sentence)
- Give 2-3 specific, practical tips, warnings, or facts about {topic}
- End with a strong call to action or memorable warning
- Total length: exactly 3-4 sentences
- Tone: serious but empowering, like a professional PSA narrator
- Language: write entirely in {lang_name}

Example format (Cybersecurity, English):
"Cybersecurity means protecting your personal information and devices from online threats. Always use strong passwords, avoid clicking unknown links, and never share OTPs or private data. Stay alert online—one small mistake can lead to data theft or hacking."

Output ONLY the awareness message — no headings, no explanations, no bullet points."""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        caption = response.text.strip()
        print(f"[awareness] Generated awareness caption for topic: {topic}")
        return caption
    except Exception as e:
        print(f"⚠️  Awareness caption generation failed: {e}")
        return (
            f"{topic} awareness is important for everyone. "
            f"Stay informed about {topic} to protect yourself and your community. "
            f"Knowledge and vigilance are your strongest defenses—spread the word and stay safe."
        )


def generate_awareness_lecture(topic: str, language: str) -> str:
    """
    Generate a complete educational lecture script about an awareness topic.
    This is a FULL NARRATIVE lecturette (not image-based), designed to:
    - Explain what the topic is
    - Discuss why it matters
    - Explain how to prevent/protect
    - Provide actionable advice
    - Call to action
    
    Returns a single narration script suitable for full voiceover.
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, "English")

    prompt = f"""You are creating a powerful awareness PSA (Public Service Announcement) lecture for a global audience.

Topic to educate about: {topic}

Your task: Write a compelling, informative 3-4 minute lecture script in {lang_name} language that:

1. INTRODUCTION (30 seconds):
   - Open with a hook that grabs attention
   - Define what {topic} actually is
   - Why it affects people

2. THE PROBLEM (60 seconds):
   - Explain the dangers and consequences
   - Share statistics or real-world impacts if relevant
   - Help listeners understand why this matters to them

3. PREVENTION & SOLUTIONS (90 seconds):
   - Specific steps people can take to prevent/protect themselves
   - What to do if they encounter this issue
   - Resources or organizations that can help
   - Practical, actionable advice

4. EMPOWERMENT & CALL TO ACTION (30 seconds):
   - Inspire listeners to take action
   - Encourage them to spread awareness
   - End with a powerful, memorable message

Style guidelines:
- Write in {lang_name} language ONLY
- Use clear, accessible language understandable to all ages
- Include specific examples or scenarios when helpful
- Sound like a trusted authority figure giving a TED-style talk
- Be informative but NOT fear-mongering
- Include pauses/natural breaks where indicated (use … for dramatic pauses)
- Make it personal and relatable
- Create urgency without panic
- Do NOT include markers, timestamps, or headings
- Output ONLY the narration script, nothing else

Total script should be approximately 850-1000 words to fit a 3-4 minute video."""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        script = response.text.strip()
        return script
    except Exception as e:
        print(f"⚠️  Awareness lecture generation failed: {e}")
        return f"Welcome to this awareness campaign about {topic}. Understanding and preventing {topic} is important for everyone. Please seek authoritative sources for more information. Thank you."


def generate_awareness_caption(topic: str, language: str) -> str:
    """
    Generate a focused, short awareness caption (2-4 sentences) about a topic.
    This is used as a generic caption for all images in awareness mode.
    
    Example output: "Cybersecurity means protecting your personal information and devices from online threats. 
                    Always use strong passwords, avoid clicking unknown links, and never share OTPs or private data. 
                    Stay alert online—one small mistake can lead to data theft or hacking."
    """
    _ensure_configured()

    lang_name = LANG_NAMES.get(language, "English")

    prompt = f"""Generate a short, focused awareness message about: {topic}

Requirements:
- Write in {lang_name} language ONLY
- 2-4 sentences maximum
- Start with a clear definition or statement (what is {topic}?)
- Include 1-2 practical tips or prevention methods
- End with an empowering call to action or motivation
- Use accessible, clear language
- Sound authoritative but hopeful
- Do NOT include any labels, numbers, or formatting
- Output ONLY the awareness message, nothing else

Make it work as a caption that could apply to any image in an awareness video about {topic}."""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        caption = response.text.strip()
        return caption
    except Exception as e:
        print(f"⚠️  Awareness caption generation failed: {e}")
        return f"{topic} is an important issue that affects many people. Stay informed, take action, and help spread awareness. Together, we can make a difference."


def suggest_music_vibe(captions: list[str]) -> str:
    """Analyze captions and return the best music vibe for this project."""
    _ensure_configured()

    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(captions))
    prompt = f"""Analyze these image descriptions and decide the single best background music mood for a video slideshow:

{numbered}

Choose EXACTLY ONE from this list:
calm, romantic, rock, happy, sad, motivational

Reply with ONLY the one word — nothing else."""

    try:
        gen_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(prompt)
        vibe = response.text.strip().lower().replace('"', '').replace("'", "")
        valid = ["calm", "romantic", "rock", "happy", "sad", "motivational"]
        return vibe if vibe in valid else "calm"
    except Exception:
        return "calm"
