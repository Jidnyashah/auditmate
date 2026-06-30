"""
tools/rag_tools.py
------------------
ChromaDB-backed RAG tools for regulatory Q&A and audit trail search.
"""

import chromadb
from pathlib import Path
from typing import Optional
import sys
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# ── Embedding function (Cloud-based, no PyTorch needed) ───────
class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    def __call__(self, input: list[str]) -> list[list[float]]:
        if not input:
            return []
        from google import genai
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=input,
        )
        # response.embeddings is a list where each element has a .values property
        return [emb.values for emb in response.embeddings]

_EMBED_FN = GeminiEmbeddingFunction()


def _get_client() -> chromadb.PersistentClient:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks of ~chunk_size characters."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ── Indexing ──────────────────────────────────────────────────

def index_regulations(reg_dir: Optional[str] = None, force: bool = False) -> int:
    """
    Index all .txt files in the regulations directory into ChromaDB.
    Returns number of chunks indexed.
    """
    client = _get_client()

    if force:
        try:
            client.delete_collection(config.REGULATIONS_COLLECTION)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=config.REGULATIONS_COLLECTION,
        embedding_function=_EMBED_FN,
    )

    # Skip if already populated
    if collection.count() > 0 and not force:
        return collection.count()

    reg_path = Path(reg_dir) if reg_dir else config.DATA_DIR / "regulations"
    docs, ids, metas = [], [], []

    for txt_file in sorted(reg_path.glob("*.txt")):
        text = txt_file.read_text(encoding="utf-8")
        source = txt_file.stem
        chunks = _chunk_text(text)
        for j, chunk in enumerate(chunks):
            docs.append(chunk)
            ids.append(f"{source}_{j:03d}")
            metas.append({"source": source, "chunk": j})

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    return len(docs)


def index_audit_trail(audit_entries: list[dict]) -> int:
    """
    Index audit log entries into ChromaDB for semantic search.
    """
    client = _get_client()
    collection = client.get_or_create_collection(
        name=config.AUDIT_TRAIL_COLLECTION,
        embedding_function=_EMBED_FN,
    )

    docs, ids, metas = [], [], []
    for entry in audit_entries:
        text = f"{entry.get('event_type','')}: {entry.get('description','')}"
        doc_id = f"audit_{entry.get('id', len(docs))}"
        docs.append(text)
        ids.append(doc_id)
        metas.append({
            "severity":   entry.get("severity", "INFO"),
            "created_at": entry.get("created_at", ""),
        })

    if docs:
        collection.upsert(documents=docs, ids=ids, metadatas=metas)

    return len(docs)


# ── Retrieval ─────────────────────────────────────────────────

def search_regulations(query: str, n_results: int = 3) -> list[dict]:
    """Semantic search over the regulations collection."""
    client = _get_client()
    try:
        collection = client.get_collection(
            name=config.REGULATIONS_COLLECTION,
            embedding_function=_EMBED_FN,
        )
    except Exception:
        return []

    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count() or 1))
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text":       doc,
            "source":     meta.get("source", "unknown"),
            "score":      round(1 - dist, 4),   # convert distance → similarity
        })
    return output


def search_audit_trail(query: str, n_results: int = 3) -> list[dict]:
    """Semantic search over indexed audit trail entries."""
    client = _get_client()
    try:
        collection = client.get_collection(
            name=config.AUDIT_TRAIL_COLLECTION,
            embedding_function=_EMBED_FN,
        )
    except Exception:
        return []

    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text":       doc,
            "severity":   meta.get("severity", ""),
            "created_at": meta.get("created_at", ""),
            "score":      round(1 - dist, 4),
        })
    return output
