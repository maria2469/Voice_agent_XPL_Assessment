import google.generativeai as genai
from core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-pro")

    def generate_response(self, query: str, context: str) -> str:
        prompt = f"""
        You are a helpful assistant.
        ONLY answer from the provided context.

        Context:
        {context}

        Question:
        {query}

        If the answer is not in the context, say:
        "I couldn't find this information on the website."
        """

        response = self.model.generate_content(prompt)
        return response.text