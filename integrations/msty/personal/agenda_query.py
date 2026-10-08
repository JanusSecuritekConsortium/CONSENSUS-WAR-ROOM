"""Fresh, read-only agenda questions that do not depend on the model server."""
from datetime import datetime, timedelta
import re
from . import store
from .connectors import TZ, calendar_events
from .context import agenda, stamp


def answer(text, now=None):
    query = ' '.join(text.casefold().strip(' .?!').split())
    match = re.fullmatch(r'(?:please )?(?:check|show|read|what is|what\'s)(?: me)?(?: my| the)? (?:schedule|agenda|calendar)(?: for)?(?: today| tomorrow)?(?: afternoon| morning| evening)?', query)
    if not match:
        return None
    now = now or datetime.now(TZ)
    day = now.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    if 'tomorrow' in query:
        day += timedelta(days=1)
    hours = (12,18) if 'afternoon' in query else (0,12) if 'morning' in query else (18,24) if 'evening' in query else (0,24)
    start, end = day+timedelta(hours=hours[0]), day+timedelta(hours=hours[1])
    sources, warnings = [], []
    accounts = [a for a in store.load()['accounts'] if a.get('kind')=='calendar' and a.get('enabled')]
    for account in accounts:
        try:
            result = calendar_events(account, now, 'morning')
            events=[]
            for event in result['events']:
                beginning=stamp(event['start'])
                ending=stamp(event.get('end'))
                if beginning and beginning < end and ((ending and ending > start) or (not ending and beginning >= start)):
                    events.append(event)
            sources.append({'id':account['id'],'label':account['label'],'status':'ok','events':events})
            warnings.extend(result.get('warnings', []))
        except Exception:
            warnings.append(account['label']+': calendar unavailable; appointments could not be checked.')
    heading='AURELIUS — AGENDA · '+day.strftime('%d/%m/%Y')+' · '+str(hours[0]).zfill(2)+':00–'+str(hours[1]).zfill(2)+':00 · Europe/Madrid'
    if not accounts:
        return heading+'\nNo enabled calendar is configured.'
    body='\n'.join(agenda(sources)) if sources else 'Calendar unavailable. I cannot confirm your schedule.'
    return heading+'\n'+body+'\n'+'\n'.join(dict.fromkeys(warnings))
