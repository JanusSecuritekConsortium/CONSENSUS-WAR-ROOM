"""Inspectable priority rules. Every level change carries a plain reason."""
from __future__ import annotations

from datetime import datetime, timedelta

from .store import OPEN, PRIORITIES, parse

LEVEL = {name: index for index, name in enumerate(PRIORITIES)}
QUIET = 'kept quietly'


def quiet(item: dict) -> bool:
    """Old conversations stay queryable but never appear in a brief or an alert."""
    return any(QUIET in reason for reason in item.get('priority_reasons') or [])


def alert_worthy(item: dict, favourites) -> bool:
    """Very important: urgent, or high from a favourite contact; never unsure or quiet items."""
    if item['review'] or quiet(item) or item['state'] not in OPEN or item['kind'] == 'waiting':
        return False
    return item['priority'] == 'URGENT' or (item['priority'] == 'HIGH' and item.get('contact_id') in favourites)


def raise_to(current: str, target: str) -> str:
    return target if LEVEL[target] > LEVEL[current] else current


def bump(current: str) -> str:
    return PRIORITIES[min(LEVEL[current] + 1, len(PRIORITIES) - 2)]  # bumps never reach URGENT


def age_text(delta: timedelta) -> str:
    hours = int(delta.total_seconds() // 3600)
    if hours < 24:
        return f'{max(hours, 1)}h'
    days = hours // 24
    return f'{days} day' + ('s' if days != 1 else '')


def assess(item: dict, now: datetime, settings: dict) -> tuple[str, bool, list[str]]:
    """Return (priority, overdue, reasons) for an open or snoozed item."""
    local_today = now.astimezone(settings['tz']).date()
    level = 'LOW' if item['kind'] == 'waiting' else 'NORMAL'
    overdue = False
    reasons: list[str] = []
    seen = parse(item.get('first_seen_at')) or now
    age = now - seen
    last = parse(item.get('last_activity')) or seen
    undated = item['kind'] in ('reply', 'waiting') or (item['kind'] == 'commitment' and not item.get('due_at'))
    if undated and not item.get('pinned_priority') and now - last >= timedelta(days=settings['quiet_after_days']):
        return 'LOW', False, [f'no activity for {age_text(now - last)}; {QUIET}']
    if item['kind'] == 'reply':
        if age >= timedelta(hours=settings['reply_overdue_after_hours']):
            level, overdue = raise_to(level, 'HIGH'), True
            reasons.append(f'unanswered for {age_text(age)}')
        elif age >= timedelta(hours=settings['reply_high_after_hours']):
            level = raise_to(level, 'HIGH')
            reasons.append(f'unanswered for {age_text(age)}')
        if item.get('follow_ups', 0) >= 2:
            level = bump(level)
            reasons.append(f'{item["follow_ups"]} messages since your last reply')
    elif item['kind'] == 'commitment' and item.get('due_at'):
        due = parse(item['due_at']).astimezone(settings['tz']).date() if 'T' in item['due_at'] \
            else datetime.strptime(item['due_at'], '%Y-%m-%d').date()
        if due < local_today:
            level, overdue = raise_to(level, 'HIGH'), True
            days = (local_today - due).days
            reasons.append('due yesterday' if days == 1 else f'due {days} days ago')
        elif due == local_today:
            level = raise_to(level, 'HIGH')
            reasons.append('due today')
    elif item['kind'] == 'appointment' and (item.get('event') or {}).get('date'):
        day = datetime.strptime(item['event']['date'], '%Y-%m-%d').date()
        if 0 <= (day - local_today).days <= 2:
            level = raise_to(level, 'HIGH')
            reasons.append('proposed date is close')
    elif item['kind'] == 'waiting' and age >= timedelta(days=settings['waiting_remind_after_days']):
        level = raise_to(level, 'NORMAL')
        reasons.append(f'no answer for {age_text(age)}')
    if item.get('contact_id') in settings['important_contacts']:
        level = bump(level)
        reasons.append('important contact')
    if item.get('urgent'):
        level = 'URGENT'
        reasons.append('marked urgent in the conversation')
    if item.get('review'):
        level = 'LOW' if level != 'URGENT' else level
        reasons.append(f'unsure (confidence {item["confidence"]:.2f}); please confirm')
    if item.get('pinned_priority'):
        level = item['pinned_priority']
        reasons.append('priority set by you')
    return level, overdue, reasons
