from db.vector_store import get_vector_store_sync
from langchain_core.prompts import PromptTemplate
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.llms.gemini import get_llm as get_gemini_llm
from services.llms.kimi import get_llm as get_kimi_llm
from services.llms.deepseek import get_llm as get_deepseek_llm


class RAGService:
    def __init__(self):
        print("🔌 Initializing RAG Service...")

        self.vector_store = get_vector_store_sync()

        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5},
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

        print("✅ RAG Ready (Multi-LLM Mode)")

    # -------------------
    # Helpers
    # -------------------
    def _format_docs(self, docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def _normalize_response(self, response):
        try:
            # Gemini fix
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
    # 🔥 PARALLEL MULTI-RAG
    # -------------------
    def query_multi(self, user_query: str) -> dict:
        print("🔍 Retrieving documents...")

        # ✅ Step 1: Retrieve ONCE
        docs = self.retriever.invoke(user_query)

        # ✅ Step 2: Shared context
        context = self._format_docs(docs)

        # ✅ Step 3: Shared prompt
        formatted_prompt = self.prompt.format(
            context=context,
            question=user_query
        )

        print("🤖 Running LLMs in parallel...")

        results = {}

        def call_llm(name, llm):
            try:
                raw = llm.invoke(formatted_prompt)
                clean = self._normalize_response(raw)
                return name, clean
            except Exception as e:
                return name, f"Error: {str(e)}"

        # 🚀 PARALLEL EXECUTION
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(call_llm, name, llm)
                for name, llm in self.llms.items()
            ]

            for future in as_completed(futures):
                name, answer = future.result()

                results[name] = {
                    "answer": answer,
                    "sources": [
                        {
                            "title": doc.metadata.get("title"),
                            "url": doc.metadata.get("url"),
                            "category": doc.metadata.get("category"),
                        }
                        for doc in docs
                    ],
                }

        print("✅ All LLMs responded")

        return results


# -------------------
# Runtime Test
# -------------------
if __name__ == "__main__":
    rag = RAGService()

    while True:
        q = input("\nAsk: ")
        if q.lower() in ["exit", "quit"]:
            break

        results = rag.query_multi(q)

        for model, res in results.items():
            print(f"\n===== {model.upper()} =====")
            print(res["answer"])