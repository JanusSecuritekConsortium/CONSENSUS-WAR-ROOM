"""Import a Google Contacts CSV export: names, addresses and favourites (starred contacts).

Export from contacts.google.com (Export > Google CSV) and save the file as
<state folder>/system/google-contacts.csv. Each scan re-imports it when it changes.
The addresses of one Google contact join one attention contact because Google lists
them together; addresses already tracked as different people are never merged, only proposed.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import re

from . import config, log, store

EMAIL_COLUMN = re.compile(r'^E-mail \d+ - Value$', re.IGNORECASE)


def csv_path(settings: dict) -> Path:
    return Path(settings['google_contacts_csv']) if settings['google_contacts_csv'] \
        else config.home() / 'system' / 'google-contacts.csv'


def parse(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    people = []
    for row in rows:
        name = (row.get('Name') or ' '.join(filter(None, [row.get('First Name'), row.get('Middle Name'),
                                                           row.get('Last Name')]))).strip()
        labels = (row.get('Labels') or row.get('Group Membership') or '').casefold()
        emails = []
        for column, value in row.items():
            if column and EMAIL_COLUMN.match(column) and value:
                emails += [part.strip().casefold() for part in value.split(':::') if '@' in part]
        if emails:
            people.append({'name': name, 'emails': list(dict.fromkeys(emails)), 'favourite': 'starred' in labels})
    return people


def apply(db, people: list[dict], now: datetime) -> dict:
    favourites, created, proposals = set(), 0, 0
    stamp = store.iso(now)
    for person in people:
        known = {}
        for address in person['emails']:
            row = db.execute("SELECT contact_id FROM identities WHERE channel='email' AND address=?", (address,)).fetchone()
            if row:
                known[address] = row['contact_id']
        owners = sorted(set(known.values()))
        if owners:
            contact_id = owners[0]
        else:
            contact_id = store.contact_for(db, 'email', person['emails'][0], person['name'], now)
            known[person['emails'][0]] = contact_id
            created += 1
        for other in owners[1:]:  # already separate people: ask, never merge
            for address, owner in known.items():
                if owner == other:
                    db.execute('INSERT OR IGNORE INTO identity_proposals VALUES(?,?,?,?,?,?)',
                               ('email', address, contact_id, 'same Google contact', 'proposed', stamp))
                    proposals += 1
        for address in person['emails']:
            if address not in known:
                db.execute("INSERT INTO identities(channel,address,contact_id,display_name) VALUES('email',?,?,?)",
                           (address, contact_id, person['name']))
        if person['name']:
            db.execute('UPDATE contacts SET name=?, updated_at=? WHERE id=? AND name<>?',
                       (person['name'], stamp, contact_id, person['name']))
        if person['favourite']:
            favourites.add(contact_id)
    store.meta_set(db, 'favourite_contacts', sorted(favourites))
    log.event('contacts_imported', people=len(people), favourites=len(favourites), created=created, proposals=proposals)
    return {'people': len(people), 'favourites': len(favourites), 'created': created, 'proposals': proposals}


def sync(db, settings: dict, now: datetime, force: bool = False) -> dict | None:
    """Import the export when it is new or changed since the last import."""
    path = csv_path(settings)
    if not path.exists():
        return None
    stamp = path.stat().st_mtime
    if not force and store.meta_get(db, 'google_contacts_mtime') == stamp:
        return None
    result = apply(db, parse(path), now)
    store.meta_set(db, 'google_contacts_mtime', stamp)
    return result
