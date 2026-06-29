"""
Migration: Fix vector_memory.db tables to allow NULL embeddings (for TF-IDF fallback).
Also adds reasoning_summary column to nba_actions if missing.
"""
import sqlite3

# Fix 1: reasoning_summary column in praxis.db
conn = sqlite3.connect("praxis.db")
try:
    conn.execute("ALTER TABLE nba_actions ADD COLUMN reasoning_summary TEXT DEFAULT ''")
    conn.commit()
    print("nba_actions.reasoning_summary: added")
except sqlite3.OperationalError as e:
    print(f"nba_actions.reasoning_summary: {e}")
conn.close()

# Fix 2: Drop old NOT NULL embedding tables — new vector_store.py recreates them as nullable
import os
db_path = "vector_memory.db"
if os.path.exists(db_path):
    conn2 = sqlite3.connect(db_path)
    tables = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for (table,) in tables:
        # Check if embedding column is NOT NULL
        info = conn2.execute(f"PRAGMA table_info({table})").fetchall()
        for col in info:
            col_name, col_type, notnull = col[1], col[2], col[3]
            if col_name == "embedding" and notnull:
                print(f"Recreating {table} with nullable embedding...")
                conn2.execute(f"DROP TABLE IF EXISTS {table}")
                conn2.commit()
                print(f"  Dropped {table} — will be recreated on next use")
                break
    conn2.close()
    print("vector_memory.db: schema fixed")
else:
    print("vector_memory.db: does not exist yet, will be created fresh")

print("Migration complete.")
