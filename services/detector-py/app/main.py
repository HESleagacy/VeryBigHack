from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import schedule
import time
import threading
import asyncio
from app.scoring import run_analysis_job
from app.blockchain import init_blockchain_logging


load_dotenv() 

# --- Environment & DB Setup ---
MONGODB_URI = os.getenv("MONGO_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGO_URI not set")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[os.getenv("DB_NAME", "07")]

print("Detector: Connected to MongoDB successfully")

# --- Scheduler Setup ---
def run_scheduler():
    print("[Scheduler] Starting background scheduler...")
    schedule.every(60).seconds.do(run_analysis_job, db=db)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- Lifespan Events (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("\n" + "=" * 60)
    print("🧠  SENTINEL DETECTOR SERVICE STARTED")
    print("=" * 60)
    print(f"✓ MongoDB connected")
    
    try:
        init_blockchain_logging()
        print("✓ Blockchain connector initialized")
    except Exception as e:
        print(f"🚨 ERROR: Failed to initialize blockchain connector: {e}")

    print("✓ Starting background detection loop...")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print(f"✓ Background analysis will run every 60 seconds")
    print("=" * 60 + "\n")
    
    yield
    
    # Shutdown
    print("\n[SHUTDOWN] Closing MongoDB connection...")
    mongo_client.close()
    print("[SHUTDOWN] Detector service stopped")

app = FastAPI(lifespan=lifespan)

# --- API Endpoints ---
@app.post("/run_analysis")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """
    Manually triggers an analysis run.
    Good for demos or forcing an update.
    """
    print("[API] Manual analysis run triggered...")
    background_tasks.add_task(run_analysis_job, db)
    return {"status": "Analysis triggered in background"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sentinel-detector"}
