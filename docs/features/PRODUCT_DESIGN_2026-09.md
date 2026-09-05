# Candidate experience redesign

## Direction

The owner requested a more established professional platform, referencing LinkedIn and BambooHR, and explicitly requested scroll-craft for the landing page. The new public experience uses a common white header, forest-green actions, soft neutral grounds, consistent sans-serif typography, compact borders, and fewer promotional blocks.

Reference review: [LinkedIn jobs](https://www.linkedin.com/jobs/) emphasizes role categories and clear entry points; [BambooHR](https://www.bamboohr.com/) connects human outcomes to product explanations. This implementation adapts those principles without copying either identity.

## Scope and behavior

- Landing page: actual search form, category links into filtered results, layered existing photography, a clearly labelled interactive matching example, editable-CV explanation, FAQ and direct closing action. Authenticated visitors continue to the dashboard. Public content renders while session detection resolves.
- The matching example computes skill overlap from three illustrative roles. It is not production ranking, a live vacancy list, or a promise of a particular score. Its search link carries the leading role into real search.
- Login and signup: shared public navigation and a quieter supporting panel. Existing phone OTP, email login, remember-session, handoff prefill and verification behavior remain in place. Forms use POST as the non-JavaScript fallback to avoid putting personal fields in query strings.
- Public jobs: search and filters appear first; desktop has a result list and selected-job description. Phones use a single list with links to the full job. Search accepts `q` and `location` URL parameters, plus recruiter/remote/date filters and pagination. Obsolete requests cannot overwrite a newer result set.
- Signup prompts are now intent-triggered by saving a role instead of appearing after five seconds of browsing. The dialog uses layout centering independently from animation, bounds its height, supports Escape and focus cycling, locks background scrolling and restores focus.
- Public detail pages, the dashboard shell and shared job cards receive consistent restrained styling. Existing private dashboard features and source CV behavior are retained.
- Public applications still leave to the employer/source without registration. Backend ownership requirements for personal data and CVs are unchanged.

## Implementation

- Shared public navigation: `frontend/components/layout/PublicHeader.tsx`.
- Scoped design system: `frontend/app/product.css`, imported once in the root layout.
- Brief and scroll design record: `scrollcraft/builds/veloxahire/BRIEF.md`.
- Existing Framer Motion handles the landing choreography and reduced motion. The unmodified scroll-craft engine is retained in the build folder as a reference; it is not loaded into the React app because its global lifecycle has no unmount contract.
- No generated assets, new runtime packages, production migrations or deployment changes were required for this redesign.

## Verification

Desktop job results and the selected description now have separate scroll areas within a viewport-sized workspace. Scrolling the list does not move the description or propagate to the page at the list boundary. The results region supports keyboard focus. At 760px and below, results retain normal document scrolling.

- Frontend TypeScript check and isolated production build passed; 24 routes built.
- Browser checks cover landing scroll sections, skill selection and role-link propagation, mobile navigation, login/signup fields, email-login switching, job selection, remote filters, pagination, and reduced motion at 1440, 390 and 360 pixels.
- Additional checks cover phone verification form progression with a mocked OTP response, failed search, retry, empty results, dialog center alignment, Escape dismissal and restored focus.
- Job responses and OTP delivery are mocked only in the browser verification scripts. This proves the UI wiring, not live SMS delivery, successful authentication or production job inventory.
- Accessibility inspection caught pale skill and date labels; these were darkened. Final results and screenshot evidence are recorded in the scroll-craft verification note.
- Physical-phone behavior, production deployment and authenticated data workflows were not verified by these browser checks.

The production preview is served from an isolated copy to avoid conflicting with the user's existing development server and its `.next` cache.

## Signed-in workspace follow-up

- Added a dedicated, scoped `frontend/app/dashboard.css` rather than changing the public theme or CV editor.
- Rebuilt the overview around actual recommendation previews, application totals, profile completion, CV-tailoring entry points and alert preferences. Failed overview requests display a retry state, not invented zero counts. Phone-registered candidates are greeted using their name metadata.
- Navigation labels are now Overview, Job matches, Explore jobs, Applications, Profile and Settings. URLs and admin authorization are unchanged.
- Matches, applications, profile and settings use consistent typography, borders, spacing and forest-green actions. Applications use readable single-column rows and underlined state tabs. Profile forms and alert handlers remain intact.
- Added accessible names to email/WhatsApp schedule controls, active navigation and application-tab state. Reduced-motion styling is scoped to the workspace.
- Verification uses isolated browser-only session and API fixtures. It covers response rendering, desktop/phone layout and local interactions, not real authentication, database writes, CV generation or message delivery. No backend authorization or production settings changed.
- Final checks: TypeScript and isolated production build passed (24 routes). All five workspace pages passed at 1440, 390 and 360px with no horizontal overflow, runtime errors or detected Axe WCAG A/AA violations. Mobile navigation, application tabs, profile edit/cancel and overview error/retry passed. Local screenshots and the fixture runner are under `/tmp/veloxahire-design-check/`; temporary artifacts are not release tests.
