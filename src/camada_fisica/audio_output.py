# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.

from __future__ import annotations

from typing import Optional

import numpy as np

try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None


class SpeakerUnavailableError(RuntimeError):
    """Erro quando não é possível acessar a saída de áudio."""


def check_speaker_access(device: Optional[object] = None) -> dict:
    """Verifica se existe um dispositivo de saída de áudio disponível."""

    if sd is None:
        raise SpeakerUnavailableError(
            "A biblioteca 'sounddevice' não está disponível."
        )

    try:
        info = sd.query_devices(device=device, kind="output")
    except Exception as exc:
        raise SpeakerUnavailableError(
            f"Não foi possível acessar a saída de áudio: {exc}"
        ) from exc

    return {
        "name": info.get("name"),
        "max_output_channels": info.get("max_output_channels"),
        "default_samplerate": info.get("default_samplerate"),
    }


def play_audio(
    signal: np.ndarray,
    sample_rate: int,
    device: Optional[object] = None,
) -> None:
    """Reproduz um sinal acústico pelo dispositivo de saída."""

    if sd is None:
        raise SpeakerUnavailableError(
            "A biblioteca 'sounddevice' não está disponível."
        )

    signal = np.asarray(signal, dtype=np.float32)

    if signal.size == 0:
        raise ValueError("Não é possível reproduzir um sinal vazio.")

    if signal.ndim not in (1, 2):
        raise ValueError(
            "O sinal deve ser mono (1 dimensão) ou multicanal (2 dimensões)."
        )

    if sample_rate <= 0:
        raise ValueError("A taxa de amostragem deve ser positiva.")

    try:
        sd.play(
            signal,
            samplerate=sample_rate,
            device=device,
            blocking=True,
        )
    except Exception as exc:
        raise SpeakerUnavailableError(
            f"Não foi possível reproduzir o sinal: {exc}"
        ) from exc


def stop_audio() -> None:
    """Interrompe uma reprodução iniciada por play_audio()."""

    if sd is not None:
        sd.stop()