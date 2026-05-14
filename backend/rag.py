import os
import re
import chromadb
import ollama
import sys
from backend.logger import logger

EMBED_MODEL = "nomic-embed-text"

# Create persistent ChromaDB
client = chromadb.PersistentClient(path="vectorstore")

collection = client.get_or_create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"},
)

# =========================================================
# 1. CLEANING
# =========================================================
def clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# 2. EMBEDDING ENGINE (FAST)
# =========================================================
def embed(text: str):
    """Fast Ollama embedding call."""
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response["embeddings"][0]


# =========================================================
# 3. CHUNKING ENGINE (OPTIMIZED)
# =========================================================
def chunk_text(text, chunk_size=180):
    """
    180-token chunks give BEST retrieval for small models.
    """
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])


# =========================================================
# 4. INGESTION
# =========================================================
def ingest(folder: str):
    doc_id = 0

    for filename in os.listdir(folder):
        if not filename.endswith(".txt"):
            continue

        with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
            raw = clean_text(f.read())

        for chunk in chunk_text(raw):
            vec = embed(chunk)

            collection.add(
                ids=[f"doc_{doc_id}"],
                documents=[chunk],
                embeddings=[vec],
                metadatas=[{"source": filename}],
            )
            doc_id += 1

    logger.info("Ingestion complete.")


# =========================================================
# 5. QUERY ENGINE (ULTRA FAST)
# =========================================================
def query(text: str, n_results=3):
    """Return top-n most relevant chunks."""
    vec = embed(text)

    results = collection.query(
        query_embeddings=[vec],
        n_results=n_results,
    )

    # If no documents found, avoid app crash
    if results is None or "documents" not in results:
        return {
            "documents": [[]],
            "metadatas": [[]]
        }

    return results


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ingest":
        if len(sys.argv) > 2:
            folder = sys.argv[2]
            ingest(folder)
        else:
            logger.info("Usage: python rag.py --ingest <folder>")
    else:
        logger.info("Usage: python rag.py --ingest <folder>")
