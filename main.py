# main.py
import os
from dotenv import load_dotenv

# Initialize environment variables before importing any dependent modules
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.db import init_db
from backend.api.routes import elders
from backend.webhooks import twilio_webhook
from backend.api.routes import recommendations

"""
Main Application Entry Point
Configures FastAPI middleware, registers routing controllers, and manages startup/shutdown events.
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan Context Manager.
    Executes startup logic before accepting requests.
    """
    init_db()
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

# Mount the modular API routes for V2
app.include_router(elders.router, prefix="/api/elders", tags=["Elders"])
app.include_router(recommendations.router, prefix="/api", tags=["Recommendations"])
app.include_router(twilio_webhook.router, prefix="/webhooks", tags=["Twilio Webhooks"])