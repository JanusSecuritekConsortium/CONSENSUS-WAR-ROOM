"""Calendar titles keep their own language in speech."""
from integrations.msty.personal import title_language as tl


def test_titles_are_classified_by_their_own_words():
    assert tl.classify('Project review') == 'en'
    assert tl.classify('Weekly sync') == 'en'
    assert tl.classify('Reunión con el proveedor') == 'es'
    assert tl.classify('Cena con Laura') == 'es'
    assert tl.classify('Dentista') == 'es'
    assert tl.classify('Laura') is None  # a name alone gives no clear signal


def test_remember_reads_unsure_titles_in_spanish_and_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(tl.store, 'ROOT', tmp_path)
    tl.remember([{'title': 'Project review'}, {'title': 'Cena con Laura'}, {'title': 'Laura'}, {'title': None}])
    assert tl.known() == {'Project review': 'en', 'Cena con Laura': 'es', 'Laura': 'es'}
    tl.remember(object())  # bad input is ignored, the calendar still loads


def test_spoken_agenda_leaves_out_the_calendar_name():
    from integrations.msty.personal import spoken_briefing as s
    text = 'Friday 13/11\n- 09:00–10:00: Project review [Proton Calendar]\n- All day: Laura [Proton Calendar]'
    spoken = s.narration(text)
    assert spoken.count('Proton Calendar') == 1 and 'Project review' in spoken and 'Laura' in spoken
    assert spoken.index('On Proton Calendar you have the following appointments') < spoken.index('Project review')
    assert s.narration('- Todo el día: Cena con Laura [Proton Calendar]', 'es').startswith('En Proton Calendar tienes las siguientes citas')
    assert 'appointments' not in s.narration('No events today.')
    assert 'Work email' in s.narration('- Attention: Invoice [Work email]')  # mail keeps its account


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


def test_catalan_titles_are_told_apart_from_spanish():
    assert tl.classify('Sopar amb la Marta') == 'ca'
    assert tl.classify('Reunió setmanal de l·lumínica') == 'ca'
    assert tl.classify('Dinar amb els proveïdors') == 'ca'
    assert tl.classify('Cena con los proveedores') == 'es'
    assert tl.classify('Reunión semanal') == 'es'
    titles = {'Sopar amb la Marta': 'ca'}
    assert tl.segments('Hoy tienes Sopar amb la Marta.', 'es', titles) == [('Hoy tienes ', 'es'), ('Sopar amb la Marta.', 'ca')]


def _fake_render(tmp_path, monkeypatch, catalan_voices):
    from integrations.msty.personal import spoken_briefing as s
    from voice import aurelius_adapter
    monkeypatch.setattr(s.store, 'ROOT', tmp_path)
    monkeypatch.setattr(tl, 'known', lambda: {'Sopar amb la Marta': 'ca'})
    monkeypatch.setattr(s, 'spanish_settings', lambda settings: {**settings, 'base_voice_name': ['Microsoft Pablo']})
    monkeypatch.setattr(s, 'installed_voices', lambda code: list(catalan_voices) if code == '403' else [])
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

    monkeypatch.setattr(aurelius_adapter.AureliusAdapter, 'save_only', save_only)
    monkeypatch.setattr(s.shutil, 'which', lambda name: 'ffmpeg')
    monkeypatch.setattr(s.subprocess, 'run', lambda command, **kw: __import__('pathlib').Path(command[-1]).write_bytes(b'OggS'))
    with s.audio_file('Hoy tienes Sopar amb la Marta.', 'es'):
        pass
    return spoken


def test_catalan_titles_use_a_catalan_voice_when_windows_has_one(tmp_path, monkeypatch):
    spoken = _fake_render(tmp_path, monkeypatch, ['Microsoft Herena'])
    assert [voice for _, voice in spoken] == ['Microsoft Pablo', 'Microsoft Herena']


def test_catalan_titles_stay_spanish_without_a_catalan_voice(tmp_path, monkeypatch):
    spoken = _fake_render(tmp_path, monkeypatch, [])
    assert len(spoken) == 1 and spoken[0][1] == 'Microsoft Pablo' and 'Sopar amb la Marta' in spoken[0][0]


def test_catalan_settings_keep_the_aurelius_shape():
    from integrations.msty.personal import spoken_briefing as s
    settings = s.catalan_settings({'transpose': 2, 'catalan': {'transpose': 0, 'protect': 0.5}}, voices=['Microsoft Herena'])
    assert settings['base_voice_name'] == ['Microsoft Herena'] and settings['transpose'] == 0
    assert settings['speech_language'] == 'ca'
