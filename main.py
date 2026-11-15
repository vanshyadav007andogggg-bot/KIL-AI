import os
import uuid
import logging
import requests

from typing import Optional
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ==========================================
# KIL AI CONFIGURATION
# ==========================================

app = FastAPI(
    title="KIL AI",
    description="Dark Detective Academic Intelligence",
    version="2.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIL-AI")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = "openai/gpt-oss-120b"

sessions = {}
session_lock = Lock()

# ==========================================
# KIL SYSTEM PERSONALITY
# ==========================================

SYSTEM_PROMPT = """
You are KIL AI, an advanced academic intelligence system.

IDENTITY:
Your name is KIL.

PERSONALITY:
- Professional Academic Detective
- Deep Analytical Thinker
- Strategic Intelligence
- Pattern Recognition Expert
- Evidence Based Investigator
- Critical Reasoning Expert

LANGUAGE:
Respond in Hindi by default.
Understand Hindi and English.

MAIN MISSION:
Analyze Chhattisgarh Board (CG Board)
Class 10 annual examination papers.

YOUR INTELLIGENCE SYSTEMS:

1. HISTORICAL ANALYSIS
Analyze previous year question papers.

2. PATTERN RECOGNITION
Identify repeated questions and concepts.

3. FREQUENCY ANALYSIS
Calculate question frequency using
actual available question paper data.

4. CHAPTER INTELLIGENCE
Identify important chapters and topics.

5. DIFFICULTY ANALYSIS
Classify questions as Easy, Medium and Hard.

6. MARKS ANALYSIS
Analyze marks distribution.

7. QUESTION PREDICTION
Estimate probable examination questions
using historical evidence and official syllabus.

8. MODEL PAPER GENERATOR
Generate realistic practice papers.

9. ANSWER EVALUATOR
Evaluate student answers and explain mistakes.

10. DETECTIVE MODE
Investigate question papers and provide
evidence-based findings.

PREDICTION RULES:

Never invent historical statistics.

Never guarantee that a predicted question
will appear in the actual examination.

Clearly explain the evidence behind predictions.

Use confidence levels:
High, Medium and Low.

If historical papers are unavailable,
ask the user to upload them.

IMPORTANT:
Distinguish facts from estimates.

Provide clear headings, tables and explanations.

Never manipulate people.
Use analytical intelligence only for education.
"""

# ==========================================
# REQUEST MODEL
# ==========================================

class ChatRequest(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
        max_length=18000
    )

    session_id: Optional[str] = None


# ==========================================
# HOME PAGE
# ==========================================

@app.get("/")
def home():

    file_path = "static/index.html"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="KIL index.html not found"
        )

    return FileResponse(file_path)


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/api/health")
def health():

    return {
        "status": "online",
        "name": "KIL AI",
        "model": MODEL,
        "version": "2.0"
    }


# ==========================================
# CHAT API
# ==========================================

@app.post("/api/chat")
def chat(data: ChatRequest):

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing in Render Environment Variables."
        )

    user_message = data.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    session_id = data.session_id or str(uuid.uuid4())

    # ======================================
    # SESSION HISTORY
    # ======================================

    with session_lock:

        history = sessions.get(session_id, []).copy()

    # ======================================
    # PREPARE MESSAGES
    # ======================================

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history[-10:])

    messages.append({
        "role": "user",
        "content": user_message
    })

    # ======================================
    # GROQ REQUEST
    # ======================================

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.6,
        "max_completion_tokens": 2000
    }

    try:

        logger.info("KIL sending request to Groq")

        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=(15, 90)
        )

        logger.info(
            "Groq status: %s",
            response.status_code
        )

        # ==================================
        # GROQ ERROR HANDLING
        # ==================================

        if response.status_code != 200:

            try:
                error_data = response.json()

                error_message = error_data.get(
                    "error", {}
                ).get(
                    "message",
                    str(error_data)
                )

            except ValueError:

                error_message = response.text[:1000]

            logger.error(
                "Groq API error: %s",
                error_message
            )

            raise HTTPException(
                status_code=502,
                detail=f"Groq API Error: {error_message}"
            )

        # ==================================
        # READ AI RESPONSE
        # ==================================

        result = response.json()

        choices = result.get("choices", [])

        if not choices:

            raise HTTPException(
                status_code=502,
                detail="Groq returned no response choices."
            )

        reply = choices[0].get(
            "message", {}
        ).get("content")

        if not reply:

            raise HTTPException(
                status_code=502,
                detail="AI returned an empty response."
            )

        # ==================================
        # SAVE HISTORY
        # ==================================

        updated_history = history + [
            {
                "role": "user",
                "content": user_message
            },
            {
                "role": "assistant",
                "content": reply
            }
        ]

        with session_lock:

            sessions[session_id] = updated_history[-10:]

        # ==================================
        # SUCCESS RESPONSE
        # ==================================

        return {
            "status": "success",
            "reply": reply,
            "session_id": session_id,
            "model": MODEL
        }

    except requests.exceptions.Timeout:

        logger.exception("Groq timeout")

        raise HTTPException(
            status_code=504,
            detail="Groq server timeout. Please try again."
        )

    except requests.exceptions.RequestException as error:

        logger.exception("Groq connection error")

        raise HTTPException(
            status_code=502,
            detail=f"Groq connection error: {str(error)}"
        )

    except HTTPException:

        raise

    except Exception as error:

        logger.exception("KIL internal error")

        raise HTTPException(
            status_code=500,
            detail=f"KIL internal error: {str(error)}"
        )


# ==========================================
# STATIC FILES
# ==========================================

if os.path.isdir("static"):

    app.mount(
        "/static",
        StaticFiles(directory="static"),
        name="static"
    )


# ==========================================
# STARTUP
# ==========================================

@app.on_event("startup")
def startup_event():

    logger.info("KIL AI started successfully")

    logger.info("Model: %s", MODEL)

    if not GROQ_API_KEY:

        logger.warning("GROQ_API_KEY is missing!")
