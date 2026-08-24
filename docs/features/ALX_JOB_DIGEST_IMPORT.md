# ALX Ghana Job Digest Import

The ALX Ghana Community circulates a weekly PDF of local job openings. This
feature turns that PDF into candidate-visible jobs on the **Local Jobs** board.

## Where it lives

| Piece | File |
|---|---|
| PDF extraction + entry parsing | `backend/app/services/alx_job_importer.py` |
| Admin API (preview / commit) | `backend/app/api/v1/endpoints/job_imports.py` |
| Admin UI | `frontend/app/dashboard/admin/job-imports/page.tsx` |
| API client | `frontend/lib/api/admin.ts` |
| Schema | `migrations/017_add_alx_job_imports.sql` |

## The digest format

Every entry in the PDF follows one shape:

```
N. <Company> is hiring a <role>.
Apply here: <url>
Deadline: <Month DD, YYYY>
```

Two quirks matter:

1. **A rotated watermark** ("ALX Ghana Community") sits in the text layer and
   interleaves single characters into the body copy. It is set in
   `Poppins-Italic` at ~50-65pt while body copy is 12pt, so the importer drops
   every character at or above 20pt before extracting text.
2. **Apply links wrap across lines**, so the URL in the text layer is often
   truncated (`...officer-5741` instead of `...officer-57414`). The importer
   reads URLs from the PDF's link **annotations** instead, matching each
   annotation to an entry by vertical position on the page.

If ALX changes the layout, `parse_digest_text()` still works on any text that
keeps the numbered `N.` / `Apply here:` / `Deadline:` structure, and entries
that do not match `"<Company> is hiring a <role>"` fall back to using the whole
headline as the job title rather than being dropped.

## Import flow

1. An admin opens **Administration → Job imports** and uploads the PDF.
2. `POST /api/v1/admin/job-imports/alx/preview` parses it and returns every
   entry with a status. **Nothing is written.** Statuses are:
   - `new` — not on the board yet
   - `already_imported` — a previous digest already brought it in
   - `duplicate_of_scraped` — one of the scrapers already has this URL
3. The admin reviews and selects entries. Only `new`, unexpired entries are
   pre-selected.
4. `POST /api/v1/admin/job-imports/alx/commit` imports the selected entries.

## Enrichment

The digest carries no job description, which would leave the recommendation
engine with nothing but a title to embed. With "Fetch full descriptions"
enabled (the default), each apply URL is fetched through
`ExternalJobParser.parse_from_url()` — the same SSRF-validated path used for
user-submitted job URLs — to extract description, location, requirements, and
skills. Fetches run 5 at a time with a 45s per-URL timeout.

Enrichment is best-effort: a page that cannot be read still imports, using the
digest headline as its description. The response reports `enrichment_failed`.

## How imported jobs behave

- `source = 'alx'`, `origin_system = 'alx'`, `origin_job_id = sha256(normalized apply URL)[:32]`
- The unique index on `(origin_system, origin_job_id)` makes re-importing the
  same job an update rather than a duplicate, so overlapping weekly digests are
  safe to upload in full.
- `posted_date` is preserved on re-import, so a re-listed job does not jump to
  the top of the board every week.
- `location` defaults to `Ghana` when enrichment finds nothing better.
- `application_deadline` is stored; entries already past their deadline are
  skipped at commit, and expired jobs are filtered out of the Local Jobs board.
- Embeddings are queued per imported job so the AI recommendation engine picks
  them up. They qualify automatically via the engine's "recent, non-recruiter"
  visibility branch — no changes were needed there.

## Local Jobs scope

`GET /api/v1/jobs/?scope=local` returns Ghana-local jobs: `source IN
('recruiter', 'alx')`, excluding anything past its deadline. The dashboard
Local Jobs tab uses this instead of the previous `source=recruiter` filter.

The public `/jobs` page's "Direct recruiter roles" toggle is unchanged — it
still means ATS recruiter jobs specifically.

## Operating notes

- The endpoints require `is_admin`; there is no unauthenticated path.
- Uploads are capped at 10MB and must be a real PDF (`%PDF` header checked).
- A commit accepts at most 200 entries.
