from chromadb.config import Settings

import chromadb
import google.generativeai as genai
from config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME, TOP_K_RESULTS


def embed_query(text):
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]


def retrieve(question, top_k=TOP_K_RESULTS):
    """
    Returns a list of matching chunks:
    [{"text": ..., "source": ..., "page": ..., "score": ...}]
    Returns empty list if no documents are indexed.
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH , settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(COLLECTION_NAME)

    if collection.count() == 0:
        return []

    query_embedding = embed_query(question)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", "?"),
            "score": round(dist, 4)
        })

    return chunks


def format_context(chunks):
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Source {i}: {chunk['source']}, Page {chunk['page']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)
