from db.pg_vector import get_vector_store
from services.gemini import GeminiService

class RAGService:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.gemini = GeminiService()

    def query(self, user_query: str):
        docs = self.vector_store.similarity_search(user_query, k=5)

        context = "\n\n".join([doc.page_content for doc in docs])

        response = self.gemini.generate_response(user_query, context)

        return {
            "context": context,
            "response": response
        }