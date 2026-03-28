import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Google Gemini API key for LangChain embeddings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Cohere API key for fallback embeddings
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

    # Database URL
    DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()