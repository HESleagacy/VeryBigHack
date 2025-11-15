from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import importlib
from contextlib import asynccontextmanager
import datetime as dt

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set in .env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY not set in .env")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["07"]
query_logs_collection = db["query_logs"]
print("Connected to MongoDB")

noise_engine = importlib.import_module("noise_engine")
generate_noisy_response = noise_engine.generate_noisy_response
load_paraphraser_model = noise_engine.load_paraphraser_model

class PromptRequest(BaseModel):
    prompt: str
    userId: str

class NoisyResponse(BaseModel):
    response: str

async def startup_event():
    print("\n" + "="*60)
    print("SENTINEL WRAPPERS SERVICE STARTED")
    print("="*60)
    print("MongoDB connected")
    print("DeepSeek API key ready")
    print("Loading T5 model...")
    try:
        load_paraphraser_model()
        print("T5 model loaded")
    except Exception as e:
        print(f"T5 load failed: {e}")
    print("Service ready")
    print("="*60 + "\n")

async def shutdown_event():
    print("\n[SHUTDOWN] Closing MongoDB...")
    mongo_client.close()
    print("[SHUTDOWN] Done")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()

app = FastAPI(lifespan=lifespan)

@app.post("/get_noisy_response", response_model=NoisyResponse)
async def get_noisy_response(request: PromptRequest):
    try:
        print("\n" + "="*60)
        print("GENERATING NOISY RESPONSE")
        print(f"User: {request.userId}")
        print(f"Prompt: {request.prompt}")

        result = await generate_noisy_response(request.prompt, DEEPSEEK_API_KEY)
        clean = result["clean_answer"]
        noisy = result["noisy_answer"]

        print(f"Clean: {clean[:100]}...")
        print(f"Noisy: {noisy[:100]}...")

        log = {
            "userId": request.userId,
            "timestamp": datetime.now(dt.timezone.utc),
            "prompt": request.prompt,
            "original_answer": clean,
            "noisy_answer_served": noisy,
            "response_type_served": "NOISY"
        }
        query_logs_collection.insert_one(log)
        print("Logged to DB")
        print("="*60 + "\n")

        return NoisyResponse(response=noisy)

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "sentinel-wrappers",
        "timestamp": datetime.now(dt.timezone.utc)
    }
