"""
FastAPI main app — mounts all routes, initializes DB, seeds demo domains.
"""
import os
import sys
from pathlib import Path

# Ensure backend dir is in path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal, Domain, MemoryPattern
from core.adapter import reload_adapters, list_adapter_slugs
from routes.domains import router as domains_router
from routes.interactions import router as interactions_router
from routes.nba import router as nba_router
from routes.onboarding import router as onboarding_router
from routes.outcomes import router as outcomes_router

app = FastAPI(title="Praxis AI", version="1.0.0", description="Agentic Decision Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domains_router)
app.include_router(interactions_router)
app.include_router(nba_router)
app.include_router(onboarding_router)
app.include_router(outcomes_router)


@app.on_event("startup")
def startup():
    init_db()
    reload_adapters()
    _seed_demo_domains()
    print("[Praxis AI] Ready.")


def _seed_demo_domains():
    """Ensure demo domains exist in DB and have seed memory patterns."""
    db = SessionLocal()
    try:
        slugs = list_adapter_slugs()
        for slug in slugs:
            existing = db.query(Domain).filter(Domain.slug == slug).first()
            if not existing:
                # Derive name from slug
                name = slug.replace("_", " ").title()
                domain = Domain(slug=slug, name=name, industry=slug.split("_")[0])
                db.add(domain)
                db.commit()
                db.refresh(domain)
                print(f"[Seed] Created domain: {slug} (id={domain.id})")
            else:
                domain = existing

            # Seed a few memory patterns per domain if empty
            count = db.query(MemoryPattern).filter(MemoryPattern.domain_id == domain.id).count()
            if count == 0:
                _seed_memory_for_domain(db, domain)

        db.commit()
    finally:
        db.close()


def _seed_memory_for_domain(db, domain):
    from core.adapter import get_adapter
    try:
        adapter = get_adapter(domain.slug)
        intents = adapter.get("intents", {}).get("intents", [])
        actions = adapter.get("actions", {}).get("actions", [])
        if not intents or not actions:
            return
        top_action = actions[0]["action"] if actions else "Review and escalate"
        for i, intent in enumerate(intents[:3]):
            action = actions[min(i, len(actions) - 1)]["action"]
            db.add(MemoryPattern(
                domain_id=domain.id,
                issue_type=intent["id"],
                issue_text=f"Typical case: {intent.get('description', intent['label'])}",
                resolution=action,
                success_count=max(2, 5 - i),
                failure_count=i,
            ))
        print(f"[Seed] Seeded memory patterns for: {domain.slug}")
    except Exception as e:
        print(f"[Seed] Failed to seed memory for {domain.slug}: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
