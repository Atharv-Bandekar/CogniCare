import os
from dotenv import load_dotenv

# 1. Load the environment variables FIRST
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

# Import your existing logic
from src.agents.interviewer import InterviewerAgent
from src.agents.evaluator import EvaluatorAgent
from src.agents.coordinator import CoordinatorAgent
from src.database.db import get_demo_user_id, log_conversation, log_insight, fetch_history, init_db

# Initialize agents
interviewer = InterviewerAgent()
evaluator = EvaluatorAgent()
coordinator = CoordinatorAgent()

# FastAPI Lifespan manages startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database and load the DeBERTa model into memory on startup
    init_db()
    # Loading in a thread so the server binds to the port immediately
    threading.Thread(target=evaluator.load_model, daemon=True).start()
    yield

# Initialize the API
app = FastAPI(
    title="CogniCare AI API",
    description="Multi-Agent Backend for Cognitive Engagement",
    version="1.0.0",
    lifespan=lifespan
)

# --- Add this CORS block right after initializing the app ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Allows your Next.js app to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Data Validation ---
class QuestionRequest(BaseModel):
    language: str = "English"

class AnalyzeRequest(BaseModel):
    language: str
    question: str
    user_response: str

# --- API Endpoints ---
@app.get("/health")
async def health_check():
    """Simple endpoint to verify the server is running."""
    return {"status": "active", "agents": "initialized"}

@app.post("/api/question")
async def get_daily_question(req: QuestionRequest):
    """Agent 1: Generates the localized daily memory question."""
    try:
        history = fetch_history()
        past_questions = [rec["question"] for rec in history] if history else []
        
        question = interviewer.generate_question(
            language=req.language, 
            past_questions=past_questions
        )
        return {"question": question, "language": req.language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_response(req: AnalyzeRequest):
    """Agents 2 & 3: Evaluates the response and recommends an activity."""
    try:
        user_id = get_demo_user_id()
        
        # 1. Log the initial conversation
        conv_id = log_conversation(user_id, req.question, req.user_response)
        
        # 2. Agent 2: Evaluate (Base translation logic is handled inside your evaluate pipeline)
        from src.agents.base import translate_to_english
        eval_text = translate_to_english(req.user_response, req.language)
        evaluation = evaluator.analyze(eval_text)
        
        # 3. Agent 3: Coordinate Activity
        activity = coordinator.generate_activity(
            req.user_response, 
            evaluation, 
            language=req.language
        )
        
        # 4. Log the final insights
        log_insight(
            conv_id,
            evaluation["sentiment_label"], evaluation["sentiment_score"],
            evaluation["engagement_level"], evaluation["engagement_score"],
            activity,
        )
        
        return {
            "evaluation": evaluation,
            "activity_plan": activity
        }
    except Exception as e:
        import traceback
        traceback.print_exc()  # <--- This will print the exact error to your terminal!
        raise HTTPException(status_code=500, detail=str(e))