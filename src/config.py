import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "cognicare.db")
DEMO_USER_NAME = "Margaret"