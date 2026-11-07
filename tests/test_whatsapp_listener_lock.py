import pytest

from integrations.attention import whatsapp


def test_listener_lock_is_held_and_released(tmp_path, monkeypatch):
    monkeypatch.setattr(whatsapp, 'FOLDER', tmp_path)
    monkeypatch.setattr(whatsapp, 'LOCK', tmp_path / 'listener.lock')
    with whatsapp.SingleInstance() as held:
        assert not held.handle.closed
    assert held.handle.closed
    with whatsapp.SingleInstance():   # free again after release
        pass


def test_a_held_lock_is_reported_as_another_listener(tmp_path, monkeypatch):
    monkeypatch.setattr(whatsapp, 'FOLDER', tmp_path)
    monkeypatch.setattr(whatsapp, 'LOCK', tmp_path / 'listener.lock')

    def busy(handle):
        raise OSError('locked')

    monkeypatch.setattr(whatsapp, '_lock_without_waiting', busy)
    with pytest.raises(RuntimeError, match='already running'):
        with whatsapp.SingleInstance():
            pass
