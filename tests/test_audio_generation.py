# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.

import pytest

np = pytest.importorskip("numpy")

from camada_fisica.audio_generation import (
    DEFAULT_BEAT_DURATION,
    DEFAULT_FREQUENCY,
    DEFAULT_INTER_BEAT_SILENCE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SILENCE_DURATION,
    bit_to_audio,
    bits_to_audio,
    text_to_audio,
    text_to_frame_bits
)


def test_bit_zero_generates_one_beat():
    signal = bit_to_audio(0)

    sample_rate = DEFAULT_SAMPLE_RATE

    silence_samples = int(
        round(DEFAULT_SILENCE_DURATION * sample_rate)
    )

    beat_samples = int(
        round(DEFAULT_BEAT_DURATION * sample_rate)
    )

    assert len(signal) == (
        silence_samples
        + beat_samples
        + silence_samples
    )


def test_bit_one_generates_two_beats():
    signal = bit_to_audio(1)

    sample_rate = DEFAULT_SAMPLE_RATE

    silence_samples = int(
        round(DEFAULT_SILENCE_DURATION * sample_rate)
    )

    beat_samples = int(
        round(DEFAULT_BEAT_DURATION * sample_rate)
    )

    inter_beat_samples = int(
        round(DEFAULT_INTER_BEAT_SILENCE * sample_rate)
    )

    assert len(signal) == (
        silence_samples
        + beat_samples
        + inter_beat_samples
        + beat_samples
        + silence_samples
    )


def test_invalid_bit_raises_error():
    with pytest.raises(ValueError):
        bit_to_audio(2)


def test_bit_zero_contains_audio():
    signal = bit_to_audio(0)

    assert np.max(np.abs(signal)) > 0


def test_bit_one_contains_audio():
    signal = bit_to_audio(1)

    assert np.max(np.abs(signal)) > 0


def test_signal_starts_and_ends_in_silence():
    signal = bit_to_audio(0)

    silence_samples = int(
        round(DEFAULT_SILENCE_DURATION * DEFAULT_SAMPLE_RATE)
    )

    assert np.all(signal[:silence_samples] == 0)
    assert np.all(signal[-silence_samples:] == 0)


def test_multiple_bits_are_concatenated():
    bits = [0, 1, 0]

    signal = bits_to_audio(bits)

    expected = sum(
        len(bit_to_audio(bit))
        for bit in bits
    )

    assert len(signal) == expected


def test_empty_sequence_returns_empty_signal():
    signal = bits_to_audio([])

    assert len(signal) == 0


def test_invalid_bit_inside_sequence_raises_error():
    with pytest.raises(ValueError):
        bits_to_audio([0, 1, 2, 0])

def test_text_to_audio_generates_signal():
    signal = text_to_audio("A")

    assert isinstance(signal, np.ndarray)
    assert signal.dtype == np.float32
    assert len(signal) > 0
    assert np.max(np.abs(signal)) > 0

def test_text_to_frame_bits_adds_parity():
    bits = text_to_frame_bits("A")

    assert len(bits) == 9

    assert bits[:8] == [
        0, 1, 0, 0,
        0, 0, 0, 1,
    ]

    assert bits[8] == 0


def test_text_to_frame_bits_multiple_bytes():
    bits = text_to_frame_bits("AB")

    assert len(bits) == 18


def test_text_to_audio_includes_parity_bit():
    bits = text_to_frame_bits("A")

    sinal_esperado = bits_to_audio(bits)
    sinal_real = text_to_audio("A")

    assert np.array_equal(
        sinal_real,
        sinal_esperado,
    )