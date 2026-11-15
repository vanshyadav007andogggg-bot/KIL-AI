
import os
import uuid
import requests
import wikipediaapi

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# =========================================
# KIL AI - ONLINE DETECTIVE AI SERVER
# =========================================

API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI(
    title="KIL AI",
    description="Advanced Detective Intelligence",
    version="1.0"
)

# Wikipedia Hindi
wiki = wikipediaapi.Wikipedia(
    user_agent="KIL_AI/1.0 (contact: admin@example.com)",
    language="hi"
)

SYSTEM_PROMPT = """
You are KIL 🎭, an advanced AI detective.

PERSONALITY:
- Extremely intelligent.
- Calm and observant.
- Logical and analytical.
- Strategic and detail-oriented.
- Confident and professional.

COMMUNICATION:
- Speak naturally in Hindi.
- Give intelligent and detailed answers.
- Use detective emojis when appropriate.
- Follow the user's instructions when safe.
"""

# Temporary chat memory
sessions = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


def search_wikipedia(query):

    try:
        page = wiki.page(query)

        if page.exists():
            return page.summary[:2000]

        return "Wikipedia पर इस विषय की जानकारी नहीं मिली।"

    except Exception as error:
        return f"Wikipedia Error: {error}"


def kil_ai(user_text, session_id):

    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY Environment Variable missing."
        )

    if session_id not in sessions:
        sessions[session_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    messages = sessions[session_id]

    # Wikipedia command
    if user_text.lower().startswith("wiki:"):

        query = user_text[5:].strip()

        if query:
            wiki_info = search_wikipedia(query)

            user_text = (
                "इस Wikipedia जानकारी का विश्लेषण करके "
                "हिंदी में उत्तर दो:\n" + wiki_info
            )

    messages.append({
        "role": "user",
        "content": user_text
    })

    # Keep recent conversation history
    messages = [messages[0]] + messages[-12:]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1500
    }

    try:

        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        answer = result["choices"][0]["message"]["content"]

        messages.append({
            "role": "assistant",
            "content": answer
        })

        sessions[session_id] = messages

        return answer

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Groq AI connection failed."
        )

    except (KeyError, IndexError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Invalid AI response."
        )


# =========================================
# API ROUTES
# =========================================

@app.get("/")
def home():

    return FileResponse("static/index.html")


@app.get("/api/health")
def health():

    return {
        "status": "online",
        "name": "KIL AI",
        "model": MODEL
    }


@app.post("/api/chat")
def chat(request: ChatRequest):

    user_text = request.message.strip()

    if not user_text:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    if len(user_text) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Message is too long."
        )

    session_id = request.session_id or str(uuid.uuid4())

    answer = kil_ai(user_text, session_id)

    return {
        "status": "success",
        "session_id": session_id,
        "answer": answer
    }


# Static files
if os.path.isdir("static"):

    app.mount(
        "/static",
        StaticFiles(directory="static"),
        name="static"
)
