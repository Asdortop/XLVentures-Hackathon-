from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from core.adapter_builder import generate_adapter, deploy_adapter
from core.adapter import get_adapter
import json

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


def _sse(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


@router.post("/configure/stream")
async def configure_stream(req: OnboardingInput):
    """SSE streaming blueprint generation — emits live progress steps."""
    import re

    def generate():
        inputs = req.dict()
        slug = inputs.get("company_name", "unknown").lower().replace(" ", "_").replace("-", "_")
        slug = re.sub(r"[^a-z0-9_]", "", slug)[:30]

        STEPS = [
            ("parse",    "Parsing your business knowledge & SOPs..."),
            ("generate", "Calling LLM to generate YAML configuration..."),
            ("validate", "Validating schema — intents, actions, rules..."),
            ("preview",  "Building Blueprint Canvas preview..."),
            ("ready",    "Blueprint ready!"),
        ]
        step_idx = 0

        try:
            yield _sse("step", {"step": STEPS[0][0], "label": STEPS[0][1], "step_num": 1, "total": len(STEPS)})
            step_idx = 1

            from core.adapter_builder import (
                _build_generation_prompt, _parse_llm_output, _validate_config, _build_preview, MAX_RETRIES,
                SYSTEM_PROMPT,
            )
            from llm_provider import llm

            previous_error = None
            result = None

            for attempt in range(MAX_RETRIES):
                yield _sse("step", {"step": STEPS[1][0], "label": f"LLM generation — attempt {attempt + 1}/{MAX_RETRIES}...", "step_num": 2, "total": len(STEPS)})

                prompt = _build_generation_prompt(inputs, previous_error, attempt)
                try:
                    raw_output = llm.generate(prompt, SYSTEM_PROMPT)
                    files = _parse_llm_output(raw_output)

                    if not files:
                        previous_error = "Could not parse YAML files. Retrying..."
                        yield _sse("retry", {"attempt": attempt + 1, "error": previous_error})
                        continue

                    yield _sse("step", {"step": STEPS[2][0], "label": STEPS[2][1], "step_num": 3, "total": len(STEPS)})
                    errors = _validate_config(files)

                    if errors:
                        previous_error = "Fix these errors:\n" + "\n".join(f"  - {e}" for e in errors)
                        yield _sse("retry", {"attempt": attempt + 1, "error": f"{len(errors)} validation error(s) — auto-fixing..."})
                        continue

                    yield _sse("step", {"step": STEPS[3][0], "label": STEPS[3][1], "step_num": 4, "total": len(STEPS)})
                    preview = _build_preview(files)

                    yield _sse("step", {"step": STEPS[4][0], "label": STEPS[4][1], "step_num": 5, "total": len(STEPS)})
                    yield _sse("complete", {
                        "slug": slug,
                        "preview": preview,
                        "raw_files": files,
                        "attempts": attempt + 1,
                    })
                    return

                except Exception as e:
                    previous_error = f"LLM error: {str(e)}"
                    yield _sse("retry", {"attempt": attempt + 1, "error": str(e)[:120]})

            yield _sse("error", {"message": f"Failed after {MAX_RETRIES} attempts. {previous_error}"})

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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
