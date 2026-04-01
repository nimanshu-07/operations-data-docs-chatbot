import os
import hashlib
import logging
import chromadb
import google.generativeai as genai
from chromadb.config import Settings
from pypdf import PdfReader
from dotenv import load_dotenv
from config import (
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL,
    CHROMA_PATH, DOCS_FOLDER, COLLECTION_NAME
)

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_pdf(path):
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append((i + 1, text))
    return pages


def load_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return [(1, f.read())]


def load_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return load_pdf(path)
    elif ext == ".txt":
        return load_txt(path)
    raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_period = chunk.rfind(". ")
            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if c]


def embed(text):
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]


def make_chunk_id(filename, page, chunk_index):
    raw = f"{filename}_p{page}_c{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_docs(docs_folder=DOCS_FOLDER, reset=False):
    client = chromadb.PersistentClient(path=CHROMA_PATH , settings=Settings(anonymized_telemetry=False))

    if reset:
        logger.info("Resetting document collection...")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(COLLECTION_NAME)
    existing_ids = set(collection.get()["ids"])

    if not os.path.exists(docs_folder):
        logger.warning(f"Docs folder '{docs_folder}' not found. Skipping ingestion.")
        return

    files = [f for f in os.listdir(docs_folder) if f.endswith((".pdf", ".txt"))]
    if not files:
        logger.info(f"No documents found in '{docs_folder}'")
        return

    for filename in files:
        filepath = os.path.join(docs_folder, filename)
        logger.info(f"Ingesting: {filename}")
        pages = load_file(filepath)
        total_chunks = 0

        for page_num, page_text in pages:
            for chunk_index, chunk in enumerate(chunk_text(page_text)):
                chunk_id = make_chunk_id(filename, page_num, chunk_index)
                if chunk_id in existing_ids:
                    continue
                collection.add(
                    documents=[chunk],
                    embeddings=[embed(chunk)],
                    ids=[chunk_id],
                    metadatas=[{"source": filename, "page": page_num, "chunk_index": chunk_index}]
                )
                total_chunks += 1

        logger.info(f"  → {total_chunks} new chunks from {filename}")

    logger.info(f"Total chunks in DB: {collection.count()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe and rebuild the document index")
    args = parser.parse_args()
    ingest_docs(reset=args.reset)
