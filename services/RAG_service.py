from db.vector_store import get_vector_store_sync
from langchain_core.prompts import PromptTemplate
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import uuid

from services.llms.gemini import get_llm as get_gemini_llm
from services.llms.kimi import get_llm as get_kimi_llm
from services.llms.deepseek import get_llm as get_deepseek_llm
from services.voice_handling.voice_output import text_to_speech


TEMP_DIR = "temp_audio"


class RAGService:
    def __init__(self):
        print("🔌 Initializing RAG Service...")

        self.vector_store = get_vector_store_sync()

        # ⚡ Reduced k for faster retrieval
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3},   # 🔥 faster than 5
        )

        # 🚀 Load ALL LLMs once
        self.llms = {
            "gemini": get_gemini_llm(),
            "kimi": get_kimi_llm(),
            "deepseek": get_deepseek_llm(),
        }

        # 🎯 Optimized Prompt
        self.prompt = PromptTemplate(
            template="""
You are a friendly and professional Sunmarke School support assistant.

Speak naturally like a real school representative. Be helpful, polite, and clear.

RULES:
- Use ONLY the information provided
- If not found, say:
"I couldn't find this information on the website. Please contact the admissions team for further assistance."
- Do NOT mention "context"
- Keep answers concise and human-like

Context:
{context}

User Question:
{question}

Answer:
""",
            input_variables=["context", "question"],
        )

        print("✅ RAG Ready (Streaming Mode)")

    # -------------------
    # Helpers
    # -------------------
    def _format_docs(self, docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def _normalize_response(self, response):
        try:
            if hasattr(response, "content"):
                if isinstance(response.content, list):
                    return " ".join(
                        part.get("text", "")
                        for part in response.content
                        if isinstance(part, dict)
                    )
                return str(response.content)

            return str(response)

        except Exception:
            return str(response)

    # -------------------
    # 🔥 STREAMING MULTI-RAG
    # -------------------
    def query_multi_stream(self, user_query: str):
        print("🔍 Retrieving documents...")

        # ✅ Retrieve once
        docs = self.retriever.invoke(user_query)
        context = self._format_docs(docs)

        formatted_prompt = self.prompt.format(
            context=context,
            question=user_query
        )

        print("🤖 Running LLMs + TTS in parallel (streaming)...")

        def call_llm_and_tts(name, llm):
            try:
                # 🔥 LLM
                raw = llm.invoke(formatted_prompt)
                answer = self._normalize_response(raw)

                # 🔥 TTS immediately
                audio_file_name = f"{name}_{uuid.uuid4()}.mp3"
                audio_file_path = os.path.join(TEMP_DIR, audio_file_name)

                text_to_speech(answer, audio_file_path)

                print(f"✅ {name} done")

                return {
                    "model": name,
                    "text": answer,
                    "audioUrl": f"http://localhost:8000/audio/{audio_file_name}",
                    "sources": [
                        {
                            "title": doc.metadata.get("title"),
                            "url": doc.metadata.get("url"),
                            "category": doc.metadata.get("category"),
                        }
                        for doc in docs
                    ],
                    "error": None if answer else "No answer",
                }

            except Exception as e:
                return {
                    "model": name,
                    "text": "",
                    "audioUrl": None,
                    "sources": [],
                    "error": str(e),
                }

        # 🚀 Parallel execution
        with ThreadPoolExecutor(max_workers=len(self.llms)) as executor:
            futures = [
                executor.submit(call_llm_and_tts, name, llm)
                for name, llm in self.llms.items()
            ]

            # 🔥 STREAM results as they complete
            for future in as_completed(futures):
                yield future.result()


# -------------------
# 🧪 Test
# -------------------
if __name__ == "__main__":
    rag = RAGService()

    while True:
        q = input("\nAsk: ")
        if q.lower() in ["exit", "quit"]:
            break

        for res in rag.query_multi_stream(q):
            print(f"\n===== {res['model'].upper()} =====")
            print(res["text"])