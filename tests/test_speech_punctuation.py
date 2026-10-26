"""Spoken punctuation must not lose qualifiers, time ranges or negative values."""
from unittest.mock import Mock

import pytest

from voice.aurelius_adapter import AureliusAdapter
from voice.rvc_adapter import RVCAdapter
from voice.text_normalization import normalize_for_speech, prepare_speech_text, split_speech_text
from voice.tts_backends import TTSBackendResult


@pytest.mark.parametrize('dash', ['-', '–', '—'])
def test_prose_dashes_are_pauses(dash):
    assert normalize_for_speech('Possible change '+dash+' not confirmed.') == 'Possible change, not confirmed.'


def test_visual_formatting_does_not_run_items_together():
    text = '## Status\n---\n- **Possible** conflict (unverified)\n2. [Source](https://example.com) · `Follow-up` required.'
    assert prepare_speech_text(text) == 'Status. Possible conflict, unverified. Source, Follow up required.'


def test_symbols_with_numeric_meaning_survive():
    text = 'Window 09:00–10:30: review. Confidence 5–10%. Temperature -3.5 degrees. Difference 8 − 3.'
    assert normalize_for_speech(text) == (
        "Window nine o'clock to ten thirty: review. Confidence five to ten percent. "
        'Temperature minus three point five degrees. Difference eight minus three.'
    )


@pytest.mark.parametrize('ending', ['.', ': review.', ''])
def test_time_range_at_sentence_boundary(ending):
    assert normalize_for_speech('09:00–10:30'+ending) == "nine o'clock to ten thirty"+ending


def test_normalization_is_stable_across_adapter_and_chunking():
    text = '# Report\n- **Possible** conflict — not confirmed.\n- Check at 09:00–10:30.\n- Discuss the word slash.'
    normalized = normalize_for_speech(text)
    assert normalize_for_speech(normalized) == normalized
    assert ' '.join(split_speech_text(normalized, max_chars=80)) == normalized
    assert 'the word slash' in normalized


def test_numeric_fraction_keeps_its_meaning_without_saying_slash():
    assert normalize_for_speech('Use 1/2 of the amount.') == 'Use one over two of the amount.'


@pytest.mark.parametrize('operation', ['speak', 'synthesize', 'save_only'])
@pytest.mark.parametrize('backend', ['rvc', 'windows_sapi'])
def test_aurelius_normalizes_before_each_backend(operation, backend, tmp_path):
    adapter = AureliusAdapter.__new__(AureliusAdapter)
    adapter.profile = Mock(backend=backend, settings={'output_dir': str(tmp_path)})
    adapter.backend = Mock()
    getattr(adapter, operation)('- **Possible** change — not confirmed.')
    method = 'synthesize_to_wav' if operation == 'save_only' and backend != 'rvc' else operation
    assert getattr(adapter.backend, method).call_args.args[0] == 'Possible change, not confirmed.'


def test_rvc_failure_does_not_restore_raw_formatting():
    adapter = RVCAdapter.__new__(RVCAdapter)
    adapter.settings = {}
    adapter.convert_text = Mock(return_value=TTSBackendResult(ok=False, metadata={'error': 'unavailable'}))
    adapter.base_tts = Mock()
    adapter.base_tts.speak.return_value = TTSBackendResult(ok=True)
    assert adapter.speak('- **Possible** change — not confirmed.').ok
    adapter.base_tts.speak.assert_called_once_with('Possible change, not confirmed.')
