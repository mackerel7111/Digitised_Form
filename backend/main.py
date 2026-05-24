from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

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