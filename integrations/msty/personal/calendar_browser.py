"""Dedicated local Proton browser profile; credentials are entered by the user."""
import argparse
from pathlib import Path
from . import store

PROFILE = store.ROOT/'proton-browser'
IMPORT_URL = 'https://account.proton.me/u/1/calendar/import-export'


def open_context(playwright, headless=True):
    return playwright.chromium.launch_persistent_context(str(PROFILE), channel='msedge',
        headless=headless, locale='en-US', timezone_id='Europe/Madrid',
        accept_downloads=False, viewport={'width':1280,'height':900})


def login():
    from playwright.sync_api import sync_playwright
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        context = open_context(pw, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto('https://calendar.proton.me', wait_until='domcontentloaded')
        # Keep this explicitly requested interactive window open until the user closes it.
        try:
            page.wait_for_event('close', timeout=1800000)
        finally:
            context.close()


def event_file(payload, action_id):
    from datetime import datetime, timezone
    import icalendar
    calendar=icalendar.Calendar()
    calendar.add('prodid','-//Aurelius//User requested actions//EN')
    calendar.add('version','2.0')
    event=icalendar.Event()
    event.add('uid','aurelius-'+action_id+'@local')
    event.add('dtstamp',datetime.now(timezone.utc))
    event.add('dtstart',datetime.fromisoformat(payload['start']).astimezone(timezone.utc))
    event.add('dtend',datetime.fromisoformat(payload['end']).astimezone(timezone.utc))
    event.add('summary',payload['title'])
    event.add('location',payload.get('location',''))
    event.add('description',payload.get('description',''))
    calendar.add_component(event)
    folder=store.ROOT/'calendar-actions'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(action_id+'.ics')
    path.write_bytes(calendar.to_ical())
    return path


def create_event(payload,action_id):
    from playwright.sync_api import sync_playwright, TimeoutError
    import re
    path=event_file(payload,action_id)
    with sync_playwright() as pw:
        context=open_context(pw)
        try:
            page=context.pages[0] if context.pages else context.new_page()
            page.goto(IMPORT_URL,wait_until='domcontentloaded',timeout=30000)
            button=page.get_by_role('button',name=re.compile(r'^(Importar desde ICS|Import from ICS)$'))
            try:
                button.wait_for(timeout=20000)
            except TimeoutError:
                return {'status':'draft','needs':'Proton browser sign-in or import page unavailable; nothing imported.'}
            button.click()
            dialog=page.get_by_role('dialog')
            selected=dialog.locator('#import-calendar-select').inner_text()
            expected=next(a for a in store.load()['accounts'] if a['id']=='proton-calendar').get('write_calendar_name','My calendar')
            if selected.strip()!=expected:
                return {'status':'draft','needs':'Calendar selection does not match configured target; nothing imported.'}
            dialog.locator('input[type=file]').set_input_files(str(path))
            # This is the only operation that commits a calendar change.
            dialog.get_by_role('button',name=re.compile(r'^(Importar|Import)$')).click()
            # Observed Proton confirmation includes the successful event count.
            # A hidden/disabled Import button during encryption is NOT success.
            dialog.get_by_text(re.compile(r'1/1\s+(evento cifrado y añadido a tu calendario|event encrypted and added to your calendar)',re.I)).wait_for(timeout=90000)
            return {'status':'created','uid':'aurelius-'+action_id+'@local','calendar':selected,
                    'meaning':'Proton confirmed the ICS import. Shared read-only feed may lag.'}
        finally:
            context.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['login'])
    parser.parse_args()
    login()
