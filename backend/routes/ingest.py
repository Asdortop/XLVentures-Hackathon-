from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import io
import re

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

MAX_CHARS = 8000  # cap extracted text sent to LLM


def _extract_pdf(data: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = []
            for page in pdf.pages[:20]:  # max 20 pages
                text = page.extract_text() or ""
                pages.append(text)
            return "\n\n".join(pages)
    except Exception as e1:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages[:20]:
                pages.append(page.extract_text() or "")
            return "\n\n".join(pages)
        except Exception as e2:
            raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e1} / {e2}")


def _extract_text(data: bytes, filename: str) -> str:
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return _extract_pdf(data)
    elif fname.endswith((".txt", ".md", ".markdown")):
        return data.decode("utf-8", errors="replace")
    elif fname.endswith((".csv",)):
        text = data.decode("utf-8", errors="replace")
        # Convert CSV rows to readable sentences
        lines = text.strip().split("\n")[:100]
        return "\n".join(lines)
    elif fname.endswith((".docx",)):
        try:
            import docx
            doc = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            raise HTTPException(status_code=422, detail="DOCX support requires: pip install python-docx")
    else:
        # Try UTF-8 plain text fallback
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            raise HTTPException(status_code=422, detail=f"Unsupported file type: {filename}")


def _clean(text: str) -> str:
    # Collapse whitespace, remove non-printable chars
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {3,}', ' ', text)
    return text.strip()[:MAX_CHARS]


@router.post("/document")
async def ingest_document(
    file: UploadFile = File(...),
    field: str = Form("sops_text"),  # which form field to populate
):
    """
    Extract text from uploaded document (PDF, TXT, MD, CSV, DOCX).
    Returns extracted text truncated to MAX_CHARS, ready to populate a form field.
    """
    allowed_fields = {"sops_text", "rules_text", "actions_text", "crm_sample"}
    if field not in allowed_fields:
        raise HTTPException(status_code=400, detail=f"field must be one of: {allowed_fields}")

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:  # 10 MB cap
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    filename = file.filename or "upload.txt"
    raw = _extract_text(data, filename)
    cleaned = _clean(raw)

    if not cleaned:
        raise HTTPException(status_code=422, detail="No readable text found in file")

    return {
        "field": field,
        "text": cleaned,
        "char_count": len(cleaned),
        "truncated": len(raw) > MAX_CHARS,
        "filename": filename,
    }
