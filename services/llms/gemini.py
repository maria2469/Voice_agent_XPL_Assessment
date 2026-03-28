from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.3,
    )