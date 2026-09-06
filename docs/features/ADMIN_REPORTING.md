# Admin registrations, profiles and analytics

The administrator dashboard is organized into linked report pages:

| Page | Contents |
| --- | --- |
| `/dashboard/admin` | Traffic summary and operational totals |
| `/dashboard/admin/registrations` | Account registrations, daily signup counts, complete/partial/not-started profile totals and links to those users |
| `/dashboard/admin/users` | Searchable, paginated accounts with registration date, last login, verification flags, profile score, missing fields and existing account controls |
| `/dashboard/admin/traffic` | Traffic trend, tracked signup activity, top paths, clicks and job pages |
| `/dashboard/admin/acquisition` | Sources, campaigns, visitors, job views, apply clicks and tracked signup sessions |
| `/dashboard/admin/activity` | Recent sessions and events |

The Signups & profiles report supports rolling 7/30/90-day periods. Clicking a profile card opens the user list with the same registration period and profile state. Users also supports all-time registrations, account status, search by name/email/phone and 25 accounts per page. Filter changes reset pagination; URL parameters preserve report filters through reloads and browser navigation.

## Definitions

- **Registrations** count existing `public.users` records by `created_at`. They include admins and suspended accounts, exclude deleted accounts, and do not require analytics events. They are platform registrations, not an independent census of Supabase Auth users.
- **Profile status** measures the current profile for the selected registration cohort. It is not historical completion as of the end date, and no completion timestamp is inferred from `updated_at`.
- **Complete** is 100%; **partial** is 1–99%; **not started** is 0%, including missing profile rows and empty profiles. Fields without a score may exist on a not-started profile.
- Scores match `frontend/lib/profile-utils.ts`: job title, seniority and work preference each 10%; technical skills 20%; soft skills 10%; at least one experience with role/company/duration 20%; writing tone 10%; AI speed/quality preference 10%. CV upload/parsing and matching readiness are separate.
- Daily registrations use UTC dates; rolling periods include partial first and last days. Zero-registration dates are included.
- Behavioral signup totals are browser events or attributed sessions, as labeled. Tracking can be missing or duplicated. Signup starts and completions are not treated as a matched funnel or an account conversion rate.
- Top reports retain their bounded scope: 12 paths, 10 click targets, 10 job paths, 20 acquisition sources, latest 30 sessions and events. These limits are labeled. User pagination is server-side and has an exact filtered count.
- Anonymous sessions cannot establish which identifiable people have not registered. Use account profile filters for follow-up on registered users.

## API and security

`GET /api/v1/admin/registrations?days=30` returns account and cohort totals plus daily registrations. `GET /api/v1/admin/users` accepts `search`, `status`, `profile`, `days` (0 means all time), `page` and `page_size` (1–100, default 25). Existing global total/active/suspended counts remain all-time; `filtered_total` describes the current list.

Both APIs enforce the existing `require_admin` dependency. Candidate authentication and account-status checks still execute before administrator access. Reporting selects profile completion flags and exposes no CV files, signed storage URLs, full profile text or AI prompts. It performs no writes, provider calls or storage operations. Queries are parameterized and filters/page sizes are bounded. There is no new rate limiter; these endpoints retain existing authenticated admin access and operational rate behavior.

No schema migration is required. This uses the existing user/profile schema and analytics migrations. Deploy frontend and backend together because the user list now expects completion and pagination fields. Keep SQL completion checks and the candidate profile utility aligned if scoring rules change.

## Verification

`backend/tests/test_admin_reporting.py` covers unauthenticated/non-admin denial, validated bounds, account-based counts, missing/empty/partial/complete profiles, invalid experience, date cohorts, search/status filters and pagination. PostgreSQL tests require `ADMIN_REPORTING_TEST_DATABASE_URL` pointing to a dedicated empty database; fixtures create tables transactionally and roll back. They never use the configured application database.

`frontend/scripts/verify-admin-reports.cjs` checks the reports with synthetic browser sessions and API fixtures. Configure a separate preview with public Supabase/Auth URLs `https://admin-report-test.supabase.co`, public keys `fixture-public-key`, and API URL `http://127.0.0.1:8133`. Set `PLAYWRIGHT_PATH` if Playwright is outside node_modules. This is browser acceptance evidence, separate from real database tests and hosted authentication.

Production deployment, actual hosted signup totals and a real administrator session remain to be verified after release.

Local verification on 2026-09-06: 15 focused backend tests passed against temporary PostgreSQL 15, frontend type-check and production build passed, and synthetic browser acceptance passed at 1440px and 390px with no page errors or horizontal overflow. Browser checks exercised report navigation, profile-card drill-down, filters, pagination, missing fields, date selection, empty/error states, non-admin redirects and anonymous login redirects. No live accounts were changed.
