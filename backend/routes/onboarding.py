from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.adapter_builder import generate_adapter, deploy_adapter
from core.adapter import get_adapter

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingInput(BaseModel):
    company_name: str
    industry: str = "B2B"
    what_they_manage: str = ""
    decisions: str = ""
    primary_entity: str = "Account"
    sops_text: str = ""
    rules_text: str = ""
    actions_text: str = ""
    crm_sample: str = ""


class ConfirmInput(BaseModel):
    slug: str
    company_name: str
    industry: str
    files: dict  # { filename: yaml_content }


@router.post("/configure")
def configure(req: OnboardingInput):
    """
    Stage 1: Generate + validate adapter config.
    Returns preview for Blueprint Canvas display.
    """
    inputs = req.dict()
    try:
        result = generate_adapter(inputs)
        return {
            "slug": result["slug"],
            "preview": result["preview"],
            "attempts": result["attempts"],
            "raw_files": result["files"],
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/confirm")
def confirm(req: ConfirmInput):
    """
    Stage 2: Save confirmed adapter to disk and register domain in DB.
    """
    from database import SessionLocal, Domain
    db = SessionLocal()
    try:
        # Save adapter files
        deploy_adapter(req.slug, req.files)

        # Register domain in DB if not exists
        existing = db.query(Domain).filter(Domain.slug == req.slug).first()
        if not existing:
            domain = Domain(
                slug=req.slug,
                name=req.company_name,
                industry=req.industry,
            )
            db.add(domain)
            db.commit()
            db.refresh(domain)
            domain_id = domain.id
        else:
            domain_id = existing.id

        # Seed initial memory patterns from adapter knowledge
        try:
            adapter = get_adapter(req.slug)
            from database import MemoryPattern
            from datetime import datetime
            intents = adapter.get("intents", {}).get("intents", [])
            actions = adapter.get("actions", {}).get("actions", [])
            for intent in intents[:2]:
                top_action = actions[0]["action"] if actions else "Review and take action"
                existing_pattern = db.query(MemoryPattern).filter(
                    MemoryPattern.domain_id == domain_id,
                    MemoryPattern.issue_type == intent["id"],
                ).first()
                if not existing_pattern:
                    db.add(MemoryPattern(
                        domain_id=domain_id,
                        issue_type=intent["id"],
                        issue_text=f"Auto-seeded from adapter for intent: {intent['label']}",
                        resolution=top_action,
                        success_count=2,
                        failure_count=0,
                    ))
            db.commit()
        except Exception:
            pass

        return {"domain_id": domain_id, "slug": req.slug, "status": "deployed"}
    finally:
        db.close()
