"""Read-only source collection and reproducible AURELIUS reports. No bot credentials."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
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
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', value))).strip()


def feed_summary(value: str) -> str:
    paragraphs = re.split(r'</p\s*>', value, flags=re.I)
    for paragraph in paragraphs:
        text = clean(paragraph)
        if not text or re.search(r'breaking news email|free app|daily news podcast|continue reading|sign up for', text, re.I):
            continue
        if len(text) > 320:
            text = text[:317].rsplit(' ', 1)[0] + '...'
        return text
    return ''


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
        items.append({'title': title[:240], 'url': link, 'published': published,
                      'summary': feed_summary(item.findtext('description', ''))})
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
            result['error'] = None
            return result
        except Exception as error:
            # No credential-bearing URLs, raw response bodies, or token-bearing errors.
            result['error'] = type(error).__name__
    return result


LOW_PRIORITY = re.compile(r"\b(emmy|emmys|actor|actress|celebrity|oscars|red carpet|football|cricket|horoscope|podcast|politics live|what is|how does)\b", re.I)
HIGH_PRIORITY = re.compile(r"\b(war|ceasefire|invasion|election|sanctions|inflation|interest rates|economy|energy|climate|earthquake|floods|cyberattack|security|artificial intelligence|AI|regulation|safeguards)\b", re.I)


def select_stories(results: list[dict], limit: int = 5) -> list[tuple]:
    candidates = [(result, item) for result in results for item in result['items']
                  if not LOW_PRIORITY.search(item['title'])]
    candidates.sort(key=lambda pair: (bool(HIGH_PRIORITY.search(pair[1]['title'])), pair[1]['published']), reverse=True)
    selected, urls, tokens_seen, categories, topics = [], set(), [], {}, {}
    for result, item in candidates:
        tokens = set(re.findall(r"\w+", item['title'].casefold())) - {'the', 'a', 'an', 'to', 'in', 'of', 'and', 'as', 'for', 'on', 'with', 's'}
        url = item['url'].split('?')[0].rstrip('/')
        duplicate = any(len(tokens & old) / max(1, len(tokens | old)) >= 0.55 for old in tokens_seen)
        category = result['category']
        topic = 'AI' if re.search(r'\b(AI|artificial intelligence|datacentre)\b', item['title'], re.I) else None
        if url in urls or duplicate or categories.get(category, 0) >= 2 or (topic and topics.get(topic, 0) >= 2):
            continue
        selected.append((result, item))
        urls.add(url)
        tokens_seen.append(tokens)
        categories[category] = categories.get(category, 0) + 1
        if topic:
            topics[topic] = topics.get(topic, 0) + 1
        if len(selected) == limit:
            break
    return selected


def morning_report(results: list[dict], now: datetime) -> str:
    lines = ['AURELIUS MORNING BRIEF', 'Generated: ' + local_time(now), '', 'KEY DEVELOPMENTS']
    selected = select_stories(results)
    if not selected:
        lines.append('NO VERIFIED CURRENT DATA - No eligible recent stories were retrieved.')
    for result, item in selected:
        lines.extend([result['category'] + ' - ' + result['name'] + ' reports: ' + item['title'],
                      'Published: ' + local_time(item['published'])])
        if item.get('summary') and item['summary'].casefold() != item['title'].casefold():
            lines.append('Publisher summary: ' + item['summary'])
        lines.append('')
    lines.append('SOURCE CHECK')
    for result in results:
        state = ('retrieval failed (' + result['error'] + ')') if result['error'] else str(len(result['items'])) + ' recent items'
        lines.append(result['name'] + ': ' + state)
    lines.extend(['', 'Selection: up to five stories within 36 hours; policy, economy, security and technology keywords first, then recency; maximum two per category. Entertainment, sport and rolling politics blogs excluded.', 'Publisher reports and summaries; not independently verified.'])
    return '\n'.join(lines).strip()


def evening_report(db_path: Path, now: datetime) -> str:
    lines = ['AURELIUS END-OF-DAY', 'Generated: ' + local_time(now)]
    start = local_datetime(now).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    end = now.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    try:
        with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            lines.extend(['', 'WORK AND OPEN ITEMS'])
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            tasks = []
            if {'memory_packs', 'memory_pack_revisions'} <= tables:
                row = db.execute('SELECT r.state_json FROM memory_packs p JOIN memory_pack_revisions r ON r.id=p.current_revision_id AND r.pack_id=p.id WHERE p.id=? AND p.archived=0', ('aurelius-shared-persistent-memory',)).fetchone()
                if row:
                    state = json.loads(row[0])
                    tasks = state.get('open_tasks', []) if isinstance(state, dict) else []
                    if not isinstance(tasks, list):
                        tasks = []
            usable = []
            for task in tasks:
                if isinstance(task, str) and task.strip():
                    usable.append(clean(task)[:350])
                elif isinstance(task, dict):
                    title = task.get('title') or task.get('text') or task.get('description')
                    if isinstance(title, str) and title.strip():
                        status = clean(str(task.get('status', 'open')))
                        usable.append(clean(title)[:300] + ' (recorded status: ' + status[:40] + ')')
            if usable:
                lines.append('Saved task records from Aurelius shared memory (may need a status update):')
                lines.extend('- ' + task for task in usable[:8])
                if len(usable) > 8:
                    lines.append(str(len(usable)-8) + ' more saved items.')
            else:
                lines.append("No work tasks are saved in Aurelius shared memory. Completed work and tomorrow's priorities are unavailable.")
            lines.extend(['', 'AUTOMATED ACTIVITY'])
            rows = db.execute('SELECT id,label,status,scheduled_for FROM scheduled_job_dispatches WHERE scheduled_for >= ? AND scheduled_for <= ? AND label != ? ORDER BY scheduled_for DESC LIMIT 20', (start, end, 'End-of-Day Shutdown')).fetchall()
            if not rows:
                lines.append('No other scheduled runs recorded today.')
            for dispatch_id, label, status, scheduled in rows:
                lines.append(clean(label) + ': ' + status)
                deliveries = db.execute("SELECT status FROM scheduled_job_delivery_attempts WHERE dispatch_id=? AND destination_kind='channel'", (dispatch_id,)).fetchall()
                if deliveries:
                    statuses = [row[0] for row in deliveries]
                    delivery = 'delivered' if 'delivered' in statuses else ', '.join(dict.fromkeys(statuses))
                    lines.append('Telegram delivery: ' + delivery)
            lines.extend(['', 'NEXT STEP', "Review the saved open items and choose tomorrow's first task." if usable else "Record today's completed work and one next task in your work tracker so the next review has work evidence.", '', 'Sources: Msty scheduled run records and Aurelius shared memory. Automated runs do not establish personal work completed.'])
    except (sqlite3.Error, ValueError, TypeError) as error:
        lines.append('Activity source unavailable (' + type(error).__name__ + '). No work summary could be verified.')
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
