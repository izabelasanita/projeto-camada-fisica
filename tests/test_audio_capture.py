# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
"""Testes do módulo de captura de áudio.

Os testes NÃO dependem de um microfone físico: um backend falso
(`FakeInputStream`) é injetado no lugar do `sounddevice.InputStream` através
do parâmetro `stream_factory` de `AudioCapture`.
"""

from __future__ import annotations

import pytest

from camada_fisica.audio_capture import (
    AudioCapture,
    AudioCaptureConfig,
    MicrophoneUnavailableError,
    is_ready_for_reception,
)

np = pytest.importorskip("numpy")


class FakeInputStream:
    """Simula um sounddevice.InputStream, entregando blocos pré-definidos
    ao callback assim que `start()` é chamado."""

    def __init__(self, config: AudioCaptureConfig, callback, blocks=None):
        self.config = config
        self.callback = callback
        self.blocks = blocks if blocks is not None else []
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True
        for block in self.blocks:
            self.callback(block, len(block), None, None)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


def make_factory(blocks):
    def factory(config, callback):
        return FakeInputStream(config, callback, blocks=blocks)

    return factory


def test_start_and_stop_capture_returns_samples():
    blocks = [
        np.array([[0.1], [0.2], [0.3]], dtype="float32"),
        np.array([[0.4], [0.5]], dtype="float32"),
    ]
    capture = AudioCapture(stream_factory=make_factory(blocks))

    capture.start()
    assert capture.is_capturing is True

    samples = capture.stop()
    assert capture.is_capturing is False
    assert samples.shape == (5, 1)
    np.testing.assert_allclose(
        samples.flatten(), [0.1, 0.2, 0.3, 0.4, 0.5], rtol=1e-6
    )


def test_get_captured_samples_without_starting_is_empty():
    capture = AudioCapture(stream_factory=make_factory([]))
    samples = capture.get_captured_samples()
    assert len(samples) == 0


def test_set_sample_rate_before_capture():
    capture = AudioCapture(stream_factory=make_factory([]))
    capture.set_sample_rate(16_000)
    assert capture.config.sample_rate == 16_000


def test_set_sample_rate_rejects_out_of_range():
    capture = AudioCapture(stream_factory=make_factory([]))
    with pytest.raises(ValueError):
        capture.set_sample_rate(1_000)
    with pytest.raises(ValueError):
        capture.set_sample_rate(200_000)


def test_set_sample_rate_rejects_change_during_capture():
    capture = AudioCapture(stream_factory=make_factory([]))
    capture.start()
    with pytest.raises(RuntimeError):
        capture.set_sample_rate(48_000)
    capture.stop()


def test_capture_duration_matches_sample_rate():
    config = AudioCaptureConfig(sample_rate=100, channels=1)
    blocks = [np.zeros((100, 1), dtype="float32")]  # 100 amostras a 100 Hz = 1s
    capture = AudioCapture(config=config, stream_factory=make_factory(blocks))

    capture.start()
    capture.stop()

    assert capture.get_capture_duration() == pytest.approx(1.0)


def test_is_ready_for_reception_true_for_valid_signal():
    samples = np.array([[0.0], [0.5], [-0.5], [0.2]], dtype="float32")
    assert is_ready_for_reception(samples) is True


def test_is_ready_for_reception_false_for_silence():
    samples = np.zeros((10, 1), dtype="float32")
    assert is_ready_for_reception(samples) is False


def test_is_ready_for_reception_false_for_empty():
    samples = np.zeros((0, 1), dtype="float32")
    assert is_ready_for_reception(samples) is False


def test_is_ready_for_reception_false_for_nan():
    samples = np.array([[0.1], [float("nan")], [0.3]], dtype="float32")
    assert is_ready_for_reception(samples) is False


def test_check_microphone_access_raises_without_sounddevice(monkeypatch):
    import camada_fisica.audio_capture as audio_capture_module

    monkeypatch.setattr(audio_capture_module, "sd", None)
    with pytest.raises(MicrophoneUnavailableError):
        AudioCapture.check_microphone_access()


def test_start_raises_without_sounddevice_and_no_factory(monkeypatch):
    import camada_fisica.audio_capture as audio_capture_module

    monkeypatch.setattr(audio_capture_module, "sd", None)
    capture = AudioCapture()
    with pytest.raises(MicrophoneUnavailableError):
        capture.start()
