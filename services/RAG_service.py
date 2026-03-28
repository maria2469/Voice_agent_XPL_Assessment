from db.vector_store import get_vector_store_sync
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableMap

from services.llms.gemini import get_llm as get_gemini_llm
from services.llms.kimi import get_llm as get_kimi_llm
from services.llms.deepseek import get_llm as get_deepseek_llm

class RAGService:
    def __init__(self, llm_name: str = "gemini"):
        self.vector_store = get_vector_store_sync()
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5},
        )

        # Dynamically choose LLM
        llm_name = llm_name.lower()
        if llm_name == "kimi":
            self.llm = get_kimi_llm()
        elif llm_name == "deepseek":
            self.llm = get_deepseek_llm()
        else:
            self.llm = get_gemini_llm()

        self.prompt = PromptTemplate(
            template="""
You are a friendly, knowledgeable assistant. Answer questions clearly, directly, and in first person, as if you are speaking to the user. Use the context to provide accurate and helpful answers.

Context:
{context}

Question:
{question}

Instructions:
1. Speak directly to the user, using "you" or "I" when appropriate.
2. Use the context as your primary source to answer the question.
3. If the context is incomplete, reason carefully and provide helpful guidance, but do not make up facts.
4. Keep your answers concise, clear, and user-focused.
5. Reference the context only when relevant.
6. If the answer cannot be determined from the context, say:
"I couldn't find this information on the website."

Answer:
""",
            input_variables=["context", "question"],
        )

        self.chain = self._build_chain()

    def _format_docs(self, docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def _build_chain(self):
        retrieve = RunnableMap({
            "question": RunnablePassthrough(),
            "docs": self.retriever,
        })

        format_context = RunnableMap({
            "question": lambda x: x["question"],
            "context": lambda x: self._format_docs(x["docs"]),
            "source_documents": lambda x: x["docs"],
        })

        generate = RunnableMap({
            "answer": self.prompt | self.llm | StrOutputParser(),
            "source_documents": lambda x: x["source_documents"],
        })

        return retrieve | format_context | generate

    def query(self, user_query: str) -> dict:
        result = self.chain.invoke(user_query)
        return {
            "answer": result["answer"],
            "sources": [
                {
                    "title": doc.metadata.get("title"),
                    "url": doc.metadata.get("url"),
                    "category": doc.metadata.get("category"),
                }
                for doc in result["source_documents"]
            ],
        }


if __name__ == "__main__":
    print("Choose LLM: gemini, kimi, deepseek")
    llm_choice = input("LLM choice: ").strip().lower()
    rag = RAGService(llm_name=llm_choice)

    while True:
        q = input("\nAsk: ")
        if q.lower() in ["exit", "quit"]:
            break
        result = rag.query(q)
        print("\nAnswer:\n", result["answer"])
        print("\nSources:")
        for s in result["sources"]:
            print(s)