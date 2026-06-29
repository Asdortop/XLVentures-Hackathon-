import sqlite3, os, json, sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Check vector_memory.db
db_path = "vector_memory.db"
if not os.path.exists(db_path):
    print("MISS: vector_memory.db does not exist yet")
    print("  -> No interactions have been approved/rejected yet, OR sentence-transformers failed")
else:
    size = os.path.getsize(db_path)
    print(f"OK: vector_memory.db exists — {size:,} bytes ({size//1024} KB)")
    conn = sqlite3.connect(db_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"   Tables: {[t[0] for t in tables]}")
    for (table,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"\n   [{table}] = {count} entries")
        rows = conn.execute(f"SELECT id, document, metadata FROM {table} LIMIT 5").fetchall()
        for row in rows:
            meta = json.loads(row[2]) if row[2] else {}
            print(f"     id={row[0]} | approved={meta.get('approved')} | intent={meta.get('issue_type')} | entity={meta.get('entity_name')}")
            print(f"     doc: {row[1][:90]}")
    conn.close()

# 2. Sentence transformers check
print("\n--- Sentence Transformers ---")
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    model = SentenceTransformer("all-MiniLM-L6-v2")
    v1 = model.encode("client churn risk renewal")
    v2 = model.encode("customer cancellation subscription renewal")
    sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    print(f"OK: model loaded, dim={len(v1)}")
    print(f"OK: similarity test (churn vs cancellation) = {sim:.3f}  ({'GOOD' if sim > 0.5 else 'LOW - check model'})")
except Exception as e:
    print(f"FAIL: {e}")

# 3. Vector store end-to-end test
print("\n--- Vector Store Module ---")
try:
    from memory.vector_store import store_memory, retrieve_similar, collection_count

    ok = store_memory(
        domain_slug="__test__",
        doc_id="diag_001",
        text="Client health score dropped to 45%, renewal in 30 days, churn risk high",
        metadata={"issue_type": "churn_risk", "resolution": "Schedule executive QBR",
                  "approved": True, "success_count": 1, "entity_name": "TestCorp", "severity": "critical"}
    )
    print(f"store_memory: {'OK' if ok else 'FAIL'}")

    results = retrieve_similar("__test__", "health score declining renewal approaching", n=3, min_similarity=0.2)
    print(f"retrieve_similar: {len(results)} result(s)")
    for r in results:
        print(f"  sim={r['similarity']} | {r['document'][:70]}")

    count = collection_count("__test__")
    print(f"collection_count(__test__): {count}")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback; traceback.print_exc()
