import os
from dotenv import load_dotenv

# 1. Load the environment variables FIRST
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from groq import Groq
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

# Import your existing logic
from src.agents.interviewer import InterviewerAgent
from src.agents.evaluator import EvaluatorAgent
from src.agents.coordinator import CoordinatorAgent

# Notice: get_demo_user_id is GONE from this import line!
from src.database.db import supabase, log_conversation, log_insight, fetch_history, init_db

# Initialize agents
interviewer = InterviewerAgent()
evaluator = EvaluatorAgent()
coordinator = CoordinatorAgent()

# FastAPI Lifespan manages startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    threading.Thread(target=evaluator.load_model, daemon=True).start()
    yield

# Initialize the API
app = FastAPI(
    title="CogniCare AI API",
    description="Multi-Agent Backend for Cognitive Engagement",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Dependency ---
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Intercepts the Authorization header, extracts the JWT, and verifies 
    it with Supabase. Returns the secure user_id if valid.
    """
    token = credentials.credentials
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return user_response.user.id
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=401, detail="Not authenticated")


# --- Pydantic Models ---
class QuestionRequest(BaseModel):
    language: str = "English"

class AnalyzeRequest(BaseModel):
    language: str
    question: str
    user_response: str


# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "active", "agents": "initialized"}


@app.post("/api/question")
async def get_daily_question(req: QuestionRequest, user_id: str = Depends(get_current_user)):
    """Agent 1: Generates the localized daily memory question."""
    try:
        history = fetch_history(user_id)
        past_questions = [rec["question"] for rec in history] if history else []
        
        question = interviewer.generate_question(
            language=req.language, 
            past_questions=past_questions
        )
        return {"question": question, "language": req.language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_response(req: AnalyzeRequest, user_id: str = Depends(get_current_user)):
    """Agents 2 & 3: Evaluates the response and recommends an activity."""
    try:
        # 1. Log the initial conversation securely using the verified user_id
        conv_id = log_conversation(user_id, req.question, req.user_response)
        
        # 2. Agent 2: Evaluate 
        from src.agents.base import translate_to_english
        eval_text = translate_to_english(req.user_response, req.language)
        evaluation = evaluator.analyze(eval_text)
        
        # 3. Agent 3: Coordinate Activity
        activity = coordinator.generate_activity(
            req.user_response, 
            evaluation, 
            language=req.language
        )
        
        # 4. Log the final insights securely linking it to the conversation
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
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    """Receives an audio blob from the browser and transcribes it using Groq."""
    try:
        temp_file_path = f"temp_{audio.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(await audio.read())
            
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        with open(temp_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(temp_file_path, file.read()),
              model="whisper-large-v3",
              prompt="The user is answering a question. Might contain Hindi, Marathi, Tamil, or English.",
              response_format="json",
            )
            
        os.remove(temp_file_path)
        return {"text": transcription.text}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(user_id: str = Depends(get_current_user)):
    """Fetches the entire conversation and insight history for the dashboard."""
    try:
        # Securely fetch ONLY this user's history
        history_data = fetch_history(user_id)
        return {"history": history_data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))