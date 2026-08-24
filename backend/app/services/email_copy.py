"""Dialect phrase packs and HTML/text rendering for job digest emails.

Copy is hand-written per locale rather than LLM-generated: a digest goes to a
candidate's inbox unreviewed, so the phrasing must be predictable, on-brand and
free of the drift an LLM introduces. Variants rotate deterministically per user
per day so a subscriber does not read the identical sentence every morning.

Locales:
    ``en``   — professional English in a Ghanaian register (default / fallback).
    ``twi``  — Twi/Akan framing with English job details.

The English pack is written the way a Ghanaian colleague would write it: warm,
courteous, direct. Deliberately *not* pidgin — West African pidgins differ by
country, and copy that reads as Nigerian to a Ghanaian reader lands worse than
plain English would.

Job titles, company names, locations and AI match reasons are *always* left in
their original language and HTML-escaped: they are scraped, untrusted content.
"""

from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

SUPPORTED_LOCALES = ("en", "twi")
DEFAULT_LOCALE = "en"

# Brand palette — kept literal because email clients do not support CSS vars.
BRAND = "#4f46e5"
BRAND_DARK = "#3730a3"
INK = "#111827"
MUTED = "#6b7280"
LINE = "#e5e7eb"
CANVAS = "#f4f5f7"
CARD = "#ffffff"


@dataclass(frozen=True)
class LocalePack:
    """Every user-visible string for one dialect.

    Tuple-valued fields are rotation variants; single strings are fixed. All
    ``{placeholders}`` are filled with values we control (names are escaped by
    the renderer before substitution into HTML).
    """

    code: str
    label: str
    subjects: Tuple[str, ...]
    preheaders: Tuple[str, ...]
    greetings: Tuple[str, ...]
    intros: Tuple[str, ...]
    jobs_heading: str
    match_label: str
    why_label: str
    view_job_label: str
    cta_button: str
    signoffs: Tuple[str, ...]
    footer_reason: str
    unsubscribe_label: str
    manage_label: str
    single_job_note: str


LOCALE_PACKS: Dict[str, LocalePack] = {
    "en": LocalePack(
        code="en",
        label="English",
        subjects=(
            "{first_name}, {count} roles that match your profile",
            "{count} new openings for you, {first_name}",
            "Your job matches for {day_name}, {first_name}",
        ),
        preheaders=(
            "Selected from today's postings and ranked by how closely they fit you.",
            "We went through today's listings so you don't have to.",
            "The closest matches to your profile at the moment.",
        ),
        greetings=(
            "Hello {first_name},",
            "Good morning {first_name},",
            "Hello {first_name}, we hope you are doing well.",
        ),
        intros=(
            "We went through today's postings and {count} of them match your profile.",
            "Here are {count} roles that line up with your experience and skills.",
            "{count} new openings came in today that suit what you are looking for.",
        ),
        jobs_heading="Your matches",
        match_label="match",
        why_label="Why this fits",
        view_job_label="View role",
        cta_button="See all my matches",
        signoffs=(
            "Do well to apply early — some of these close quickly.",
            "All the best with your applications.",
            "Wishing you the very best this week.",
        ),
        footer_reason=(
            "You are receiving this because you signed up for job match emails "
            "on VeloxaHire."
        ),
        unsubscribe_label="Unsubscribe",
        manage_label="Manage email settings",
        single_job_note=(
            "Only one strong match today — we would rather send you one good role "
            "than five weak ones."
        ),
    ),
    "twi": LocalePack(
        code="twi",
        label="Twi",
        subjects=(
            "{first_name}, adwuma {count} a ɛfata wo",
            "Maakye {first_name} — adwuma {count} aba",
            "Adwuma {count} a ɛne wo hyia, {first_name}",
        ),
        preheaders=(
            "Yɛhwɛɛ adwuma a ɛbaa nnɛ na yɛpaw deɛ ɛfata wo.",
            "Ɛnyɛ adwuma nyinaa — deɛ ɛne wo nimdeɛ hyia.",
            "Adwuma foforɔ a ɛfa wo adwuma ho.",
        ),
        greetings=(
            "Maakye {first_name}!",
            "Agoo {first_name}, wo ho te sɛn?",
            "{first_name}, akwaaba.",
        ),
        intros=(
            "Yɛhwehwɛɛ adwuma a ɛbaa nnɛ mu, na {count} wɔ hɔ a ɛne wo nimdeɛ hyia.",
            "Yɛanya adwuma {count} a ɛfata dwuma a wotumi yɛ.",
            "Adwuma {count} aba a yɛsusu sɛ ɛbɛyɛ wo yie.",
        ),
        jobs_heading="Adwuma a ɛfata wo",
        match_label="ɛhyia",
        why_label="Deɛ enti a ɛfata wo",
        view_job_label="Hwɛ adwuma no",
        cta_button="Hwɛ adwuma no nyinaa",
        signoffs=(
            "Bɔ mmɔden na fa wo nsa hyɛ mu. Nyame nhyira wo.",
            "Sɔ hwɛ — wobɛtumi.",
            "Yɛhyɛ wo nkuran. Medaase.",
        ),
        footer_reason=(
            "Worenya saa email yi ɛfiri sɛ wokyerɛw wo din maa adwuma email wɔ "
            "VeloxaHire so."
        ),
        unsubscribe_label="Gyae email yi",
        manage_label="Sesa wo email nhyehyɛeɛ",
        single_job_note="Adwuma baako pɛ na ɛfata wo nnɛ, nanso ɛyɛ papa.",
    ),
}


def get_pack(locale: Optional[str]) -> LocalePack:
    """Return the phrase pack for ``locale``, falling back to English."""
    key = (locale or "").strip().lower()
    return LOCALE_PACKS.get(key, LOCALE_PACKS[DEFAULT_LOCALE])


def variant_index(seed: str, on_date: date, count: int) -> int:
    """Pick a rotation variant deterministically.

    Mixing the user id into the day ordinal means two users on the same day
    usually see different phrasing, and one user sees different phrasing on
    consecutive days — without storing any rotation state.

    SHA-256 rather than :func:`hash` because the latter is salted per process,
    which would make a user's variant jump around between Celery workers.
    """
    if count <= 0:
        return 0
    digest = int(
        hashlib.sha256((seed or "anon").encode("utf-8")).hexdigest()[:12], 16
    )
    return (on_date.toordinal() + digest) % count


def _esc(value: Optional[str], limit: int = 200) -> str:
    cleaned = " ".join((value or "").split())[:limit]
    return html.escape(cleaned, quote=True)


def _score_pct(score: Optional[float]) -> Optional[int]:
    if score is None:
        return None
    try:
        pct = int(round(float(score) * 100))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, pct))


@dataclass(frozen=True)
class DigestJob:
    """One row in a digest, already flattened out of the ORM."""

    title: str
    company: str
    location: str
    url: str
    match_score: Optional[float]
    match_reason: Optional[str]
    salary: Optional[str] = None
    job_type: Optional[str] = None


def _meta_line(job: DigestJob) -> str:
    bits = [b for b in (job.location, job.job_type, job.salary) if b and b.strip()]
    return " · ".join(bits)


def render_subject(pack: LocalePack, first_name: str, count: int, index: int, on_date: date) -> str:
    template = pack.subjects[index % len(pack.subjects)]
    return template.format(
        first_name=first_name,
        count=count,
        day_name=on_date.strftime("%A"),
    )


def render_text(
    pack: LocalePack,
    *,
    first_name: str,
    jobs: Sequence[DigestJob],
    index: int,
    cta_url: str,
    unsubscribe_url: str,
    settings_url: str,
) -> str:
    """Plain-text alternative. Required — HTML-only mail is a spam signal."""
    count = len(jobs)
    lines: List[str] = [
        pack.greetings[index % len(pack.greetings)].format(first_name=first_name),
        "",
        pack.intros[index % len(pack.intros)].format(count=count),
        "",
        f"{pack.jobs_heading}:",
        "",
    ]
    for position, job in enumerate(jobs, start=1):
        lines.append(f"{position}. {job.title} — {job.company}")
        meta = _meta_line(job)
        if meta:
            lines.append(f"   {meta}")
        pct = _score_pct(job.match_score)
        if pct is not None:
            lines.append(f"   {pct}% {pack.match_label}")
        if job.match_reason:
            reason = " ".join(job.match_reason.split())[:220]
            lines.append(f"   {pack.why_label}: {reason}")
        if job.url:
            lines.append(f"   {job.url}")
        lines.append("")

    if count == 1:
        lines.extend([pack.single_job_note, ""])

    lines.extend(
        [
            f"{pack.cta_button}: {cta_url}",
            "",
            pack.signoffs[index % len(pack.signoffs)],
            "",
            "—",
            pack.footer_reason,
            f"{pack.unsubscribe_label}: {unsubscribe_url}",
            f"{pack.manage_label}: {settings_url}",
        ]
    )
    return "\n".join(lines)


def _job_card_html(pack: LocalePack, job: DigestJob) -> str:
    title = _esc(job.title, 140)
    company = _esc(job.company, 100)
    url = html.escape(job.url or "", quote=True)
    meta = _esc(_meta_line(job), 160)
    pct = _score_pct(job.match_score)

    badge = ""
    if pct is not None:
        badge = (
            f'<span style="display:inline-block;background:#eef2ff;color:{BRAND_DARK};'
            'font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;'
            f'white-space:nowrap;">{pct}% {_esc(pack.match_label, 30)}</span>'
        )

    reason = ""
    if job.match_reason:
        reason = (
            f'<p style="margin:10px 0 0;font-size:13px;line-height:1.5;color:{MUTED};">'
            f'<strong style="color:{INK};">{_esc(pack.why_label, 40)}:</strong> '
            f"{_esc(job.match_reason, 240)}</p>"
        )

    meta_html = (
        f'<p style="margin:5px 0 0;font-size:13px;color:{MUTED};">{meta}</p>'
        if meta
        else ""
    )

    link_open = f'<a href="{url}" style="color:{BRAND};text-decoration:none;">' if url else "<span>"
    link_close = "</a>" if url else "</span>"

    action = ""
    if url:
        action = (
            f'<p style="margin:14px 0 0;"><a href="{url}" '
            f'style="display:inline-block;font-size:13px;font-weight:600;color:{BRAND};'
            'text-decoration:none;">'
            f"{_esc(pack.view_job_label, 40)} &rarr;</a></p>"
        )

    return f"""
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background:{CARD};border:1px solid {LINE};border-radius:12px;margin:0 0 14px;">
                <tr>
                  <td style="padding:18px 20px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:top;">
                          <h3 style="margin:0;font-size:16px;line-height:1.35;font-weight:700;color:{INK};">
                            {link_open}{title}{link_close}
                          </h3>
                          <p style="margin:4px 0 0;font-size:14px;color:{INK};">{company}</p>
                          {meta_html}
                        </td>
                        <td style="vertical-align:top;text-align:right;padding-left:12px;">{badge}</td>
                      </tr>
                    </table>
                    {reason}
                    {action}
                  </td>
                </tr>
              </table>"""


def render_html(
    pack: LocalePack,
    *,
    first_name: str,
    jobs: Sequence[DigestJob],
    index: int,
    cta_url: str,
    unsubscribe_url: str,
    settings_url: str,
) -> str:
    """Table-based, inline-styled HTML — the only layout email clients agree on."""
    count = len(jobs)
    safe_name = _esc(first_name, 60)
    greeting = pack.greetings[index % len(pack.greetings)].format(first_name=safe_name)
    intro = pack.intros[index % len(pack.intros)].format(count=count)
    preheader = pack.preheaders[index % len(pack.preheaders)]
    signoff = pack.signoffs[index % len(pack.signoffs)]

    cards = "".join(_job_card_html(pack, job) for job in jobs)
    cta = html.escape(cta_url, quote=True)
    unsub = html.escape(unsubscribe_url, quote=True)
    manage = html.escape(settings_url, quote=True)

    single_note = ""
    if count == 1:
        single_note = (
            f'<p style="margin:0 0 18px;font-size:13px;color:{MUTED};font-style:italic;">'
            f"{html.escape(pack.single_job_note)}</p>"
        )

    return f"""<!doctype html>
<html lang="{pack.code[:2]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{html.escape(pack.jobs_heading)}</title>
</head>
<body style="margin:0;padding:0;background:{CANVAS};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{html.escape(preheader)}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="max-width:600px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
          <tr>
            <td style="padding:0 0 18px;">
              <span style="font-size:17px;font-weight:800;color:{BRAND};letter-spacing:-0.2px;">VeloxaHire</span>
            </td>
          </tr>
          <tr>
            <td style="background:{CARD};border:1px solid {LINE};border-radius:16px;padding:26px 24px;">
              <p style="margin:0 0 12px;font-size:17px;font-weight:700;color:{INK};">{greeting}</p>
              <p style="margin:0 0 22px;font-size:15px;line-height:1.6;color:#374151;">{html.escape(intro)}</p>

              <p style="margin:0 0 12px;font-size:12px;font-weight:700;letter-spacing:0.6px;
                        text-transform:uppercase;color:{MUTED};">{html.escape(pack.jobs_heading)}</p>
              {cards}
              {single_note}

              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 6px;">
                <tr>
                  <td style="background:{BRAND};border-radius:10px;">
                    <a href="{cta}" style="display:inline-block;padding:12px 22px;font-size:15px;
                       font-weight:600;color:#ffffff;text-decoration:none;">{html.escape(pack.cta_button)}</a>
                  </td>
                </tr>
              </table>

              <p style="margin:20px 0 0;font-size:14px;color:#374151;">{html.escape(signoff)}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 6px 0;font-size:12px;line-height:1.6;color:{MUTED};text-align:center;">
              <p style="margin:0 0 8px;">{html.escape(pack.footer_reason)}</p>
              <p style="margin:0;">
                <a href="{unsub}" style="color:{MUTED};text-decoration:underline;">{html.escape(pack.unsubscribe_label)}</a>
                &nbsp;·&nbsp;
                <a href="{manage}" style="color:{MUTED};text-decoration:underline;">{html.escape(pack.manage_label)}</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_digest(
    *,
    locale: Optional[str],
    first_name: str,
    jobs: Sequence[DigestJob],
    user_id: str,
    on_date: date,
    cta_url: str,
    unsubscribe_url: str,
    settings_url: str,
) -> Dict[str, Any]:
    """Render subject + HTML + text for one user's digest."""
    pack = get_pack(locale)
    index = variant_index(user_id, on_date, len(pack.subjects))
    return {
        "locale": pack.code,
        "subject": render_subject(pack, first_name, len(jobs), index, on_date),
        "html": render_html(
            pack,
            first_name=first_name,
            jobs=jobs,
            index=index,
            cta_url=cta_url,
            unsubscribe_url=unsubscribe_url,
            settings_url=settings_url,
        ),
        "text": render_text(
            pack,
            first_name=first_name,
            jobs=jobs,
            index=index,
            cta_url=cta_url,
            unsubscribe_url=unsubscribe_url,
            settings_url=settings_url,
        ),
    }
