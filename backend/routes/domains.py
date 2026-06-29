from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Domain
from core.adapter import list_adapter_slugs, get_adapter

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("")
def list_domains(db: Session = Depends(get_db)):
    domains = db.query(Domain).all()
    result = []
    for d in domains:
        adapter_ui = {}
        try:
            adapter = get_adapter(d.slug)
            adapter_ui = adapter.get("ui", {})
        except Exception:
            pass
        result.append({
            "id": d.id,
            "slug": d.slug,
            "name": d.name,
            "industry": d.industry,
            "label": adapter_ui.get("domain_label", d.name),
            "entity_label": adapter_ui.get("entity_label", "Entity"),
            "created_at": d.created_at.isoformat(),
        })
    return result


@router.get("/{domain_id}/demo")
def get_demo_interaction(domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    try:
        adapter = get_adapter(domain.slug)
        ui = adapter.get("ui", {})
        demo = ui.get("demo_interaction", {})
        scenarios = ui.get("sample_scenarios", [])
        return {
            "entity_name": demo.get("entity_name", ""),
            "text": demo.get("text", ""),
            "placeholder": ui.get("interaction_placeholder", "Paste customer interaction here..."),
            "sample_scenarios": scenarios,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
