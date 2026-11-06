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
# OpenRouter Key
ENCODED_OPENROUTER_KEY = "c2stb3ItdjEtODBlZGVkNjU5NTJlNjQ4OWY4MWJjNzg2OTkwNTlkNTBhYmVhZjBlYzYyNzQyOTkyMjY5YTJiZmUzMmFhNjBiYQ=="

# Deepgram Key
ENCODED_DEEPGRAM_KEY = "YmY0MWFkMzE5YmI1NGE4Y2YyMGQzMTg1NTA3ZWFhYjEzMDhiYjI2OA=="

# Twilio Credentials (Account SID & Auth Token)
# Account SID: AC7278afcd191be543b24d41b7de42a1f2
# Auth Token: fd042f3e9d20685fd088ce6ec83b78cd
ENCODED_TWILIO_SID = "QUM3Mjc4YWZjZDE5MWJlNTQzYjI0ZDRhYjdkZTQyYTFmMg=="
ENCODED_TWILIO_TOKEN = "ZmQwNDJmM2U5ZDIwNjg1ZmQwODhjZTZlYzgzYjc4Y2Q="

# Firebase Database URL
FIREBASE_DATABASE_URL = "https://commutrade-default-rtdb.firebaseio.com"

# Twilio Phone Number
TWILIO_PHONE_NUMBER = "+17372508034"

# Decode credentials dynamically at runtime
OPENROUTER_API_KEY = base64.b64decode(ENCODED_OPENROUTER_KEY).decode("utf-8")
DEEPGRAM_API_KEY = base64.b64decode(ENCODED_DEEPGRAM_KEY).decode("utf-8")
TWILIO_ACCOUNT_SID = base64.b64decode(ENCODED_TWILIO_SID).decode("utf-8")
TWILIO_AUTH_TOKEN = base64.b64decode(ENCODED_TWILIO_TOKEN).decode("utf-8")

# Initialize Firebase Admin SDK
firebase_admin.initialize_app(options={
    "databaseURL": FIREBASE_DATABASE_URL
})

app = FastAPI(title="AI Voice Agent Backend with Twilio", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_live_system_prompt() -> str:
    """Fetches the active system prompt from Firebase Realtime Database."""
    default_prompt = (
        "You are a helpful, polite, and professional AI Voice Agent. "
        "Answer user questions concisely and clearly."
    )
    try:
        ref = db.reference("/ai_config/system_prompt")
        prompt = ref.get()
        return prompt if prompt else default_prompt
    except Exception as e:
        print(f"Error fetching prompt from Firebase: {e}")
        return default_prompt

class CallRequest(BaseModel):
    to_number: str

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Twilio AI Voice Agent Active"}

@app.post("/trigger-twilio-call")
async def trigger_twilio_call(body: CallRequest):
    """Triggers an outbound call using Twilio API to any phone number (e.g. +918969475203)."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
    
    # Twilio expects form-urlencoded data
    payload = {
        "To": body.to_number,
        "From": TWILIO_PHONE_NUMBER,
        "Url": "https://webhooks.twilio.com/v1/Voice/Template/voice_speech_recognition"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            data=payload,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
