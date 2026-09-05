# Editable tailored CVs

## Candidate flow

1. A registered, active user uploads a CV and waits for parsing to complete.
2. From **Dashboard → Job Match**, the user selects **Tailor CV** on a role.
3. The API creates a private copy for that role. It never changes the uploaded source CV.
4. The browser editor autosaves structured changes and shows a live preview.
5. The user can restore an earlier revision, reset to the initial AI draft, download DOCX, or use the browser print dialog to save PDF.

Normal public job browsing and external application links remain public. CV generation, reading, editing, revision history and download all require `get_current_user`; every database lookup is also filtered by that user's ID.

## Safety model

- Source CV and job text are sanitized and bounded before entering the model prompt.
- The job description is explicitly treated as untrusted reference text.
- AI may rewrite the summary and supporting descriptions, and reorder source skills. Rewritten prose cannot be mechanically proven true, so every draft carries a visible candidate-review warning.
- Identity, employers, role names, dates, education and project identity are copied from the source CV rather than trusted from model output.
- Skills not found in the source CV are discarded. New numbers in AI-written experience text raise a visible review warning.
- The generated document is stored as private JSONB and exported in memory. No public storage URL is created.
- Updates use an expected revision and return HTTP 409 when another session has saved first.
- Generation is limited to five requests per registered user per hour when HTTP rate limiting is enabled.

The user can deliberately edit every field in the generated copy. These edits are not written back to the uploaded CV because the candidate, not the AI, is the authority for corrections and additions.

## API

- `POST /api/v1/cv-generations` — create or reopen the latest draft for a job and unchanged source CV; pass `regenerate: true` to explicitly spend another AI generation.
- `GET /api/v1/cv-generations` — list the signed-in user's drafts.
- `GET /api/v1/cv-generations/{id}` — load one owned draft.
- `PATCH /api/v1/cv-generations/{id}` — autosave structured content with `expected_revision`.
- `GET /api/v1/cv-generations/{id}/revisions` — list revision metadata.
- `POST /api/v1/cv-generations/{id}/restore/{revision}` — copy an old revision into a new current revision.
- `POST /api/v1/cv-generations/{id}/reset` — copy the initial AI draft into a new current revision.
- `GET /api/v1/cv-generations/{id}/download.docx` — authenticated in-memory DOCX export.

## Deployment

Apply `migrations/019_add_editable_cv_generations.sql` before deploying the backend. At least one AI provider must be configured; the router prefers Gemini for this task and can use another configured provider as fallback. A missing or invalid provider response fails visibly and does not create a fake tailored draft.

Generation currently runs in the request so the candidate immediately receives a complete editor document. If provider latency starts exceeding the API timeout, move only the generation step to Celery and retain these ownership and revision rules.
