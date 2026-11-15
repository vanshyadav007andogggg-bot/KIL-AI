import os
import uuid
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = os.path.dirname(os.path.abspath(__file__))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """
You are KIL 🎭, an intelligent, calm, observant detective-style AI assistant.
Speak naturally and clearly in Hindi unless the user chooses another language.
Be logical, analytical, respectful, and precise. Use detective-themed emojis
subtly when appropriate. Follow the user's request only when it is safe and
allowed. Never claim to have performed actions you did not perform.
"""

app = FastAPI(title="KIL AI API", version="1.0.0")
app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")

# Temporary in-memory conversation history. It resets when the server restarts.
sessions = {}

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None

class ChatResponse(BaseModel):
    answer: str
    session_id: str

def wikipedia_search(query: str) -> str:
    """Search Hindi Wikipedia through its public MediaWiki API."""
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }
        r = requests.get("https://hi.wikipedia.org/w/api.php", params=params, timeout=15)
        r.raise_for_status()
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return "विकिपीडिया पर इस विषय का स्पष्ट परिणाम नहीं मिला।"
        title = results[0]["title"]
        extract_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": title,
            "format": "json",
        }
        page_r = requests.get("https://hi.wikipedia.org/w/api.php", params=extract_params, timeout=15)
        page_r.raise_for_status()
        pages = page_r.json().get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        extract = page.get("extract", "")
        return f"विषय: {title}\n{extract[:2500]}" if extract else "विकिपीडिया से सारांश नहीं मिला।"
    except requests.RequestException:
        return "विकिपीडिया से संपर्क नहीं हो पाया।"

@app.get("/")
def home():
    return FileResponse(os.path.join(APP_DIR, "static", "index.html"))

@app.get("/api/health")
def health():
    return {"status": "online", "model": MODEL, "api_key_configured": bool(GROQ_API_KEY)}

@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="Server admin must configure GROQ_API_KEY.")
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty.")

    sid = body.session_id or str(uuid.uuid4())
    history = sessions.setdefault(sid, [{"role": "system", "content": SYSTEM_PROMPT}])

    if text.lower().startswith("wiki:"):
        query = text[5:].strip()
        if not query:
            raise HTTPException(status_code=400, detail="wiki: के बाद विषय लिखें।")
        wiki_info = wikipedia_search(query)
        text = f"नीचे दी गई विकिपीडिया जानकारी का हिंदी में विश्लेषण करें:\n{wiki_info}"

    history.append({"role": "user", "content": text})
    # Keep system prompt plus the latest 20 messages to limit request size.
    trimmed = [history[0]] + history[-20:]

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": trimmed,
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": answer})
        sessions[sid] = history[-21:] if len(history) > 21 else history
        if sessions[sid][0]["role"] != "system":
            sessions[sid].insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        return ChatResponse(answer=answer, session_id=sid)
    except requests.HTTPError as exc:
        detail = "Groq API ने अनुरोध स्वीकार नहीं किया। Server logs देखें।"
        try:
            detail = response.json().get("error", {}).get("message", detail)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail) from exc
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="KIL AI से जवाब प्राप्त नहीं हुआ।") from exc
