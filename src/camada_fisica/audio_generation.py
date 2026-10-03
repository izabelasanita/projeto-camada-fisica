# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.

from __future__ import annotations

import numpy as np


DEFAULT_SAMPLE_RATE = 44_100
DEFAULT_FREQUENCY = 1_000
DEFAULT_BEAT_DURATION = 0.15
DEFAULT_SILENCE_DURATION = 0.80
DEFAULT_INTER_BEAT_SILENCE = 0.30
DEFAULT_FADE_DURATION = 0.005


def _validate_bit(bit: int) -> None:
    if bit not in (0, 1):
        raise ValueError("Cada bit deve ser 0 ou 1.")


def _generate_silence(
    duration: float,
    sample_rate: int,
) -> np.ndarray:
    samples = int(round(duration * sample_rate))
    return np.zeros(samples, dtype=np.float32)


def _generate_beat(
    frequency: float,
    duration: float,
    sample_rate: int,
    fade_duration: float,
) -> np.ndarray:
    samples = int(round(duration * sample_rate))

    if samples <= 0:
        raise ValueError("A duração da batida deve ser positiva.")

    time = np.arange(samples) / sample_rate

    signal = np.sin(2 * np.pi * frequency * time)

    fade_samples = int(round(fade_duration * sample_rate))
    fade_samples = min(fade_samples, samples // 2)

    if fade_samples > 0:
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        signal[:fade_samples] *= fade_in
        signal[-fade_samples:] *= fade_out

    return signal.astype(np.float32)


def bit_to_audio(
    bit: int,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    frequency: float = DEFAULT_FREQUENCY,
    beat_duration: float = DEFAULT_BEAT_DURATION,
    silence_duration: float = DEFAULT_SILENCE_DURATION,
    inter_beat_silence: float = DEFAULT_INTER_BEAT_SILENCE,
    fade_duration: float = DEFAULT_FADE_DURATION,
) -> np.ndarray:
    """Converte um bit do Método 1 em seu sinal acústico."""

    _validate_bit(bit)

    if sample_rate <= 0:
        raise ValueError("A taxa de amostragem deve ser positiva.")

    if frequency <= 0:
        raise ValueError("A frequência deve ser positiva.")

    if beat_duration <= 0:
        raise ValueError("A duração da batida deve ser positiva.")

    if silence_duration < 0:
        raise ValueError("A duração do silêncio não pode ser negativa.")

    if inter_beat_silence < 0:
        raise ValueError(
            "O intervalo entre batidas não pode ser negativo."
        )

    silence = _generate_silence(
        silence_duration,
        sample_rate,
    )

    beat = _generate_beat(
        frequency,
        beat_duration,
        sample_rate,
        fade_duration,
    )

    parts = [
        silence,
        beat,
    ]

    if bit == 1:
        parts.append(
            _generate_silence(
                inter_beat_silence,
                sample_rate,
            )
        )
        parts.append(beat.copy())

    parts.append(silence.copy())

    return np.concatenate(parts)


def bits_to_audio(
    bits: list[int],
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    frequency: float = DEFAULT_FREQUENCY,
    beat_duration: float = DEFAULT_BEAT_DURATION,
    silence_duration: float = DEFAULT_SILENCE_DURATION,
    inter_beat_silence: float = DEFAULT_INTER_BEAT_SILENCE,
    fade_duration: float = DEFAULT_FADE_DURATION,
) -> np.ndarray:
    """Converte uma sequência de bits em um único sinal acústico."""

    if not bits:
        return np.array([], dtype=np.float32)

    signals = [
        bit_to_audio(
            bit,
            sample_rate=sample_rate,
            frequency=frequency,
            beat_duration=beat_duration,
            silence_duration=silence_duration,
            inter_beat_silence=inter_beat_silence,
            fade_duration=fade_duration,
        )
        for bit in bits
    ]

    return np.concatenate(signals)

def text_to_frame_bits(text: str) -> list[int]:
    """
    Converte um texto nos quadros do Método 1.

    Cada byte do texto gera:
        8 bits de dados + 1 bit de paridade par.

    Exemplo:
        'A' -> 01000001 + paridade
    """

    from .codec import bytes_to_bits, text_to_bytes
    from .paridade import montar_quadro

    dados = text_to_bytes(text)

    bits_transmissao = []

    for byte in dados:
        bits_dados = bytes_to_bits(bytes([byte]))
        quadro = montar_quadro(bits_dados)

        bits_transmissao.extend(quadro)

    return bits_transmissao

def text_to_audio(
    text: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    frequency: float = DEFAULT_FREQUENCY,
    beat_duration: float = DEFAULT_BEAT_DURATION,
    silence_duration: float = DEFAULT_SILENCE_DURATION,
    inter_beat_silence: float = DEFAULT_INTER_BEAT_SILENCE,
    fade_duration: float = DEFAULT_FADE_DURATION,
) -> np.ndarray:
    """
    Converte texto diretamente no sinal acústico do Método 1.

    Cada byte é transmitido como um quadro de 9 bits:
    8 bits de dados + 1 bit de paridade par.
    """

    bits = text_to_frame_bits(text)

    return bits_to_audio(
        bits,
        sample_rate=sample_rate,
        frequency=frequency,
        beat_duration=beat_duration,
        silence_duration=silence_duration,
        inter_beat_silence=inter_beat_silence,
        fade_duration=fade_duration,
    )