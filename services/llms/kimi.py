import requests
from langchain_core.runnables import Runnable
from core.config import settings

MOONSHOT_API_KEY = settings.MOONSHOT_API_KEY
MOONSHOT_API_URL = "https://api.moonshot.ai/v1/chat/completions"

class KimiLLM(Runnable):
    def __init__(self, model="kimi-k2.5"):
        self.model = model
        self.api_key = MOONSHOT_API_KEY

    def invoke(self, prompt, *args, **kwargs):
        if hasattr(prompt, "to_string"):
            prompt = prompt.to_string()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are Kimi, an AI assistant."},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            response = requests.post(MOONSHOT_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                return "Moonshot API rate limit exceeded. Try again later."
            elif response.status_code == 401:
                return "Moonshot API unauthorized. Check your API key."
            else:
                return f"Moonshot API error: {e}"
        except Exception as e:
            return f"Unexpected error calling Moonshot API: {e}"

def get_llm():
    return KimiLLM()