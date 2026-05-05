import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

REQUEST_TIMEOUT = 30
USER_AGENT = "changelog-impact-pipeline/0.1"


def fetch_all(sources: list[dict]) -> dict[str, dict]:
    """Fetch each source. Returns {source_id: {"text": str|None, "error": str|None}}."""
    results = {}
    for src in sources:
        sid = src["source_id"]
        url = src["url"]
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            results[sid] = {"text": resp.text, "error": None}
        except Exception as e:
            print(f"[ingest] WARN failed to fetch {sid} ({url}): {e}")
            results[sid] = {"text": None, "error": str(e)}
    return results


def parse_all(raw: dict[str, dict], sources: list[dict]) -> dict[str, list[dict]]:
    """Parse each fetched payload deterministically into entry dicts."""
    parsed = {}
    for src in sources:
        sid = src["source_id"]
        fmt = src["format"]
        text = raw.get(sid, {}).get("text")
        if text is None:
            parsed[sid] = []
            continue
        if fmt == "markdown":
            entries = _parse_markdown(text, sid, src["name"])
        elif fmt == "html":
            entries = _parse_html(text, sid, src["name"])
        else:
            print(f"[ingest] WARN unknown format {fmt!r} for {sid}; skipping")
            entries = []
        parsed[sid] = entries
    return parsed


_VERSION_HEADER = re.compile(
    r"^##\s+(?:\[?v?(?P<version>\d[\w.\-+]*)\]?)?\s*[-–]?\s*(?P<rest>.*)$"
)
_DATE_INLINE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _parse_markdown(text: str, source_id: str, source_name: str) -> list[dict]:
    lines = text.splitlines()
    blocks: list[dict] = []
    current: dict | None = None
    body_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current is not None:
                current["body"] = "\n".join(body_lines).strip()
                blocks.append(current)
            m = _VERSION_HEADER.match(line)
            version = None
            published = None
            header_text = line[3:].strip()
            if m:
                version = m.group("version")
                rest = m.group("rest") or ""
                date_m = _DATE_INLINE.search(rest)
                if date_m:
                    published = date_m.group(1)
            if not published:
                date_m = _DATE_INLINE.search(header_text)
                if date_m:
                    published = date_m.group(1)
            if version is None:
                version = header_text or "unknown"
            current = {
                "version": version,
                "published_at": published,
                "header": header_text,
            }
            body_lines = []
        else:
            if current is not None:
                body_lines.append(line)

    if current is not None:
        current["body"] = "\n".join(body_lines).strip()
        blocks.append(current)

    entries: list[dict] = []
    sub_entries: list[tuple[dict, str, str | None]] = []  # (block, body_text, raw_type)

    for block in blocks:
        body = block.get("body", "")
        bullets = _extract_bullets(body)
        if bullets:
            for bullet in bullets:
                title, raw_type = _split_title_and_type(bullet)
                sub_entries.append((block, title, raw_type))
        else:
            title = block["header"] or block["version"]
            sub_entries.append((block, title, None))

    width = max(3, len(str(len(sub_entries))))
    for idx, (block, body_text, raw_type) in enumerate(sub_entries, start=1):
        entry_id = f"{source_id}-{str(idx).zfill(width)}"
        title = body_text.splitlines()[0].strip() if body_text else block["header"]
        entries.append({
            "entry_id": entry_id,
            "source_id": source_id,
            "source": source_name,
            "version_or_date": block["version"],
            "published_at": block["published_at"],
            "change_title": title[:200],
            "change_body": body_text.strip(),
            "change_type_raw": raw_type,
        })
    return entries


def _extract_bullets(body: str) -> list[str]:
    """Extract markdown list items, joining continuation lines."""
    items: list[str] = []
    current: list[str] | None = None
    for line in body.splitlines():
        if re.match(r"^[\s]*[-*+]\s+", line):
            if current is not None:
                items.append(" ".join(current).strip())
            current = [re.sub(r"^[\s]*[-*+]\s+", "", line)]
        elif current is not None and line.strip() == "":
            items.append(" ".join(current).strip())
            current = None
        elif current is not None and line.startswith((" ", "\t")):
            current.append(line.strip())
        else:
            if current is not None:
                items.append(" ".join(current).strip())
                current = None
    if current is not None:
        items.append(" ".join(current).strip())
    return [i for i in items if i]


_TYPE_PREFIX = re.compile(r"^\s*(?:\*\*)?(?P<type>[A-Za-z]+)(?:\*\*)?\s*[:\-]\s*(?P<rest>.*)$")


def _split_title_and_type(text: str) -> tuple[str, str | None]:
    m = _TYPE_PREFIX.match(text)
    if m:
        candidate = m.group("type").lower()
        known = {"breaking", "fix", "bugfix", "feat", "feature", "deprecated",
                 "deprecation", "security", "chore", "docs", "perf", "refactor",
                 "added", "changed", "removed", "fixed"}
        if candidate in known:
            return m.group("rest").strip(), candidate
    return text.strip(), None


def _parse_html(text: str, source_id: str, source_name: str) -> list[dict]:
    soup = BeautifulSoup(text, "html.parser")
    entries: list[dict] = []
    candidates: list[tuple[str | None, str, str]] = []  # (date, title, body)

    # Strategy 1: <article> tags
    articles = soup.find_all("article")
    if articles:
        for art in articles:
            date = _extract_date_from_node(art)
            heading = art.find(["h1", "h2", "h3", "h4"])
            title = heading.get_text(strip=True) if heading else ""
            body = art.get_text(" ", strip=True)
            if title or body:
                candidates.append((date, title or body[:120], body))

    # Strategy 2: dated heading sections
    if not candidates:
        for h in soup.find_all(["h2", "h3"]):
            text_h = h.get_text(" ", strip=True)
            date = _try_parse_date(text_h)
            if not date:
                continue
            body_parts: list[str] = []
            for sib in h.find_next_siblings():
                if sib.name in {"h1", "h2", "h3"}:
                    break
                body_parts.append(sib.get_text(" ", strip=True))
            body = " ".join(p for p in body_parts if p)
            candidates.append((date, text_h, body))

    # Strategy 3: list items as fallback
    if not candidates:
        for li in soup.find_all("li"):
            txt = li.get_text(" ", strip=True)
            if not txt:
                continue
            date = _try_parse_date(txt)
            candidates.append((date, txt[:120], txt))

    width = max(3, len(str(len(candidates))))
    for idx, (date, title, body) in enumerate(candidates, start=1):
        entry_id = f"{source_id}-{str(idx).zfill(width)}"
        entries.append({
            "entry_id": entry_id,
            "source_id": source_id,
            "source": source_name,
            "version_or_date": date or title[:60],
            "published_at": date,
            "change_title": title[:200],
            "change_body": body[:5000],
            "change_type_raw": None,
        })
    return entries


def _extract_date_from_node(node) -> str | None:
    time_tag = node.find("time")
    if time_tag:
        dt = time_tag.get("datetime") or time_tag.get_text(strip=True)
        d = _try_parse_date(dt)
        if d:
            return d
    return _try_parse_date(node.get_text(" ", strip=True))


def _try_parse_date(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if m:
        try:
            return dateparser.parse(m.group(0)).date().isoformat()
        except Exception:
            pass
    m = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
        text,
    )
    if m:
        try:
            return dateparser.parse(m.group(0)).date().isoformat()
        except Exception:
            pass
    return None
