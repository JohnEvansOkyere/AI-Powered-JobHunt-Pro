"""
Shared helpers for RSS/XML job feed scrapers (WeWorkRemotely, MyJobMag, JobWebGhana).
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional


def parse_rss_items(xml_text: str) -> List[Dict[str, str]]:
    """Parse RSS 2.0 <item> elements into dicts of tag -> text (namespaces stripped)."""
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        record: Dict[str, str] = {}
        for child in item:
            tag = child.tag.split("}")[-1]  # strip namespace
            text = (child.text or "").strip()
            if text and tag not in record:
                record[tag] = text
        items.append(record)
    return items


def parse_rfc822_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an RFC 822 pubDate to naive UTC (freshness filter compares utcnow())."""
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def strip_html(html: str) -> str:
    if not html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def fix_mojibake(text: str) -> str:
    """Undo latin-1/UTF-8 double encoding (MyJobMag feeds) and normalize nbsp."""
    if not text:
        return ""
    for _ in range(2):
        try:
            fixed = text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if fixed == text:
            break
        text = fixed
    return text.replace("\xa0", " ").strip()
