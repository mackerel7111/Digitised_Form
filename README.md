# Digitised Form

A small web app for turning static PDF forms into reusable digital forms. Users can upload a PDF, review auto-suggested fields, publish a template, fill the digital form, save entries, and download the original PDF with values overlaid in the mapped positions.

## Stack

- Frontend: Vue 3, Vite, Bootstrap
- Backend: FastAPI, PyMuPDF
- Storage: SQLite for templates/submissions, local files for uploaded/exported PDFs

## How It Works

1. Upload a text-based PDF form.
2. The backend uses PyMuPDF to inspect PDF words, lines, boxes, and checkbox-like shapes.
3. A rule-based extractor suggests fields such as labelled text lines, checkbox groups, and multiline note areas.
4. The Template Builder shows the PDF preview with overlay boxes.
5. The user reviews the template: edit labels/types, add/remove fields, drag boxes, resize boxes, and publish.
6. The Fill screen generates a simple web form from the published template.
7. Saved entries are stored in SQLite.
8. PDF export uses the reviewed field coordinates to write submitted values onto the original PDF.

The reviewed template is the source of truth. The extractor only creates a draft.

## Run Locally

Install frontend dependencies:

```sh
npm install
```

Install backend dependencies:

```sh
python -m pip install -r backend/requirements.txt
```

Start the backend:

```sh
cd backend
python -m uvicorn main:app --reload
```

Start the frontend in a second terminal:

```sh
npm run dev
```

Open the Vite URL, usually:

```text
http://localhost:5173
```

## Project Structure

```text
backend/
  main.py            FastAPI routes
  database.py        SQLite persistence
  extract_fields.py  Rule-based field extraction
  inspect_pdf.py     Debug script for inspecting PDF structure
  pdf_service.py     PDF preview rendering and filled-PDF export
  storage/           Local uploads, exports, and SQLite DB (gitignored)

src/
  App.vue
  components/
    DashboardView.vue
    TemplateBuilderView.vue
    FillFormView.vue
    EntriesView.vue
```

## Adding A New Form Next Month

For forms similar to the samples:

1. Upload the PDF from the dashboard.
2. Open **Build Template**.
3. Review the suggested fields on the PDF preview.
4. Remove false positives.
5. Add any missed fields manually.
6. Adjust labels, field types, positions, widths, and heights.
7. Use **Save Draft** while reviewing.
8. Click **Publish Template** when the mapping is correct.
9. Fill a test entry and download the filled PDF to verify placement.

For a new PDF layout that the extractor does not handle well:

1. Run the inspection tool:

```sh
cd backend
python inspect_pdf.py path/to/new-form.pdf
```

2. Check whether PyMuPDF can see the relevant text, lines, boxes, or drawings.
3. Add or adjust a rule in `backend/extract_fields.py`.
4. Re-run:

```sh
python extract_fields.py path/to/new-form.pdf
```

5. Confirm the output fields look reasonable, then test through the web app.

Typical places to extend:

- `extract_text_line_fields()` for labelled blank lines
- `extract_checkbox_fields()` for checkbox/radio-like groups
- `extract_multiline_fields()` for notes/comments boxes
- a new helper if the form introduces tables or another repeated pattern

## Data Model

Field positions are stored as normalized page-relative coordinates:

```json
{
  "id": "site_name",
  "label": "Site Name",
  "type": "text",
  "page": 1,
  "rect": {
    "x": 0.164,
    "y": 0.1659,
    "w": 0.4286,
    "h": 0.019
  }
}
```

This keeps templates independent of preview zoom or screen size. PyMuPDF export converts the normalized rectangle back to PDF page coordinates.

## Notes

- Processing is local; no VLM/OCR service is required for the supplied text-based PDFs.
- Uploaded PDFs and generated exports are stored under `backend/storage/`, which is ignored by Git.
- Date fields can optionally render as date boxes for PDFs that use separate character cells.
