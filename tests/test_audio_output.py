import pytest

np = pytest.importorskip("numpy")

import camada_fisica.audio_output as audio_output
from camada_fisica.audio_output import (
    SpeakerUnavailableError,
    check_speaker_access,
    play_audio,
)


def test_play_audio_sends_signal_to_sounddevice(monkeypatch):
    signal = np.array([0.0, 0.5, -0.5], dtype=np.float32)

    calls = {}

    def fake_play(data, samplerate, device, blocking):
        calls["data"] = data
        calls["samplerate"] = samplerate
        calls["device"] = device
        calls["blocking"] = blocking

    monkeypatch.setattr(audio_output.sd, "play", fake_play)

    play_audio(signal, 44_100)

    np.testing.assert_array_equal(calls["data"], signal)
    assert calls["samplerate"] == 44_100
    assert calls["device"] is None
    assert calls["blocking"] is True


def test_play_audio_rejects_empty_signal():
    with pytest.raises(ValueError):
        play_audio(np.array([], dtype=np.float32), 44_100)


def test_play_audio_rejects_invalid_sample_rate():
    signal = np.array([0.0, 0.5], dtype=np.float32)

    with pytest.raises(ValueError):
        play_audio(signal, 0)


def test_play_audio_rejects_invalid_dimensions():
    signal = np.zeros((2, 2, 2), dtype=np.float32)

    with pytest.raises(ValueError):
        play_audio(signal, 44_100)


def test_check_speaker_access(monkeypatch):
    expected = {
        "name": "Fake Speaker",
        "max_output_channels": 2,
        "default_samplerate": 44_100,
    }

    def fake_query_devices(device=None, kind=None):
        assert kind == "output"
        return expected

    monkeypatch.setattr(
        audio_output.sd,
        "query_devices",
        fake_query_devices,
    )

    info = check_speaker_access()

    assert info == expected


def test_play_audio_raises_when_sounddevice_unavailable(monkeypatch):
    monkeypatch.setattr(audio_output, "sd", None)

    signal = np.array([0.0, 0.5], dtype=np.float32)

    with pytest.raises(SpeakerUnavailableError):
        play_audio(signal, 44_100)