"""Keep a voter's prompt inside the local model's context window by dropping the least important extras first.

Msty's llama.cpp server gives every model CONTEXT_TOKENS (the preset's `c = 8192`). A longer request is refused
with "exceeds the available context size" before any answer, and every other model has the same limit, so the
vote would fail. On a busy news day BELLATOR's prompt reached 9,572 tokens. Rather than fail, background extras
are trimmed in this order until the prompt fits: archive reference passages, news citations, news items,
AETERNUM data items, older retrieved decisions, deliberation rounds older than the latest, and finally the
personal brief is shortened. The proposal, the voter's instructions, the current round and the latest
earlier round (which later rounds must answer) are never cut.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

CONTEXT_TOKENS = 8192   # Msty llama.cpp preset: c = 8192
CHARS_PER_TOKEN = 4.0   # measured 4.3 on an English vote prompt; Spanish and Catalan run lower
MARGIN_TOKENS = 300     # chat template and the execution-model line

# (path to a list, which end to drop, how many to always keep): least important first.
DROPPABLE = (
    (("memory_context", "external_reference_context", "matches"), -1, 0),
    (("bellator_context_packet", "rss_intelligence", "citations"), -1, 0),
    (("bellator_context_packet", "rss_intelligence", "items"), -1, 0),
    (("aeternum_data_packet", "items"), -1, 0),
    (("memory_context", "items"), -1, 0),
    # Later rounds answer the latest round: dropping it fails the vote ("peer round unavailable").
    (("deliberation", "previous_rounds"), 0, 1),
)
BRIEF = ("memory_context", "second_brain")
BRIEF_FLOOR = 600       # characters of the personal brief always kept


def char_budget(max_output_tokens: int, system_prompt_chars: int = 0) -> int:
    return int((CONTEXT_TOKENS - int(max_output_tokens) - MARGIN_TOKENS) * CHARS_PER_TOKEN) - int(system_prompt_chars)


def _at(context: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    value: Any = context
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _shorten_brief(context: Dict[str, Any]) -> bool:
    holder = _at(context, BRIEF[:-1])
    brief = holder.get(BRIEF[-1]) if isinstance(holder, dict) else None
    if isinstance(brief, str) and len(brief) > BRIEF_FLOOR:
        holder[BRIEF[-1]] = brief[:max(BRIEF_FLOOR, len(brief) // 2)].rstrip() + " [shortened to fit]"
        return True
    if isinstance(brief, dict):
        for key in ("summary", "text", "content", "body"):
            text = brief.get(key)
            if isinstance(text, str) and len(text) > BRIEF_FLOOR:
                brief[key] = text[:max(BRIEF_FLOOR, len(text) // 2)].rstrip() + " [shortened to fit]"
                return True
    return False


def fit_prompt(render: Callable[[Dict[str, Any]], str], context: Dict[str, Any], max_output_tokens: int,
               system_prompt_chars: int = 0) -> Tuple[str, List[str]]:
    """Render the prompt, trimming `context` in place until it fits. Returns the prompt and what was trimmed."""
    budget = char_budget(max_output_tokens, system_prompt_chars)
    prompt = render(context)
    trimmed: List[str] = []
    while len(prompt) > budget:
        for path, end, keep in DROPPABLE:
            items = _at(context, path)
            if isinstance(items, list) and len(items) > keep:
                items.pop(end)
                trimmed.append(".".join(path))
                break
        else:
            if not _shorten_brief(context):
                break  # nothing left to trim; the server will say so
            trimmed.append(".".join(BRIEF))
        prompt = render(context)
    return prompt, trimmed


__all__ = ["CONTEXT_TOKENS", "char_budget", "fit_prompt"]
