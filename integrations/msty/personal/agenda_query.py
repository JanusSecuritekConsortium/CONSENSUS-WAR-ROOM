"""Fresh, read-only agenda questions that do not depend on the model server."""
from datetime import datetime, timedelta
import re
from . import store
from .connectors import TZ, calendar_events
from .context import agenda, stamp, clean, event_title
from .language import choose, detect, fold


def location_reply(sources, target, *, plural=False, excluded_titles=(), lang='en'):
    """Answer from recorded locations; clarify an ambiguous appointment."""
    key = fold(clean(target).strip('"“”'))
    generic = key in ('meeting', 'meetings', 'appointment', 'appointments', 'event', 'events',
                      'reunion', 'reuniones', 'cita', 'citas', 'evento', 'eventos')
    excluded = {clean(title).casefold() for title in excluded_titles if isinstance(title, str)} if isinstance(excluded_titles, list) else set()
    candidates, seen = [], set()
    for source in sources:
        for event in source.get('events', []):
            if event.get('status', '').upper() == 'CANCELLED':
                continue
            title = event_title(event)
            normalized = fold(title)
            if generic and title.casefold() in excluded:
                continue
            if not generic and normalized != key:
                continue
            identity = (event.get('uid') or source['id']+title, event['start'])
            if identity not in seen:
                candidates.append(event)
                seen.add(identity)
    if not candidates:
        return choose(lang, 'No matching appointments were retrieved for that period.',
                      'No se encontraron citas coincidentes para ese período.')
    candidates.sort(key=lambda event: event['start'])
    if len(candidates) > 1 and not plural:
        return choose(lang, 'Which appointment do you mean?\n', '¿A qué cita te refieres?\n')+'\n'.join(
            '- '+event_title(event)+' · '+event_start(event).strftime('%d/%m %H:%M') for event in candidates)
    return '\n'.join('- '+event_title(event)+': '+(clean(event.get('location', '')) or
                        choose(lang, 'No location is recorded in the calendar.',
                               'No hay ubicación registrada en el calendario.')) for event in candidates)


def event_start(event):
    if event.get('all_day'):
        try:
            return datetime.fromisoformat(event['start']).replace(tzinfo=TZ)
        except (ValueError, KeyError):
            return None
    return stamp(event.get('start'))


def answer(text, now=None, *, lang=None, route=None, vault=None):
    lang = lang or detect(text)
    query = ' '.join(fold(text).strip(' .?!¿¡').split())
    query = re.sub(r'[, ]+(?:in english|in spanish|en ingles|en espanol)$', '', query)
    if re.search(r'\b(?:book|create|cancel|delete|move|reschedule|send|invite|reserva|crea|cancela|borra|elimina|mueve|reprograma|envia|invita)\b', query):
        return None
    location = re.fullmatch(r"(?:please )?(?P<verb>where is|where's|where are) (?:(?:my|the) )?(?P<title>.+?)(?: (?:for )?(?P<day>today|tomorrow))?", query)
    explicit_locations = re.search(r' (?:with|including)(?: the)? (?:locations|venues|addresses)$', query)
    if not location:
        location = re.fullmatch(r'(?:por favor )?(?P<verb>donde es|donde esta|donde estan|donde son) (?:(?:mi|mis|la|las|el|los) )?(?P<title>.+?)(?: (?P<day>hoy|manana))?', query)
    explicit_locations = explicit_locations or re.search(r' (?:con|incluyendo)(?: las)? (?:ubicaciones|direcciones|lugares)$', query)
    schedule_query = query[:explicit_locations.start()] if explicit_locations else query
    match = re.fullmatch(r'(?:please )?(?:check|show|read|what is|what\'s)(?: me)?(?: my| the)? (?:schedule|agenda|calendar)(?: for)?(?: today| tomorrow)?(?: afternoon| morning| evening)?', schedule_query)
    match = match or re.fullmatch(r'(?:por favor )?(?:muestra(?:me)?|ensena(?:me)?|lee(?:me)?|revisa|consulta|cual es|que hay en)(?: mi| la| el)? (?:agenda|calendario|horario)(?: (?:para|de))?(?: hoy| manana)?(?: por la (?:manana|tarde|noche))?', schedule_query)
    next_query = query in ("what's next", 'what is next', 'whats next', 'what’s next', 'next appointment',
                           'what is my next meeting', "what's my next meeting", 'que sigue', 'que viene ahora',
                           'cual es mi proxima reunion', 'cual es mi siguiente cita')
    next_location = query in ('where is my next meeting', "where's my next meeting", 'where',
                              'donde es mi proxima reunion', 'donde esta mi proxima reunion', 'donde')
    changes = query in ('what changed', 'what has changed', "what's changed", 'que cambio', 'que ha cambiado', 'que cambios hay')
    if not match and not location and not next_query and not next_location and not changes:
        return None
    now = now or datetime.now(TZ)
    day = now.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    if (location['day'] in ('tomorrow', 'manana') if location else
            ('tomorrow' in schedule_query or 'manana' in schedule_query.replace('por la manana', ''))):
        day += timedelta(days=1)
    hours_query = '' if location else schedule_query
    hours = (12,18) if ('afternoon' in hours_query or 'por la tarde' in hours_query) else (0,12) if ('morning' in hours_query or 'por la manana' in hours_query) else (18,24) if ('evening' in hours_query or 'por la noche' in hours_query) else (0,24)
    start, end = day+timedelta(hours=hours[0]), day+timedelta(hours=hours[1])
    sources, warnings = [], []
    config = store.load()
    accounts = [a for a in config['accounts'] if a.get('kind')=='calendar' and a.get('enabled')]
    for account in accounts:
        try:
            result = calendar_events(account, now, 'morning')
            events=[]
            for event in result['events']:
                beginning=event_start(event)
                ending=event_start({**event, 'start': event.get('end')}) if event.get('end') else None
                if beginning and (next_query or next_location or changes or
                        beginning < end and ((ending and ending > start) or (not ending and beginning >= start))):
                    events.append(event)
            sources.append({**result,'id':account['id'],'label':account['label'],'kind':'calendar','status':'ok','events':events})
            # Source warnings are structured into the local language without translating names.
            if result.get('warnings'):
                warnings.append(choose(lang, 'Calendar source may lag updates or have limited coverage.',
                                       'La fuente del calendario puede tardar en actualizarse o tener cobertura limitada.'))
        except Exception:
            sources.append({'id':account['id'],'label':account['label'],'kind':'calendar','status':'unavailable','events':[]})
            warnings.append(account['label']+choose(lang, ': calendar unavailable; appointments could not be checked.', ': calendario no disponible; no se pudieron comprobar las citas.'))
    heading='AURELIUS — AGENDA · '+day.strftime('%d/%m/%Y')+' · '+str(hours[0]).zfill(2)+':00–'+str(hours[1]).zfill(2)+':00 · Europe/Madrid'
    if not accounts:
        return heading+'\n'+choose(lang, 'No enabled calendar is configured.', 'No hay ningún calendario habilitado.')
    available = [source for source in sources if source['status']=='ok']
    if changes:
        from .calendar_changes import snapshot, baseline, compare
        from .publication import VAULT
        from .interaction_store import owner
        previous = baseline(vault or VAULT, owner(route) if route else None)
        body = '\n'.join(compare(snapshot(sources, now), previous,
                                 excluded_titles=config.get('agenda_reminder_excluded_titles', []), lang=lang))
    elif (next_query or next_location) and available:
        excluded = {clean(title).casefold() for title in config.get('agenda_reminder_excluded_titles', [])}
        events = [event for source in available for event in source['events']
                  if (event.get('status') or '').upper() != 'CANCELLED'
                  and event_title(event).casefold() not in excluded and event_start(event) and event_start(event) >= now]
        events.sort(key=event_start)
        if events:
            event = events[0]
            nearest = [candidate for candidate in events if event_start(candidate)==event_start(event)]
            body = (location_reply([{'id':'next','events':nearest}], 'meetings', lang=lang) if next_location else
                    choose(lang, 'Next: ', 'Próximo: ')+event_title(event)+' · '+event_start(event).strftime('%d/%m %H:%M'))
        else:
            body = choose(lang, 'No upcoming appointments retrieved in the next seven days.', 'No se encontraron próximas citas en los siguientes siete días.')
    elif location and available:
        body = location_reply(sources, location['title'], plural=location['verb'] in ('where are', 'donde estan', 'donde son'),
                              excluded_titles=config.get('agenda_reminder_excluded_titles', []), lang=lang)
    else:
        body='\n'.join(agenda(available, excluded_titles=config.get('agenda_reminder_excluded_titles', []),
                              include_locations=bool(explicit_locations) or
                              config.get('agenda_include_locations_by_default', False) is True, lang=lang)) if available else choose(lang, 'Calendar unavailable. I cannot confirm your schedule.', 'Calendario no disponible. No puedo confirmar tu agenda.')
    return heading+'\n'+body+'\n'+'\n'.join(dict.fromkeys(warnings))
