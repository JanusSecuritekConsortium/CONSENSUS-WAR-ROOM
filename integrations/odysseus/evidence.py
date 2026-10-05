"""Narrow read-only facts shared with the external AURELIUS engine."""
from __future__ import annotations

import json
import re

from core.paths import MEMORY_PATH


def clean(value):
    """Exclude credential-like fields and redact inline credential assignments."""
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()
                if not re.search(r'password|secret|token|api.?key|authorization', str(key), re.I)}
    if isinstance(value, list):
        return [clean(item) for item in value[:20]]
    if isinstance(value, str):
        return re.sub(r'(?i)(\b(?:password|secret|token|api[_ -]?key)\b\s*[:=]\s*)\S+',
                      r'\1<REDACTED>', value)[:3000]
    return value


def query_text(arguments):
    if not isinstance(arguments, dict) or set(arguments) - {'query'}:
        raise ValueError('Only a query is accepted')
    query = arguments.get('query', '')
    if not isinstance(query, str) or len(query) > 200:
        raise ValueError('Query must be text of at most 200 characters')
    return query.strip()


def mnemosyne_search(arguments):
    query = query_text(arguments)
    if not MEMORY_PATH.is_file():
        return {'status': 'unavailable', 'matches': [], 'source': 'CONSENSUS decision memory'}
    if MEMORY_PATH.stat().st_size > 2_000_000:
        raise ValueError('Memory source exceeds read budget')
    data = json.loads(MEMORY_PATH.read_text(encoding='utf-8-sig'))
    decisions = data.get('decisions', [])
    if not isinstance(decisions, list):
        raise ValueError('Unexpected decision-memory format')
    terms = query.casefold().split()
    matches = [item for item in decisions if not terms or
               any(term in str(item).casefold() for term in terms)]
    return {'status': 'available', 'source': 'CONSENSUS decision memory (MNEMOSYNE boundary)',
            'query': query, 'matches': clean(matches[-5:]), 'trust': 'untrusted_data'}


def aurelius_memory_recall(arguments):
    from integrations.msty.aurelius_memory import recall
    return clean(recall(query_text(arguments)))


def aurelius_briefing_memory(arguments):
    from integrations.msty.personal.publication import recall
    if not isinstance(arguments, dict) or set(arguments) - {'mode'}:
        raise ValueError('Only a briefing mode is accepted')
    mode = arguments.get('mode', 'latest')
    if mode not in {'latest', 'morning', 'evening', 'weekly'}:
        raise ValueError('Invalid briefing mode')
    result = clean(recall(mode))
    result['trust'] = 'untrusted_historical_snapshot'
    return result


HANDLERS = {'mnemosyne_search': mnemosyne_search,
            'aurelius_memory_recall': aurelius_memory_recall,
            'aurelius_briefing_memory': aurelius_briefing_memory}


def collect(prompt):
    """Fetch only sources explicitly relevant to the operator's request."""
    query = prompt.strip()[:200]
    lower = prompt.casefold()
    requested = []
    if re.search(r'\b(memory|remember|recall|memoria|recuerda|recordar)\b', lower):
        requested.append(('aurelius_memory_recall', {'query': query}))
    if re.search(r'\b(consensus|mnemosyne|decision|decisions|tribunal|decisión|decisiones)\b', lower):
        requested.append(('mnemosyne_search', {'query': query}))
    if re.search(r'\b(brief|briefing|briefings|agenda|informe)\b', lower):
        requested.append(('aurelius_briefing_memory', {'mode': 'latest'}))
    result = {}
    for name, arguments in requested:
        try:
            data = HANDLERS[name](arguments)
            if len(json.dumps(data, ensure_ascii=False)) > 4500:
                data = {'status': 'source_exceeds_context_budget', 'data_omitted': True}
            result[name] = data
        except Exception as error:
            result[name] = {'status': 'unavailable', 'error_type': type(error).__name__}
    return result
