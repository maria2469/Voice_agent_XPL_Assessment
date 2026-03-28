# services/embedding.py
import asyncio
from core.config import settings
import time
import random
from typing import List

# ------------------ Import Google embeddings ------------------
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except ImportError:
    GoogleGenerativeAIEmbeddings = None

# ------------------ Import Cohere embeddings ------------------
try:
    from langchain_cohere.embeddings import CohereEmbeddings
    from cohere.errors import TooManyRequestsError as Cohere429Error
except ImportError:
    CohereEmbeddings = None
    Cohere429Error = Exception


class LoopingHybridEmbedding:
    """
    Alternates between Google Gemini and Cohere on rate limits (429),
    looping until all texts are embedded. Supports sync + async.
    """
    def __init__(self, batch_size: int = 50):
        if not GoogleGenerativeAIEmbeddings:
            raise RuntimeError("Google Gemini embeddings not installed")

        self.google = GoogleGenerativeAIEmbeddings(
            model="text-embedding-004",
            google_api_key=settings.GEMINI_API_KEY,
        )

        self.cohere = CohereEmbeddings(
            model="embed-english-v3.0",
            cohere_api_key=settings.COHERE_API_KEY
        ) if CohereEmbeddings else None

        if not self.cohere:
            print("⚠️ Cohere SDK not installed, fallback unavailable.")

        self.current = "google"
        self.batch_size = batch_size

    # ------------------ Sync embedding ------------------
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        remaining_texts = texts[:]

        while remaining_texts:
            batch = remaining_texts[:self.batch_size]
            try:
                print(f"🔹 Embedding batch of {len(batch)} texts using {self.current}...")
                if self.current == "google":
                    embeddings = self.google.embed_documents(batch)
                else:
                    embeddings = self.cohere.embed_documents(batch)
                all_embeddings.extend(embeddings)
                remaining_texts = remaining_texts[self.batch_size:]
            except (Exception, Cohere429Error) as e:
                print(f"⚠️ {self.current.capitalize()} rate limit or error: {e}")
                self.current = "cohere" if self.current == "google" else "google"
                wait_time = random.uniform(1, 3)
                print(f"⏳ Waiting {wait_time:.2f}s before retrying batch…")
                time.sleep(wait_time)

        print(f"✅ Finished embedding {len(all_embeddings)} documents.")
        return all_embeddings

    # ------------------ Async embedding ------------------
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Async wrapper for LangChain async vector stores.
        Runs synchronous batching in a thread executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed_documents, texts)


# ------------------ Factory ------------------
def get_embedding_service() -> LoopingHybridEmbedding:
    """
    Returns a LoopingHybridEmbedding instance.
    Can be used for both sync and async embeddings.
    """
    return LoopingHybridEmbedding()