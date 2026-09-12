"""Read-only source collection and reproducible AURELIUS reports. No bot credentials."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FEEDS = (
    ('World', 'BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Business', 'BBC Business', 'https://feeds.bbci.co.uk/news/business/rss.xml'),
    ('Technology', 'BBC Technology', 'https://feeds.bbci.co.uk/news/technology/rss.xml'),
    ('World', 'The Guardian World', 'https://www.theguardian.com/world/rss'),
)
MAX_BYTES = 2_000_000


def clean(value: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', '', value))).strip()


def local_datetime(now: datetime) -> datetime:
    try:
        return now.astimezone(ZoneInfo('Europe/Madrid'))
    except ZoneInfoNotFoundError:
        # Windows has OS timezone rules even when Python's optional tzdata is absent.
        return now.astimezone()


def local_time(now: datetime) -> str:
    return local_datetime(now).strftime('%Y-%m-%d %H:%M UTC%z')


def parse_feed(data: bytes, now: datetime) -> list[dict]:
    if len(data) > MAX_BYTES or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsafe or oversized feed')
    root = ET.fromstring(data)
    items = []
    for item in root.findall('.//item'):
        title = clean(item.findtext('title', ''))
        link = item.findtext('link', '').strip()
        try:
            published = parsedate_to_datetime(item.findtext('pubDate', ''))
            if published.tzinfo is None:
                continue
        except (TypeError, ValueError, OverflowError):
            continue
        if not title or urlparse(link).scheme != 'https' or '/iplayer/' in link:
            continue
        if not now - timedelta(hours=36) <= published <= now + timedelta(minutes=5):
            continue
        items.append({'title': title[:240], 'url': link, 'published': published})
    return sorted(items, key=lambda item: item['published'], reverse=True)


def fetch_feed(feed: tuple, now: datetime) -> dict:
    category, name, url = feed
    result = {'category': category, 'name': name, 'url': url, 'items': [], 'error': None}
    for attempt in range(2):
        try:
            request = Request(url, headers={'User-Agent': 'AureliusBrief/1.0 (RSS reader)'})
            with urlopen(request, timeout=12) as response:
                data = response.read(MAX_BYTES + 1)
            result['items'] = parse_feed(data, now)
            return result
        except Exception as error:
            # No credential-bearing URLs, raw response bodies, or token-bearing errors.
            result['error'] = type(error).__name__
    return result


def morning_report(results: list[dict], now: datetime) -> str:
    lines = ['AURELIUS MORNING BRIEF', 'Generated: ' + local_time(now), '', 'SOURCE CHECK']
    for result in results:
        state = ('retrieval failed (' + result['error'] + ')') if result['error'] else str(len(result['items'])) + ' dated headlines within 36 hours'
        lines.append(result['name'] + ': ' + state)
    lines.extend(['', 'CURRENT HEADLINES'])
    selected, seen = [], set()
    # One headline per source/category before filling any remaining slots.
    for result in results:
        for item in result['items']:
            key = item['title'].casefold()
            if key not in seen:
                selected.append((result, item))
                seen.add(key)
                break
    if not selected:
        lines.append('NO VERIFIED CURRENT DATA - No recent dated headlines were retrieved. Check source connectivity; no news was invented.')
    for result, item in selected[:5]:
        lines.extend([
            result['category'] + ' - ' + result['name'] + ' reports: ' + item['title'],
            'Published: ' + local_time(item['published']),
            '',
        ])
    lines.extend(['SCOPE AND LIMITATIONS', 'These are publisher-attributed RSS headlines, not independently verified events. No live market quotes or unsupported recommendations are included.'])
    return '\n'.join(lines).strip()


def evening_report(db_path: Path, now: datetime) -> str:
    lines = ['AURELIUS END-OF-DAY', 'Generated: ' + local_time(now), '', 'VERIFIED SCHEDULED ACTIVITY']
    start = local_datetime(now).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    end = now.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    try:
        with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            rows = db.execute('SELECT id,label,status,scheduled_for FROM scheduled_job_dispatches WHERE scheduled_for >= ? AND scheduled_for <= ? AND label IN (?,?) ORDER BY scheduled_for', (start, end, 'Morning Brief', 'End-of-Day Shutdown')).fetchall()
            if not rows:
                lines.append('No report runs recorded today before this check.')
            for dispatch_id, label, status, scheduled in rows:
                lines.append(label + ': ' + status + ' (scheduled ' + local_time(datetime.fromisoformat(scheduled.replace('Z', '+00:00'))) + ')')
                deliveries = db.execute("SELECT status FROM scheduled_job_delivery_attempts WHERE dispatch_id=? AND destination_kind='channel'", (dispatch_id,)).fetchall()
                lines.append('Telegram delivery: ' + (', '.join(row[0] for row in deliveries) if deliveries else 'not recorded yet'))
    except sqlite3.Error as error:
        lines.append('Activity database unavailable (' + type(error).__name__ + '). No completed work was inferred.')
    lines.extend(['', 'SOURCE CHECK', 'Msty Go local scheduling and delivery records, read-only at the generated time.', '', 'LIMITATIONS', 'This confirms scheduled report activity only. Personal work, meetings, deadlines and priorities are not inferred from these records.'])
    return '\n'.join(lines)


def collect_report(kind: str) -> str:
    now = datetime.now(timezone.utc)
    if kind == 'morning':
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda feed: fetch_feed(feed, now), FEEDS))
        return morning_report(results, now)
    if kind == 'evening':
        return evening_report(Path(os.path.expandvars(r'%APPDATA%\Msty Go\msty-go.db')), now)
    raise ValueError('kind must be morning or evening')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=('morning', 'evening'))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    print(collect_report(args.kind))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
