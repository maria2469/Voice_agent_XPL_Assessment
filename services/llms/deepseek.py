import os
import requests
from dotenv import load_dotenv
from langchain_core.runnables import Runnable

load_dotenv()

class DeepSeekLLM(Runnable):
    """
    Runnable wrapper for DeepSeek via OpenRouter.
    """
    def __init__(self, model="deepseek/deepseek-v3.2"):
        self.model = model
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment variables.")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def invoke(self, prompt, *args, **kwargs):
        # Ensure prompt is string
        if hasattr(prompt, "to_string"):
            prompt = prompt.to_string()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            return f"DeepSeek API request failed: {e}"
        except KeyError:
            return f"Unexpected response from DeepSeek API: {response.text}"

def get_llm():
    return DeepSeekLLM()