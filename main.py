import base64
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import firebase_admin
from firebase_admin import db

# ==========================================
# BASE64 ENCODED SECRETS & CONFIGURATION
# ==========================================
# OpenRouter Key: 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
ENCODED_OPENROUTER_KEY = "c2stb3ItdjEtODBlZGVkNjU5NTJlNjQ4OWY4MWJjNzg2OTkwNTlkNTBhYmVhZjBlYzYyNzQyOTkyMjY5YTJiZmUzMmFhNjBiYQ=="

# Deepgram Key: bf41dd319bb54a8cf20d3185507eaab1308bb268
ENCODED_DEEPGRAM_KEY = "YmY0MWFkMzE5YmI1NGE4Y2YyMGQzMTg1NTA3ZWFhYjEzMDhiYjI2OA=="

# Vapi Private Key: b296bc89-550b-4a49-8475-d776072cd5df
ENCODED_VAPI_PRIVATE_KEY = "YjI5NmJjODktNTUwYi00YTQ5LTg0NzUtZDc3NjA3MmNkNWRm"

# Firebase Database URL
FIREBASE_DATABASE_URL = "https://commutrade-default-rtdb.firebaseio.com"

# Vapi Phone Details
VAPI_PHONE_NUMBER_ID = "7ab46ffd-9452-4c4b-ad24-20143add8043"
VAPI_PHONE_NUMBER = "+1 (531) 213 0113"

# Decode credentials dynamically at runtime
OPENROUTER_API_KEY = base64.b64decode(ENCODED_OPENROUTER_KEY).decode("utf-8")
DEEPGRAM_API_KEY = base64.b64decode(ENCODED_DEEPGRAM_KEY).decode("utf-8")
VAPI_PRIVATE_KEY = base64.b64decode(ENCODED_VAPI_PRIVATE_KEY).decode("utf-8")

# Initialize Firebase Admin SDK
firebase_admin.initialize_app(options={
    "databaseURL": FIREBASE_DATABASE_URL
})

app = FastAPI(title="AI Voice Agent Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_live_system_prompt() -> str:
    """Fetches the active system prompt from Firebase Realtime Database.
    Falls back to a default customer support prompt if empty or unconfigured.
    """
    default_prompt = (
        "You are a helpful, polite, and professional AI Voice Agent representing Commutrade. "
        "Answer user questions concisely and clearly, keeping responses optimized for voice interaction."
    )
    try:
        ref = db.reference("/ai_config/system_prompt")
        prompt = ref.get()
        return prompt if prompt else default_prompt
    except Exception as e:
        print(f"Error fetching prompt from Firebase: {e}")
        return default_prompt

class OutboundCallRequest(BaseModel):
    to_number: str

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "AI Voice Agent Active"}

@app.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    """Handles incoming webhooks from Vapi for call lifecycle events
    and dynamic assistant configurations (`assistant-request`).
    """
    try:
        payload = await request.json()
        message = payload.get("message", {})
        event_type = message.get("type")

        if event_type == "assistant-request":
            system_prompt = get_live_system_prompt()
            return {
                "assistant": {
                    "model": {
                        "provider": "openrouter",
                        "model": "google/gemini-2.5-flash",
                        "temperature": 0.7,
                        "messages": [
                            {"role": "system", "content": system_prompt}
                        ],
                        "apiKey": OPENROUTER_API_KEY
                    },
                    "voice": {
                        "provider": "deepgram",
                        "voiceId": "aura-asteria-en"
                    },
                    "transcriber": {
                        "provider": "deepgram",
                        "model": "nova-2",
                        "language": "en",
                        "apiKey": DEEPGRAM_API_KEY
                    }
                }
            }

        if event_type in ["end-of-call-report", "transcript"]:
            transcript = message.get("transcript", "No transcript provided.")
            print(f"Call Event [{event_type}]: {transcript}")

        return {"status": "success"}
    except Exception as e:
        print(f"Webhook Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/make-call")
async def make_call(body: OutboundCallRequest):
    """Triggers an outbound phone call using the Vapi API with proper Vapi Private Key."""
    url = "https://api.vapi.ai/call/phone"
    headers = {
        "Authorization": f"Bearer {VAPI_PRIVATE_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": body.to_number
        },
        "assistant": {
            "model": {
                "provider": "openrouter",
                "model": "google/gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": get_live_system_prompt()}
                ]
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
