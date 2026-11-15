import os
import uuid
import requests

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="KIL AI")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
You are KIL AI, an intelligent and helpful AI assistant.
You can communicate in Hindi and English.
Give clear, accurate and useful answers.
Your name is KIL AI.
"""

sessions = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


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
def chat(data: ChatRequest):

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY Render par set nahi hai."
        )

    user_message = data.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message khali hai."
        )

    session_id = data.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ] + history[-10:] + [
        {
            "role": "user",
            "content": user_message
        }
    ]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1500
    }

    try:
        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "error", {}
                ).get("message", "Groq API error")
            except Exception:
                error_message = response.text[:500]

            raise HTTPException(
                status_code=502,
                detail=f"Groq API Error: {error_message}"
            )

        result = response.json()

        reply = result["choices"][0]["message"]["content"]

        history.append({
            "role": "user",
            "content": user_message
        })

        history.append({
            "role": "assistant",
            "content": reply
        })

        sessions[session_id] = history[-10:]

        return {
            "reply": reply,
            "session_id": session_id,
            "model": MODEL
        }

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Groq server timeout."
        )

    except requests.exceptions.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Connection error: {str(error)}"
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(error)}"
        )
