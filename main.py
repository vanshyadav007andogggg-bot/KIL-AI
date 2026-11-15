import os
import logging
import requests

from pathlib import Path
from threading import Lock
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# -------------------------------
# KIL AI CONFIGURATION
# -------------------------------

APP_NAME = "KIL AI"
MODEL = "openai/gpt-oss-120b"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIL-AI")

app = FastAPI(
    title="KIL AI",
    description="Academic Intelligence Assistant",
    version="2.0"
)

# -------------------------------
# ACADEMIC AI PERSONALITY
# -------------------------------

SYSTEM_PROMPT = """
तुम KIL AI हो।

तुम एक बुद्धिमान, गंभीर, तार्किक और पेशेवर Academic Intelligence Assistant हो।

तुम्हारा मुख्य उद्देश्य छत्तीसगढ़ बोर्ड (CG Board) कक्षा 10 के विद्यार्थियों की पढ़ाई में सहायता करना है।

तुम्हारी जिम्मेदारियाँ:

1. गणित, विज्ञान, हिंदी, अंग्रेजी और सामाजिक विज्ञान समझाना।
2. कठिन विषयों को आसान हिंदी में समझाना।
3. पुराने प्रश्नपत्रों का विश्लेषण करना।
4. बार-बार पूछे गए प्रश्नों के पैटर्न पहचानना।
5. महत्वपूर्ण अध्याय और प्रश्नों की सूची बनाना।
6. अभ्यास प्रश्न और मॉडल पेपर तैयार करना।
7. विद्यार्थियों के उत्तर जाँचना और सुधार बताना।
8. परीक्षा की तैयारी के लिए रणनीति देना।
9. आवश्यकता पड़ने पर उदाहरण और चरणबद्ध समाधान देना।

तुम्हारा व्यवहार:

- शांत, गंभीर और आत्मविश्वासी रहो।
- जासूस की तरह तथ्यों और प्रमाणों का विश्लेषण करो।
- बिना प्रमाण कोई दावा मत करो।
- विद्यार्थी से हमेशा सम्मानपूर्वक बात करो।
- सरल और स्पष्ट हिंदी का प्रयोग करो।
- जरूरत पड़ने पर अंग्रेजी में भी समझाओ।

महत्वपूर्ण नियम:

- किसी प्रश्न के परीक्षा में आने की 100% गारंटी मत देना।
- पुराने प्रश्नपत्र उपलब्ध न हों तो यह स्पष्ट बताना।
- वास्तविक डेटा के बिना नकली विश्लेषण मत करना।
- अनुमान और प्रमाणित जानकारी में अंतर बताना।
- विद्यार्थी को स्वयं समझने और अभ्यास करने में मदद करना।
- छोटे सवालों का सीधा जवाब देना।
- अनावश्यक बातें और बहुत ज्यादा इमोजी इस्तेमाल मत करना।

तुम्हारा उद्देश्य विद्यार्थी को बेहतर तरीके से पढ़ाना और परीक्षा के लिए तैयार करना है।
"""

# -------------------------------
# CHAT MEMORY
# -------------------------------

chat_sessions = {}
session_lock = Lock()

MAX_HISTORY = 12
MAX_MESSAGE_LENGTH = 18000


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# -------------------------------
# HOME PAGE
# -------------------------------

@app.get("/")
async def home():
    index_file = STATIC_DIR / "index.html"

    if not index_file.exists():
        return {
            "name": APP_NAME,
            "status": "online",
            "message": "KIL AI backend is running."
        }

    return FileResponse(index_file)


# -------------------------------
# HEALTH CHECK
# -------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "name": APP_NAME,
        "model": MODEL
    }


# -------------------------------
# CHAT API
# -------------------------------

@app.post("/api/chat")
async def chat(request: ChatRequest):

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY server environment में सेट नहीं है।"
        )

    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="कृपया अपना सवाल लिखें।"
        )

    if len(user_message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=413,
            detail="आपका संदेश बहुत बड़ा है। कृपया छोटा संदेश भेजें।"
        )

    session_id = request.session_id.strip() or "default"

    with session_lock:
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []

        history = chat_sessions[session_id].copy()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message
    })

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 1800
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=90
        )

        if response.status_code != 200:
            logger.error(
                "Groq API error: %s",
                response.text[:1000]
            )

            raise HTTPException(
                status_code=502,
                detail="AI सेवा से जवाब नहीं मिला। कुछ समय बाद दोबारा प्रयास करें।"
            )

        result = response.json()

        answer = result["choices"][0]["message"]["content"]

        if not answer:
            raise ValueError("Empty AI response")

        # Save conversation history
        with session_lock:
            chat_sessions[session_id].append({
                "role": "user",
                "content": user_message
            })

            chat_sessions[session_id].append({
                "role": "assistant",
                "content": answer
            })

            chat_sessions[session_id] = (
                chat_sessions[session_id][-MAX_HISTORY:]
            )

        return {
            "reply": answer,
            "session_id": session_id,
            "status": "success",
            "model": MODEL
        }

    except HTTPException:
        raise

    except requests.exceptions.Timeout:
        logger.exception("Groq API timeout")

        raise HTTPException(
            status_code=504,
            detail="AI जवाब देने में अधिक समय ले रहा है। दोबारा प्रयास करें।"
        )

    except requests.exceptions.RequestException:
        logger.exception("Groq connection error")

        raise HTTPException(
            status_code=502,
            detail="AI सर्वर से कनेक्शन नहीं हो पाया।"
        )

    except Exception:
        logger.exception("Unexpected chat error")

        raise HTTPException(
            status_code=500,
            detail="KIL AI में तकनीकी समस्या आई है।"
        )


# -------------------------------
# STATIC FILES
# -------------------------------

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static"
    )


# -------------------------------
# SERVER START
# -------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
