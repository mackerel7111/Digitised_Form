from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from extract_fields import extract_fields
from database import (
    create_form,
    create_submission,
    get_form,
    init_db,
    list_forms,
    list_submissions,
    update_form,
)
from pdf_service import export_filled_pdf_file, render_page_png

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
EXPORTS_DIR = STORAGE_DIR / "exports"

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

@app.on_event("startup")
def startup():
    init_db()

def ensure_storage():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


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

    form = create_form(upload_id, file.filename, result["fields"])

    return {
        **form,
        "extractionStatus": "complete",
    }
    
@app.get("/api/uploads/{upload_id}/page/{page_number}.png")
def render_uploaded_pdf_page(upload_id: str, page_number: int):
    pdf_path = UPLOADS_DIR / f"{upload_id}.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded PDF not found")

    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be 1 or greater")

    try:
        png_bytes = render_page_png(pdf_path, page_number)
        if png_bytes is None:
            raise HTTPException(status_code=404, detail="Page not found")
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not render PDF page: {error}") from error

    return Response(content=png_bytes, media_type="image/png")
    
@app.get("/api/forms")
def get_forms():
    forms = list_forms()

    return [
        {
            **form,
            "extractionStatus": "complete",
        }
        for form in forms
    ]
    
@app.put("/api/forms/{form_id}")
async def save_form_template(form_id: str, payload: dict):
    existing_form = get_form(form_id)

    if existing_form is None:
        raise HTTPException(status_code=404, detail="Form not found")

    fields = payload.get("fields")
    status = payload.get("status", existing_form["status"])

    if not isinstance(fields, list):
        raise HTTPException(status_code=400, detail="fields must be a list")

    updated_form = update_form(form_id, fields, status)

    return {
        **updated_form,
        "extractionStatus": "complete",
    }    

@app.post("/api/forms/{form_id}/submissions")
async def save_form_submission(form_id: str, payload: dict):
    existing_form = get_form(form_id)

    if existing_form is None:
        raise HTTPException(status_code=404, detail="Form not found")

    values = payload.get("values")

    if not isinstance(values, dict):
        raise HTTPException(status_code=400, detail="values must be an object")

    return create_submission(form_id, values)

@app.get("/api/forms/{form_id}/submissions")
def get_form_submissions(form_id: str):
    existing_form = get_form(form_id)

    if existing_form is None:
        raise HTTPException(status_code=404, detail="Form not found")

    return list_submissions(form_id)    

@app.post("/api/uploads/{upload_id}/export")
async def export_filled_pdf(upload_id: str, payload: dict):
    ensure_storage()

    pdf_path = UPLOADS_DIR / f"{upload_id}.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded PDF not found")

    fields = payload.get("fields", [])
    values = payload.get("values", {})

    if not isinstance(fields, list) or not isinstance(values, dict):
        raise HTTPException(status_code=400, detail="Invalid export payload")

    export_id = uuid4().hex
    output_path = EXPORTS_DIR / f"{export_id}.pdf"

    try:
        export_filled_pdf_file(pdf_path, output_path, fields, values)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not export PDF: {error}") from error

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"filled-{upload_id}.pdf",
    )
