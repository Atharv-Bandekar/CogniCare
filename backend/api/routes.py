# src/api/routes.py
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from groq import Groq
import traceback
import random

from backend.models.schemas import QuestionRequest, AnalyzeRequest
from backend.api.dependencies import get_current_user
from backend.database.db import log_conversation, log_insight, fetch_history
from backend.agents.interviewer import InterviewerAgent
from backend.agents.evaluator import EvaluatorAgent
from backend.agents.coordinator import CoordinatorAgent
"""
API Routes (Controllers)
Maps HTTP endpoints to specific business logic and AI agent workflows.
"""

# Initialize the router namespace
router = APIRouter()

# Instantiate AI Agents (Singletons used across requests)
interviewer = InterviewerAgent()
evaluator = EvaluatorAgent()
coordinator = CoordinatorAgent()

@router.get("/health")
async def health_check():
    """Simple ping endpoint to verify the server and agents are alive."""
    return {"status": "active", "agents": "initialized"}

# Make sure you import random at the top of routes.py!
import random 

@router.post("/api/question")
async def generate_daily_question(req: QuestionRequest, user_id: str = Depends(get_current_user)):
    try:
        history = fetch_history(user_id)
        past_questions = [rec["question"] for rec in history] if history else []
        
        # 1. Create a list of distinct topics for the AI to choose from
        topics = [
            "Childhood friendships and games",
            "A memorable travel experience",
            "The first job or career milestone",
            "A piece of advice given to them when they were young",
            "A historical event they lived through",
            "Their favorite hobbies or skills they learned",
            "Pets or animals they loved"
        ]
        
        # 2. Pick a random topic every single time this route is hit
        forced_topic = random.choice(topics)
        
        # 3. Pass that topic to your Interviewer Agent (you'll need to update the agent to accept this)
        question = interviewer.generate_question(
            language=req.language, 
            past_questions=past_questions,
            topic=forced_topic  # <-- Inject the random spark here
        )
        
        return {"question": question, "language": req.language}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/api/analyze")
async def analyze_response(req: AnalyzeRequest, user_id: str = Depends(get_current_user)):
    """
    Agents 2 & 3: Evaluates the response and recommends a cognitive activity.
    Orchestrates translation, emotional evaluation, activity generation, and database logging.
    """
    try:
        # Step 1: Securely log the raw conversation using the verified user ID
        conv_id = log_conversation(user_id, req.question, req.user_response)
        
        # Step 2: Agent 2 (Evaluator) analyzes sentiment and engagement
        from backend.agents.base import translate_to_english
        eval_text = translate_to_english(req.user_response, req.language)
        evaluation = evaluator.analyze(eval_text)
        
        # Step 3: Agent 3 (Coordinator) generates a customized activity plan
        activity = coordinator.generate_activity(req.user_response, evaluation, language=req.language)
        
        # Step 4: Persist the generated insights to Supabase
        log_insight(
            conv_id,
            evaluation["sentiment_label"], evaluation["sentiment_score"], 
            evaluation["engagement_level"], evaluation["engagement_score"], 
            activity
        )
        
        return {"evaluation": evaluation, "activity_plan": activity}
    except Exception as e:
        print("\n=== FATAL ERROR IN /api/analyze ===")
        traceback.print_exc() # <-- THIS will force the terminal to print the exact line number
        print("===================================\n")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...), 
    language: str = Form("English"), 
    user_id: str = Depends(get_current_user)
):
    try:
        temp_file_path = f"temp_{audio.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(await audio.read())
            
        iso_map = {
            "English": "en",
            "Hindi": "hi",
            "Marathi": "mr",
            "Tamil": "ta"
        }
        iso_code = iso_map.get(language, "en")
            
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        with open(temp_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(temp_file_path, file.read()),
              model="whisper-large-v3",
              language=iso_code,
              # 🚨 Notice the 'prompt' parameter has been completely deleted! 
              response_format="json",
            )
            
        os.remove(temp_file_path)
        return {"text": transcription.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/api/history")
async def get_history(user_id: str = Depends(get_current_user)):
    """
    Fetches the entire conversation and insight history for the user's dashboard view.
    """
    try:
        history_data = fetch_history(user_id)
        return {"history": history_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/refresh-question")
async def refresh_daily_question(req: QuestionRequest, user_id: str = Depends(get_current_user)):
    """
    Generates a new alternative daily question, ensuring it avoids past history questions.
    """
    try:
        history = fetch_history(user_id)
        past_questions = [rec["question"] for rec in history] if history else []

        if req.current_question:
            past_questions.append(req.current_question)
        
        # Calls the Interviewer Agent for a fresh question
        question = interviewer.generate_question(language=req.language, past_questions=past_questions)
        return {"question": question, "language": req.language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))