import asyncio
from db.vector_store import get_vector_store

async def inspect_embeddings():
    store = await get_vector_store()

    # Fetch all documents
    all_docs = await store.asimilarity_search("", k=1000)  # "" = dummy query
    print(f"Total documents stored: {len(all_docs)}\n")

    for i, doc in enumerate(all_docs[:5]):  # show first 5 docs
        print(f"Document {i+1}:")
        print(f"Source URL: {doc.metadata.get('source')}")
        print(f"Category: {doc.metadata.get('category')}")
        print(f"Content snippet: {doc.page_content[:200]}...\n")

if __name__ == "__main__":
    asyncio.run(inspect_embeddings())