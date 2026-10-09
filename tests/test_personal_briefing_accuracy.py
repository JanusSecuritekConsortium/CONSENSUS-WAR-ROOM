from datetime import datetime, timezone
import json
import pytest
from integrations.msty.personal.review import possible_misses, render
from integrations.msty.personal.studio import add_rules, RULES
from integrations.msty.personal.studio import briefing_model_info
from integrations.msty.personal.review import render_english
from integrations.msty.personal.service import personal_review
from unittest.mock import patch

NOW = datetime(2026,9,27,8,tzinfo=timezone.utc)


def mail(subject, body, **extra):
    return dict(direction='inbox', date='2026-09-20T08:00:00+00:00', subject=subject,
                body=body, message_id='<test@example.org>', **extra)


@pytest.mark.parametrize('subject,body', [
    ('Tu pedido de Example Store', 'Please review our terms. Your order is confirmed.'),
    ('Thank you for your Example purchase!', 'Please confirm receipt if you contact support.'),
    ('Recordatorio de tu cita', 'Por favor revisa los detalles de tu cita.'),
    ('Reminder', 'Your appointment is tomorrow.'),
])
def test_receipts_and_bare_reminders_are_not_pending_tasks(subject,body):
    assert possible_misses([mail(subject,body)],NOW)==[]


def test_automated_notice_without_action_subject_is_not_followup():
    item=mail('An error occurred', 'Please review the help center.', **{'from':'no-reply@example.org'})
    assert possible_misses([item],NOW)==[]


def test_explicit_requests_and_payment_actions_remain_candidates():
    for item in [mail('Project proposal','Could you review the proposal?'),
                 mail('Action required: payment failed','Please pay the outstanding balance.',automated=True)]:
        assert possible_misses([item],NOW)==[item]


def test_report_does_not_invent_end_times_or_omit_source_coverage():
    results=[{'id':'work','kind':'imap','group':'work','label':'Work','status':'ok','messages':[]},
             {'id':'calendar','kind':'calendar','label':'Calendar','status':'ok','events':[
                 {'uid':'one','start':'2026-09-27T09:15:00+02:00','all_day':False,'title':'Busy','location':'','status':''},
                 {'uid':'two','start':'2026-09-27T16:00:00+02:00','end':'2026-09-27T16:30:00+02:00','all_day':False,'title':'Event','location':'','status':'TENTATIVE'}]}]
    body=render(results,NOW,'morning')
    assert '09:15:00+02:00 (end time unavailable)' in body
    assert '16:00:00+02:00 to 2026-09-27T16:30:00+02:00' in body
    assert 'attendance/RSVP is not verified' in body
    assert 'Work: ok' in body and '200 combined' in body


def test_prompt_upgrade_replaces_old_rules_without_losing_user_text():
    old=json.dumps({'text':'Existing preference\n[AURELIUS LIVE BRIEFINGS]\nOLD\n[/AURELIUS LIVE BRIEFINGS]','mode':'append'})
    new=add_rules(old)
    assert new==add_rules(new)
    text=json.loads(new)['text']
    assert 'Existing preference' in text and 'OLD' not in text and RULES in text


def test_briefing_window_limits_history_without_mutating_other_options():
    original = {'id':'model', 'modelParams':{'temperature':0.2,'contextMessageLimit':20}}
    updated = briefing_model_info(original)
    assert updated['modelParams'] == {'temperature':0.2,'contextMessageLimit':1}
    assert original['modelParams']['contextMessageLimit']==20


def test_each_review_collects_again_with_unique_consultation_id():
    with patch('integrations.msty.personal.review.run',return_value='INFORME ACTUAL') as run:
        first,second=personal_review('morning'),personal_review('morning')
    assert run.call_count==2
    assert first['consultation_id']!=second['consultation_id']
    assert first['body_text'].startswith('INFORME ACTUAL\n\nConsultation: ')


def test_english_report_preserves_sources_and_rejects_receipt_tasks():
    results=[{'id':'work','kind':'imap','label':'Example work account','status':'ok','messages':[
        mail('Tu pedido de Example Store','Please review the terms.')], 'warnings':['A message was skipped (size/metadata limit)']},
        {'id':'outlook','kind':'outlook','label':'Outlook personal','status':'not configured'}]
    body=render_english(results,NOW,'morning')
    assert '27/09/2026 10:00:00' in body
    assert 'Example work account: read successfully: 1 Inbox + 0 Sent = 1 messages' in body
    assert 'Outlook personal: excluded or not configured' in body
    assert 'A message was skipped' in body
    assert 'Tu pedido de Example Store' not in body
    assert '100 Inbox and 100 Sent messages' in body
