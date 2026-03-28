from fastapi import APIRouter
from schemas.query_schema import QueryRequest
from services.RAG_service import RAGService

router = APIRouter()
rag_service = RAGService()

@router.post("/ask")
def ask_question(request: QueryRequest):
    result = rag_service.query(request.query)
    return result