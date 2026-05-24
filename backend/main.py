from pathlib import Path
from uuid import uuid4

import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from extract_fields import extract_fields


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"

app = FastAPI(title="Digitised Form API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_storage():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/extract-fields")
async def extract_fields_from_upload(file: UploadFile = File(...)):
    ensure_storage()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    upload_id = uuid4().hex
    pdf_path = UPLOADS_DIR / f"{upload_id}.pdf"

    contents = await file.read()
    pdf_path.write_bytes(contents)

    try:
        result = extract_fields(pdf_path)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not extract fields: {error}") from error

    return {
        "id": upload_id,
        "filename": file.filename,
        "fields": result["fields"],
    }
    
@app.get("/api/uploads/{upload_id}/page/{page_number}.png")
def render_uploaded_pdf_page(upload_id: str, page_number: int):
    pdf_path = UPLOADS_DIR / f"{upload_id}.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded PDF not found")

    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be 1 or greater")

    try:
        with fitz.open(pdf_path) as document:
            if page_number > document.page_count:
                raise HTTPException(status_code=404, detail="Page not found")

            page = document[page_number - 1]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            png_bytes = pixmap.tobytes("png")

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not render PDF page: {error}") from error

    return Response(content=png_bytes, media_type="image/png")