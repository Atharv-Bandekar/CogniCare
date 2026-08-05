# src/models/schemas.py
from pydantic import BaseModel

"""
Data Schemas (Models)
Defines the expected request payloads from the frontend using Pydantic.
This ensures strict type-checking and automatic validation before the data ever reaches our agents.
"""

class QuestionRequest(BaseModel):
    """
    Payload for requesting a new daily memory question.
    """
    language: str = "English"

class AnalyzeRequest(BaseModel):
    """
    Payload for submitting a user's answer to the daily question.
    Includes the original question to provide context to the evaluator agent.
    """
    language: str
    question: str
    user_response: str