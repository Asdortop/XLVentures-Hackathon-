"""
Pure-Python semantic vector memory store.
Primary: sentence-transformers (all-MiniLM-L6-v2) + numpy cosine similarity
Fallback: TF-IDF bag-of-words similarity (pure stdlib — always works)

Stores vectors as JSON in SQLite (vector_memory.db).
Per-domain table: embeddings_{domain_slug}
"""
import json
import math
import re
import sqlite3
from pathlib import Path

VECTOR_DB_PATH = Path(__file__).parent.parent / "vector_memory.db"

_model = None
_use_tfidf = False   # set True if sentence-transformers unavailable
_available_checked = False


def _check_available() -> bool:
    global _available_checked, _use_tfidf
    if _available_checked:
        return True
    _available_checked = True
    try:
        from sentence_transformers import SentenceTransformer  # noqa
        import numpy as np  # noqa
        _use_tfidf = False
    except Exception as e:
        print(f"[VectorStore] sentence-transformers unavailable ({type(e).__name__}): {e}")
        print("[VectorStore] Falling back to TF-IDF similarity — still functional, lower accuracy")
        _use_tfidf = True
    return True


def _get_model():
    global _model, _use_tfidf
    _check_available()
    if _use_tfidf:
        return None
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("[VectorStore] Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[VectorStore] Model ready.")
    return _model


# ── TF-IDF fallback ───────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r'\b[a-z]{2,}\b', text.lower())


def _tfidf_vector(tokens: list[str], vocab: dict) -> list[float]:
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    vec = [0.0] * len(vocab)
    for term, idx in vocab.items():
        tf = freq.get(term, 0) / max(len(tokens), 1)
        # simple IDF = 1 (no corpus — single-doc TF only)
        vec[idx] = tf
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    vocab = {t: i for i, t in enumerate(set(tokens_a + tokens_b))}
    if not vocab:
        return 0.0
    va = _tfidf_vector(tokens_a, vocab)
    vb = _tfidf_vector(tokens_b, vocab)
    return _cosine(va, vb)


# ── SQLite helpers ────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(str(VECTOR_DB_PATH))


def _ensure_table(conn: sqlite3.Connection, domain_slug: str) -> str:
    safe = re.sub(r'[^a-z0-9_]', '_', domain_slug.lower())
    table = f"embeddings_{safe}"
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id TEXT PRIMARY KEY,
            document TEXT NOT NULL,
            embedding TEXT,
            metadata TEXT NOT NULL DEFAULT '{{}}'
        )
    """)
    conn.commit()
    return table


# ── Public API ────────────────────────────────────────────────────────────────

def store_memory(domain_slug: str, doc_id: str, text: str, metadata: dict) -> bool:
    """Embed and upsert. Falls back to storing doc without vector (TF-IDF at query time)."""
    _check_available()
    try:
        embedding_json = None
        model = _get_model()
        if model is not None:
            import numpy as np
            vec = model.encode(text)
            embedding_json = json.dumps(vec.tolist())

        conn = _get_conn()
        table = _ensure_table(conn, domain_slug)
        conn.execute(
            f"INSERT OR REPLACE INTO {table} (id, document, embedding, metadata) VALUES (?,?,?,?)",
            (doc_id, text, embedding_json, json.dumps(metadata)),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[VectorStore] store failed: {e}")
        return False


def retrieve_similar(
    domain_slug: str,
    query_text: str,
    n: int = 5,
    min_similarity: float = 0.30,
) -> list[dict]:
    """Find top-n similar past memories. Uses neural embeddings or TF-IDF fallback."""
    _check_available()
    try:
        conn = _get_conn()
        table = _ensure_table(conn, domain_slug)
        rows = conn.execute(f"SELECT id, document, embedding, metadata FROM {table}").fetchall()
        conn.close()
        if not rows:
            return []

        scored = []
        model = _get_model()

        if model is not None and not _use_tfidf:
            # Neural embedding similarity
            import numpy as np
            query_vec = model.encode(query_text)
            for row_id, doc, emb_json, meta_json in rows:
                if not emb_json:
                    continue
                emb = np.array(json.loads(emb_json))
                na = float(np.linalg.norm(query_vec))
                nb = float(np.linalg.norm(emb))
                if na == 0 or nb == 0:
                    continue
                sim = float(np.dot(query_vec, emb) / (na * nb))
                if sim >= min_similarity:
                    scored.append({
                        "id": row_id,
                        "document": doc,
                        "metadata": json.loads(meta_json) if meta_json else {},
                        "similarity": round(sim, 3),
                        "method": "neural",
                    })
        else:
            # TF-IDF fallback
            for row_id, doc, _, meta_json in rows:
                sim = _tfidf_similarity(query_text, doc)
                if sim >= min_similarity:
                    scored.append({
                        "id": row_id,
                        "document": doc,
                        "metadata": json.loads(meta_json) if meta_json else {},
                        "similarity": round(sim, 3),
                        "method": "tfidf",
                    })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:n]
    except Exception as e:
        print(f"[VectorStore] retrieve failed: {e}")
        return []


def collection_count(domain_slug: str) -> int:
    try:
        conn = _get_conn()
        table = _ensure_table(conn, domain_slug)
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def warm_up():
    """Pre-load model at startup."""
    _get_model()
