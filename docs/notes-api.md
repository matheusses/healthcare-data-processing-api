# Notes API

Patient notes are short clinical notes (e.g. SOAP format) written during admission, check-ins, or visits. The API supports uploading notes via JSON body or file, listing by patient, and deleting.

## Endpoints

- **POST `/patients/{patient_id}/notes/`** — Upload a note with JSON body: `{ "recorded_at": "<ISO datetime>", "content": "<text>" }`. Patient must exist (404 otherwise).
- **POST `/patients/{patient_id}/notes/upload`** — Upload a note from a file (multipart: `file`, optional `recorded_at`). Allowed file types: `.txt`, `.pdf`, or handwritten images (`.jpg`, `.png`). Text is extracted automatically (PDF via PyPDF, images via OCR with RapidOCR). If `recorded_at` is omitted, the server sets it to the current time. Content is stored in object storage (MinIO/S3) and referenced by `storage_key`. Returns 422 for disallowed file types or when no text can be extracted.
- **GET `/patients/{patient_id}/notes/`** — List notes for a patient (paginated: `limit`, `offset`). Returns `{ "items": [...], "total": N }`.
- **GET `/patients/{patient_id}/notes/{note_id}`** — Get a single note. Returns 404 if note not found or not belonging to patient.
- **DELETE `/patients/{patient_id}/notes/{note_id}`** — Delete a note and its object-storage file (if any) and vector chunks. Returns 404 if not found.

## SOAP context

Notes may follow SOAP structure (Subjective, Objective, Assessment, Plan). The API does not parse or validate SOAP; it stores plain text. Future LLM summary endpoints can consume note content (and vector chunks) to produce SOAP-aligned or discharge summaries (see `app/shared/schemas/summary.py`).

## File upload details

- **Allowed types:** `.txt` (plain text), `.pdf` (text extracted with LangChain PyPDFLoader), `.jpg` / `.jpeg` / `.png` (handwritten or printed text extracted via OCR with RapidOCR). The vector DB (pgvector) does not "detect" handwriting itself; images are converted to text by OCR first, then that text is chunked and embedded.
- **recorded_at:** Optional. Send an ISO 8601 datetime (e.g. `2023-10-26T12:00:00Z`) to set when the note was recorded; omit to use the server's current time.
- **Size limit:** Uploads are limited to 10 MB to reduce DoS risk.
- **OCR quality:** Handwritten image quality affects OCR accuracy; clear, high-contrast images give better results.

## Configuration

- **Document storage:** `DOCUMENT_STORAGE_ENDPOINT`, `DOCUMENT_STORAGE_BUCKET`, `DOCUMENT_STORAGE_ACCESS_KEY`, `DOCUMENT_STORAGE_SECRET_KEY` (see `.env.example`).
- **Vector/embeddings (optional):** Set `OPENAI_API_KEY` and optionally `VECTOR_EMBEDDING_MODEL`, `VECTOR_EMBEDDING_DIMENSIONS` to run the embedding pipeline on note create (chunking + embeddings written to `note_chunks`).
- **Document loaders:** PDF and image extraction use `langchain-community`, `pypdf`, and `rapidocr-onnxruntime` (no extra system dependencies for OCR).

## Security

- Notes contain PHI; do not log request/response bodies that include clinical text.
- Validate and sanitize all inputs; access control and auth are out of scope for task 002 but should be added for production.
