"""Discover official postgraduate recommendation notices for manual review.

The crawler intentionally writes only to data/pending-notices.json. It searches
for every configured school, accepts only edu.cn/ac.cn pages, and never promotes
a record to the public list automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCHOOLS_PATH = DATA / "schools.json"
NOTICES_PATH = DATA / "notices.json"
PENDING_PATH = DATA / "pending-notices.json"
OVERRIDES_PATH = DATA / "source-overrides.json"
REPORT_PATH = DATA / "crawl-report.json"

NOTICE_WORDS = ("推免", "预推免", "推荐免试", "夏令营", "优秀大学生", "直博", "九推")
CS_WORDS = ("计算机", "软件", "人工智能", "网络空间安全", "信息", "电子", "自动化", "大数据")
ALLOWED_SUFFIXES = (".edu.cn", ".ac.cn")
USER_AGENT = "BaoyanDDLBot/1.0 (+manual-review; respectful daily crawler)"
TIMEOUT = 15


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        value = " ".join(data.split())
        if value:
            self.parts.append(value)
            if self.in_title:
                self.title_parts.append(value)

    @property
    def text(self) -> str:
        return " ".join(self.parts)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts)


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, value) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def fetch(url: str) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        body = response.read(2_000_000)
        try:
            return body.decode(content_type, errors="replace"), response.geturl()
        except LookupError:
            return body.decode("utf-8", errors="replace"), response.geturl()


def canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    clean_path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), clean_path, "", ""))


def is_official_url(url: str) -> bool:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return any(host == suffix[1:] or host.endswith(suffix) for suffix in ALLOWED_SUFFIXES)


def search_school(school: str, year: int) -> list[tuple[str, str]]:
    query = f'"{school}" ({" OR ".join(NOTICE_WORDS)}) ({" OR ".join(CS_WORDS)}) {year}'
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote(query)
    xml_text, _ = fetch(url)
    root = ET.fromstring(xml_text)
    results = []
    for item in root.findall(".//item")[:10]:
        title = html.unescape(item.findtext("title", default="")).strip()
        link = item.findtext("link", default="").strip()
        if link and is_official_url(link):
            results.append((title, link))
    return results


def extract_deadline(text: str) -> str | None:
    current_year = date.today().year
    patterns = [
        r"(?:截止(?:时间|日期)?|报名截至|申请截至)[^。；\n]{0,35}?(?:(20\d{2})\s*年)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?(?:[^。；\n]{0,12}?(\d{1,2})\s*[时:：点]\s*(\d{1,2})?\s*分?)?",
        r"(?:(20\d{2})[-/.年])\s*(\d{1,2})[-/.月]\s*(\d{1,2})日?[^。；\n]{0,18}?(?:截止|截至)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        year = int(match.group(1) or current_year)
        month, day = int(match.group(2)), int(match.group(3))
        hour = int(match.group(4) or 23) if match.lastindex and match.lastindex >= 4 else 23
        minute = int(match.group(5) or 59) if match.lastindex and match.lastindex >= 5 else 59
        try:
            return datetime(year, month, day, hour, minute).isoformat() + "+08:00"
        except ValueError:
            continue
    return None


def infer_type(value: str) -> str:
    if "夏令营" in value or "优秀大学生" in value:
        return "夏令营"
    if "直博" in value:
        return "直博"
    if "九推" in value:
        return "九推"
    return "预推免"


def candidate_from_url(school: dict, title_hint: str, url: str) -> dict | None:
    try:
        page, resolved_url = fetch(url)
    except Exception:
        return None
    if not is_official_url(resolved_url):
        return None
    parser = TextExtractor()
    parser.feed(page)
    title = parser.title.strip() or title_hint.strip()
    visible = parser.text[:250_000]
    combined = f"{title} {visible}"
    if not any(word in combined for word in NOTICE_WORDS):
        return None
    if not any(word in combined for word in CS_WORDS):
        return None
    if school["name"] not in combined and school["name"] not in title_hint:
        return None

    clean_url = canonical_url(resolved_url)
    digest = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]
    deadline = extract_deadline(combined)
    notice_type = infer_type(combined)
    confidence = "high" if deadline and any(word in title for word in NOTICE_WORDS) else "medium"
    today = date.today().isoformat()
    return {
        "id": f"auto-{digest}",
        "school": school["name"],
        "college": "待审核确认",
        "type": notice_type,
        "title": title[:240] or title_hint[:240] or "待审核的官方通知",
        "deadline": deadline,
        "sourceUrl": clean_url,
        "applyUrl": clean_url,
        "tags": [*school.get("tags", []), notice_type, "自动发现"],
        "discoveredAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lastCheckedAt": today,
        "verified": False,
        "reviewStatus": "pending",
        "confidence": confidence,
    }


def crawl_school(school: dict, override_urls: list[str], year: int) -> tuple[list[dict], str | None]:
    links: list[tuple[str, str]] = [("", item) for item in override_urls]
    try:
        links.extend(search_school(school["name"], year))
    except Exception as exc:
        search_error = f"{type(exc).__name__}: {exc}"
    else:
        search_error = None

    found = []
    seen = set()
    for title, url in links:
        key = canonical_url(url)
        if key in seen:
            continue
        seen.add(key)
        candidate = candidate_from_url(school, title, url)
        if candidate:
            found.append(candidate)
        time.sleep(0.15)
    return found, search_error


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--school", help="Only crawl one school by exact name")
    parser.add_argument("--limit", type=int, help="Limit school count for a smoke test")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schools = load_json(SCHOOLS_PATH, [])
    if args.school:
        schools = [item for item in schools if item["name"] == args.school]
    if args.limit:
        schools = schools[: args.limit]
    if not schools:
        raise SystemExit("No matching schools configured")

    overrides = load_json(OVERRIDES_PATH, {})
    published = load_json(NOTICES_PATH, [])
    pending = load_json(PENDING_PATH, [])
    known_urls = {canonical_url(item.get("sourceUrl", "")) for item in published + pending if item.get("sourceUrl")}
    new_items: list[dict] = []
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 10))) as executor:
        futures = {
            executor.submit(crawl_school, school, overrides.get(school["name"], []), date.today().year): school
            for school in schools
        }
        for future in as_completed(futures):
            school = futures[future]
            try:
                candidates, error = future.result()
                if error:
                    errors[school["name"]] = error
                for candidate in candidates:
                    key = canonical_url(candidate["sourceUrl"])
                    if key not in known_urls:
                        known_urls.add(key)
                        new_items.append(candidate)
            except Exception as exc:
                errors[school["name"]] = f"{type(exc).__name__}: {exc}"

    all_pending = sorted(pending + new_items, key=lambda item: item.get("discoveredAt", ""), reverse=True)
    report = {
        "ranAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schoolsAttempted": len(schools),
        "newCandidates": len(new_items),
        "pendingTotal": len(all_pending),
        "searchErrors": errors,
    }
    if not args.dry_run:
        save_json(PENDING_PATH, all_pending)
        save_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
