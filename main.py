# main.py
import os
import threading
from dotenv import load_dotenv

# Initialize environment variables before importing any dependent modules
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.db import init_db
from backend.api.routes import router, evaluator
from backend.api.routes import elders
from backend.webhooks import twilio_webhook

"""
Main Application Entry Point
Configures FastAPI middleware, registers routing controllers, and manages startup/shutdown events.
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan Context Manager.
    Executes startup logic (DB initialization, async model loading) before accepting requests,
    and handles graceful shutdown when the server stops.
    """
    init_db()
    
    # Load heavy ML models on a background thread so it doesn't block server startup
    threading.Thread(target=evaluator.load_model, daemon=True).start()
    yield

# Initialize the FastAPI instance
app = FastAPI(
    title="CogniCare AI API",
    description="Multi-Agent Backend for Cognitive Engagement",
    version="1.0.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your exact frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the modular API routes
app.include_router(router)
app.include_router(elders.router, prefix="/api/elders", tags=["Elders"])
app.include_router(twilio_webhook.router, prefix="/webhooks", tags=["Twilio Webhooks"])