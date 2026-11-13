"""Calendar titles keep their own language in speech."""
from integrations.msty.personal import title_language as tl


def test_titles_are_classified_by_their_own_words():
    assert tl.classify('Project review') == 'en'
    assert tl.classify('Weekly sync') == 'en'
    assert tl.classify('Reunión con el proveedor') == 'es'
    assert tl.classify('Cena con Laura') == 'es'
    assert tl.classify('Dentista') == 'es'
    assert tl.classify('Laura') is None  # a name alone keeps the reply's voice


def test_remember_keeps_only_clear_titles_and_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(tl.store, 'ROOT', tmp_path)
    tl.remember([{'title': 'Project review'}, {'title': 'Cena con Laura'}, {'title': 'Laura'}, {'title': None}])
    assert tl.known() == {'Project review': 'en', 'Cena con Laura': 'es'}
    tl.remember(object())  # bad input is ignored, the calendar still loads


def test_other_language_titles_get_their_own_part():
    titles = {'Project review': 'en', 'Weekly sync': 'en', 'Cena con Laura': 'es'}
    assert tl.segments('Hoy tienes Project review, y luego Weekly sync.', 'es', titles) == [
        ('Hoy tienes ', 'es'), ('Project review', 'en'), (', y luego ', 'es'), ('Weekly sync.', 'en')]
    assert tl.segments('At 8 pm, cena con laura.', 'en', titles) == [('At 8 pm, ', 'en'), ('cena con laura.', 'es')]
    assert tl.segments('Nada en inglés hoy.', 'es', titles) == [('Nada en inglés hoy.', 'es')]
    assert tl.segments('Weekly syncing later', 'es', titles) == [('Weekly syncing later', 'es')]  # whole words only


def test_voice_note_uses_each_parts_voice(tmp_path, monkeypatch):
    from integrations.msty.personal import spoken_briefing as s
    from voice import aurelius_adapter
    monkeypatch.setattr(s.store, 'ROOT', tmp_path)
    monkeypatch.setattr(tl, 'known', lambda: {'Project review': 'en'})
    monkeypatch.setattr(s, 'spanish_settings', lambda settings: {**settings, 'base_voice_name': ['Microsoft Pablo']})
    spoken = []

    class Result:
        ok = True

        def __init__(self, path):
            self.audio_path = path

    def save_only(self, text):
        spoken.append((text, self.profile.settings['base_voice_name'][0]))
        path = tmp_path/f'{len(spoken)}.wav'
        path.write_bytes(b'RIFF')
        return Result(str(path))

    commands = []
    monkeypatch.setattr(aurelius_adapter.AureliusAdapter, 'save_only', save_only)
    monkeypatch.setattr(s.shutil, 'which', lambda name: 'ffmpeg')
    monkeypatch.setattr(s.subprocess, 'run', lambda command, **kw: commands.append(command) or
                        __import__('pathlib').Path(command[-1]).write_bytes(b'OggS'))
    with s.audio_file('Hoy tienes Project review.', 'es') as path:
        assert path.read_bytes() == b'OggS'
    assert len(spoken) == 2
    assert spoken[0] == ('Hoy tienes ', 'Microsoft Pablo')
    assert spoken[1][0].startswith('Project review') and spoken[1][1] != 'Microsoft Pablo'
    assert commands[0].count('-i') == len(spoken) and 'concat=n=%d' % len(spoken) in ' '.join(commands[0])
