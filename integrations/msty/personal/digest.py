"""Bounded plain-text Telegram digests; detailed evidence stays in the vault."""
from .context import agenda, mail_context, clean
from .connectors import TZ


def units(text):
    return len(text.encode('utf-16-le'))//2


def short(text, limit=200):
    text = clean(text)
    if units(text) <= limit:
        return text
    while units(text) > limit-1:
        text = text[:-1]
    return text.rstrip()+'…'


def section(title, items, budget):
    lines = [title]
    for index, item in enumerate(items):
        item = short(item, 240)
        remaining = len(items)-index
        if units('\n'.join(lines+[item])) > budget-70:
            lines.append('+'+str(remaining)+' more items; details in local memory.')
            break
        lines.append(item)
    return '\n'.join(lines)


def personal_digest(results, now, tasks=None, weekly=False, morning=True):
    mail, failures = [], []
    low = 0
    for source in results:
        if source['status']=='unavailable':
            failures.append(source['label'])
        if source['status']!='ok':
            continue
        priority, isolated = mail_context(source.get('messages', []), now)
        low += len(isolated)
        for item in priority:
            message = item['message']
            mail.append('- '+('Attention: ' if item['urgent'] else 'Consider replying: ')+
                        clean(message.get('subject',''))+' ['+source['label']+']')
    if not mail:
        mail = ['No priority requests detected.']
    mail.append(str(low)+' isolated requests at low priority. Possible follow-ups, not confirmed tasks.')
    calendar = agenda(results)
    conflicts = [line for line in calendar if '↔' in line]
    entries = [line for line in calendar if line and (line.startswith('- ') and '↔' not in line or
               any(line.startswith(day+' ') for day in ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')))]
    if not entries:
        entries=['No appointments retrieved.']
    todo=[]
    for task in tasks or []:
        if isinstance(task,str) and task.strip():
            todo.append('- '+clean(task))
        elif isinstance(task,dict) and str(task.get('status','open')).casefold() not in ('done','completed','cancelled','closed'):
            title=task.get('title') or task.get('text') or task.get('description')
            if title:
                todo.append('- '+clean(title))
    sections=['AURELIUS · '+('DAILY PLAN' if morning else 'REVIEW')+' · '+now.astimezone(TZ).strftime('%d/%m %H:%M'),
              section('SAVED TASKS',todo or ['Task list unavailable.' if tasks is None else 'No open tasks recorded.'],550),
              section('EMAIL',mail,800),
              section('AGENDA · '+('NEXT WEEK' if weekly else 'TODAY AND COMING DAYS' if morning else 'TOMORROW'),entries,1400)]
    if conflicts:
        sections.append(section('OVERLAPS · check whether intentional',conflicts,650))
    else:
        sections.append('No overlaps detected between events with known start and end times.')
    if failures:
        sections.append('Unavailable: '+short(', '.join(failures),180))
    if any('does not share the title' in line for line in calendar):
        sections.append('Some calendar titles are hidden.')
    sections.append('Partial coverage; calendar updates may lag. Details saved in the vault.')
    return '\n\n'.join(sections)


def news_digest(body):
    # Each news item is a headline plus its source URL; keep references together.
    groups=[]
    for line in body.splitlines():
        if line.startswith('- '):
            groups.append([line])
        elif groups and line.strip().startswith('https://'):
            groups[-1].append(line.strip())
    lines=['AURELIUS · NEWS']
    for index, group in enumerate(groups):
        item=short(group[0],260)+'\n'+(group[1] if len(group)>1 else '')
        if units('\n\n'.join(lines+[item]))>3700:
            lines.append('More news in local memory.')
            break
        lines.append(item)
    if not groups:
        lines.append('No current news retrieved.')
    lines.append('Sources linked; headlines from the last 36 hours. Not a real-time alert service.')
    return '\n\n'.join(lines)
