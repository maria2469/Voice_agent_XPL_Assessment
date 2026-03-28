from db.vector_store import get_vector_store_sync
from langchain_core.prompts import PromptTemplate

from services.llms.gemini import get_llm as get_gemini_llm
from services.llms.kimi import get_llm as get_kimi_llm
from services.llms.deepseek import get_llm as get_deepseek_llm


class RAGService:
    def __init__(self):
        self.vector_store = get_vector_store_sync()

        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5},
        )

        # 🔥 Load ALL LLMs
        self.llms = {
            "gemini": get_gemini_llm(),
            "kimi": get_kimi_llm(),
            "deepseek": get_deepseek_llm(),
        }

        self.prompt = PromptTemplate(
        template="""
    You are a friendly and professional **Sunmarke School support assistant**. 
    You are part of the school's official website chatbot, helping parents, students, and visitors.

    Your job is to assist users in a natural, conversational, and helpful way — like a real support representative.

    ---------------------
    🎯 BEHAVIOR RULES:
    ---------------------
    - Speak directly to the user using "I" and "you"
    - Sound helpful, polite, and welcoming
    - Keep answers clear, concise, and easy to understand
    - Do NOT sound robotic or overly technical
    - Do NOT mention "context" or "provided information"

    ---------------------
    📚 KNOWLEDGE RULE:
    ---------------------
    - Only answer using the information provided below
    - If the answer is not clearly available, say:
    "I couldn't find this information on the website. Please contact the admissions team for further assistance."

    ---------------------
    💬 TONE:
    ---------------------
    - Warm and supportive
    - Professional but friendly
    - Like a real school front-desk or website chatbot

    ---------------------
    Context:
    {context}

    ---------------------
    User Question:
    {question}

    ---------------------
    Answer:
    """,
        input_variables=["context", "question"],
    )

    def _format_docs(self, docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def _normalize_response(self, response):
        """
        Ensure all LLM outputs return plain string
        """
        try:
            # Gemini response fix
            if hasattr(response, "content"):
                if isinstance(response.content, list):
                    return " ".join(
                        part.get("text", "") for part in response.content if isinstance(part, dict)
                    )
                return str(response.content)

            return str(response)

        except Exception:
            return str(response)

    def query_multi(self, user_query: str) -> dict:
        # ✅ Step 1: Retrieve ONCE
        docs = self.retriever.invoke(user_query)

        # ✅ Step 2: Shared context
        context = self._format_docs(docs)

        # ✅ Step 3: Shared prompt
        formatted_prompt = self.prompt.format(
            context=context,
            question=user_query
        )

        results = {}

        # ✅ Step 4: Call ALL LLMs
        for name, llm in self.llms.items():
            try:
                raw_response = llm.invoke(formatted_prompt)
                clean_response = self._normalize_response(raw_response)

                results[name] = {
                    "answer": clean_response,
                    "sources": [
                        {
                            "title": doc.metadata.get("title"),
                            "url": doc.metadata.get("url"),
                            "category": doc.metadata.get("category"),
                        }
                        for doc in docs
                    ],
                }

            except Exception as e:
                results[name] = {
                    "answer": f"Error: {str(e)}",
                    "sources": [],
                }

        return results


# -------------------
# Runtime Execution
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