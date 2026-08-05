# src/api/dependencies.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database.db import supabase

"""
API Dependencies & Security
Handles request interception, JWT token extraction, and user verification.
"""

# Initializes the standard HTTP Bearer security scheme for Swagger/OpenAPI documentation
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Intercepts the Authorization header, extracts the JWT, and securely verifies it against Supabase.
    
    Args:
        credentials: The Bearer token automatically extracted by FastAPI.
        
    Returns:
        str: The authenticated user's unique UUID.
        
    Raises:
        HTTPException: 401 Unauthorized if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        # Return the secure user ID to be used in database queries
        return user_response.user.id
        
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=401, detail="Not authenticated")