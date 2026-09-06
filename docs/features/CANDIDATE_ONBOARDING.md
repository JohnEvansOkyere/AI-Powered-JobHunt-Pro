# Candidate onboarding: profile and CV

Owner decision, 2026-09-06: both profile details and an uploaded CV are required for onboarding and recommendation generation.

## Current behavior

1. After account verification, overview and Job matches check profile essentials and the active CV. Incomplete accounts open `/profile/setup`; service failures offer retry. Public browsing/applying remains accessible.
2. Save target role, seniority and work preference, then skills. Job market is optional. Each profile step persists independently.
3. Upload a PDF or DOCX using the existing owner-scoped CV endpoint (10 MB limit). An active CV with completed parsing and nonempty structured content is required to finish. Failed uploads/parsing allow replacement, pending processing is checked every three seconds, and failed status requests have an explicit retry action.
4. Completion rechecks the CV and calls the existing rate-limited regeneration endpoint. A request failure retains saved data. Queued generation does not guarantee immediate results or suitable vacancies.

## Matching and tailoring contracts

- Matching now uses the profile plus the **active successfully parsed CV**, consistently in the embedding lookup and generation engine. The old code read nonexistent `CV.summary`/`CV.extracted_text` attributes instead of this application's `CV.parsed_content`, silently omitting CV evidence.
- The embedding includes profile intent and bounded, sanitized CV summary, skills, experience and education. Explicit personal/contact fields and raw document text are not included. Three thousand characters are reserved for profile input and the remaining budget for CV evidence, so long profile text cannot exclude the CV entirely.
- CV technical skills also feed skill-overlap scoring and the existing reranker alongside profile skills. Switching the active CV or changing its structured content changes the embedding input hash; refresh runs update the embedding before matching.
- Manual regeneration rejects missing profile essentials or missing/failed/pending/inactive/empty CVs before consuming the rate-limit allowance. Scheduled generation also checks readiness before provider calls. Existing recommendation history is retained.
- Tailoring already requires an owned, parsed source CV. It uses that CV's structured facts and the target job to create a private editable draft. Profile preferences guide matching; they are not silently added to the CV as employment facts.
- **Exact uploaded formatting is not preserved by the current tailored exporter.** It renders the edited content in the system's DOCX/preview layout. The uploaded original remains unchanged. Exact template preservation has not been implemented by this change.

## Verification and deployment boundary

Local validation on 2026-09-06: 76 focused matching/tailoring tests, frontend type-check, whitespace checks and the updated browser regression passed. Browser fixtures include a 360px required-CV screen with no horizontal overflow; screenshot `/tmp/onboarding-cv-360.png`.

- `backend/tests/test_matching_cv_requirement.py` checks real model field extraction, combined profile/CV input, budget limits, excluded contact fields, active/owned CV selection, readiness, cache invalidation, CV skill scoring and generation rejection without a CV. No live providers/database/storage.
- `frontend/scripts/verify-onboarding.cjs` checks upload request wiring, invalid file types, failed/pending/completed parsing, status polling, CV removal, failed CV reads/retry, profile resume, matching outcomes, browser access rules and phone layout using synthetic sessions/API responses. See the product design document for runner configuration.
- Deploy both frontend and backend. No schema migration is required. A real authenticated upload, parse, matching run and tailored export are still required to verify production storage, parser/model providers and job inventory.
