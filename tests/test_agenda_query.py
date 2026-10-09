from datetime import datetime
from integrations.msty.personal import agenda_query as q

def test_afternoon_filters_and_keeps_overlap(monkeypatch):
    monkeypatch.setattr(q.store,'load',lambda:{'accounts':[{'id':'cal','label':'Calendar','kind':'calendar','enabled':True}]})
    def event(title,start,end):return {'uid':title,'title':title,'start':'2026-10-08T'+start+':00+02:00','end':'2026-10-08T'+end+':00+02:00'}
    monkeypatch.setattr(q,'calendar_events',lambda *a:{'events':[event('Morning','09:00','10:00'),event('Review','14:00','16:00'),event('Call','15:00','16:30')],'warnings':[]})
    body=q.answer('Check my schedule for today afternoon',datetime(2026,10,8,10,tzinfo=q.TZ))
    assert 'Review' in body and 'Call' in body and 'Morning' not in body
    assert 'SCHEDULE OVERLAPS' in body and '12:00' in body

def test_mutations_not_interpreted_as_reads():
    assert q.answer('Book my schedule for today') is None
    assert q.answer('Check my schedule for today and delete it') is None

def test_calendar_failure_not_empty_schedule(monkeypatch):
    monkeypatch.setattr(q.store,'load',lambda:{'accounts':[{'id':'cal','label':'Calendar','kind':'calendar','enabled':True}]})
    def failed(*a):raise RuntimeError()
    monkeypatch.setattr(q,'calendar_events',failed)
    assert 'cannot confirm' in q.answer('Check my schedule for tomorrow')
