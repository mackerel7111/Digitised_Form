# DigitiseForm

DigitiseForm is a web application for turning static PDF forms into reusable digital forms. It lets a user upload a PDF, prepare a fillable template, collect form entries, and download the original PDF with submitted values overlaid in the correct positions.

This project is being built for the Form Digitisation Pipeline internship trial task.

## Core Idea

The system separates a form into two things:

- the original PDF, which remains the visual source of truth
- a template JSON file, which stores the digital fields and their positions on the PDF

The digital form does not need to visually match the PDF. It only needs to map each field back to the right page and coordinate box in the original document.

## Planned Stack

Frontend:

- Vue 3
- Vite
- TypeScript
- Vue Router
- PDF.js for PDF preview
- interact.js or a Vue drag/resize package for field boxes

Backend:

- FastAPI
- SQLite
- PyMuPDF for PDF inspection, rendering, and overlay export
- Pydantic for validation
- pytest for backend tests

Optional extraction backend:

- MinerU2.5 or another document parsing model to generate a draft template
- The app should still work without the model through manual template editing

## User Flow

### 1. Template Builder

An admin or teammate uploads a PDF form. The app shows the PDF preview and creates a draft list of fields.

The draft can come from:

- a VLM/OCR parser such as MinerU2.5
- a simpler PDF/OCR/OpenCV parser
- manual field creation by the user

The user then reviews the draft by renaming fields, changing field types, moving field boxes, resizing boxes, deleting incorrect fields, and adding missing fields.

When the template looks correct, the user publishes it.

### 2. Form Filler

A regular user chooses a published form from the form list. They see a clean digital form with normal inputs such as text fields, dates, numbers, checkboxes, and multiline text.

After filling it in, they save the entry.

### 3. PDF Export

The app loads the original PDF and the saved template coordinates. It writes the submitted values into the mapped positions and returns a filled PDF download.

## Coordinate Mapping

Field positions are stored as normalized page-relative coordinates:

```json
{
  "id": "full_name",
  "label": "Full Name",
  "type": "text",
  "page": 1,
  "rect": {
    "x": 0.18,
    "y": 0.31,
    "w": 0.42,
    "h": 0.025
  }
}
```

The browser preview uses top-left coordinates. PDF writing usually uses bottom-left coordinates. During export, normalized coordinates are converted into PDF points:

```text
pdf_x = rect.x * page_width
pdf_y = page_height - ((rect.y + rect.h) * page_height)
```

This makes the saved template independent of zoom level or screen size.

## How To Add Support For A New Form

1. Upload the new PDF in the Template Builder.
2. Generate a draft template using the parser, or add fields manually.
3. Review every field against the PDF preview.
4. Adjust field names, types, and overlay boxes.
5. Publish the template.
6. Test by filling a sample entry and downloading the filled PDF.

The final source of truth is the reviewed template JSON, not the parser output. This keeps the app reliable even when OCR or VLM extraction is imperfect.

## Development

Install frontend dependencies:

```sh
npm install
```

Run the Vue development server:

```sh
npm run dev
```

Build the frontend:

```sh
npm run build
```

Lint the frontend:

```sh
npm run lint
```

Backend setup commands will be added once the FastAPI service is created.

## Testing Plan

Important tests:

- template schema validation
- coordinate conversion from browser coordinates to PDF coordinates
- PDF overlay generation
- submission save/load
- parser fallback behavior when no VLM is configured

## Architecture Decision Summary

1. Use a hybrid approach instead of relying fully on AI extraction.
2. Store reviewed template coordinates as the source of truth.
3. Keep the VLM parser optional so the app remains cloneable and usable without GPU setup.
