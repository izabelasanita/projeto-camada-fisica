# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.
"""Captura de áudio pelo microfone (front-end da Camada Física - Recepção).

Este módulo é responsável por conceder acesso ao microfone do dispositivo e
capturar as amostras de áudio brutas que, em seguida, serão entregues aos
módulos de recepção (decodificação do Método 1 - batidas, e do Método 2 -
modulação livre) para extração dos bits transmitidos.

O acesso ao hardware é feito através da biblioteca `sounddevice` (que por sua
vez usa PortAudio). Para permitir testes automatizados sem depender de um
microfone físico, a classe `AudioCapture` aceita a injeção de uma
`stream_factory` alternativa, que substitui a criação do `sounddevice.InputStream`
por qualquer objeto compatível (ver `tests/test_audio_capture.py`).
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

try:  # numpy é uma dependência opcional (extra "audio")
    import numpy as np
except ImportError:  # pragma: no cover - ambiente sem o extra "audio"
    np = None  # type: ignore[assignment]

try:  # sounddevice é uma dependência opcional (extra "audio")
    import sounddevice as sd
except (ImportError, OSError):
    # ImportError: pacote não instalado (falta o extra "audio").
    # OSError: pacote instalado, mas a biblioteca nativa PortAudio não foi
    # encontrada no sistema operacional (ex.: ambiente sem placa de som).
    sd = None  # type: ignore[assignment]


DEFAULT_SAMPLE_RATE = 44_100
"""Taxa de amostragem inicial (Hz). 44.1 kHz é o padrão de áudio (CD-quality)
e garante margem confortável acima do limite de Nyquist para as frequências
sonoras utilizadas pelos Métodos 1 e 2 (impacto/batidas e tons até poucos
kHz)."""

DEFAULT_CHANNELS = 1
DEFAULT_BLOCK_SIZE = 1024
DEFAULT_DTYPE = "float32"

# Faixa aceitável de taxas de amostragem para a atividade.
MIN_SAMPLE_RATE = 8_000
MAX_SAMPLE_RATE = 96_000


class MicrophoneUnavailableError(RuntimeError):
    """Erro levantado quando o microfone ou suas dependências não estão
    disponíveis (biblioteca não instalada, sem dispositivo de entrada, sem
    permissão do sistema operacional, etc.)."""


@dataclass
class AudioCaptureConfig:
    """Parâmetros de configuração da captura de áudio."""

    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS
    block_size: int = DEFAULT_BLOCK_SIZE
    dtype: str = DEFAULT_DTYPE
    device: Optional[object] = None  # índice ou nome do dispositivo (sounddevice)


class AudioCapture:
    """Gerencia o ciclo de vida da captura de áudio pelo microfone.

    Uso típico::

        capture = AudioCapture()
        capture.start()
        ...  # aguarda o usuário emitir os sinais sonoros
        amostras = capture.stop()

    As amostras retornadas por :meth:`stop` (ou a qualquer momento por
    :meth:`get_captured_samples`) ficam disponíveis para os módulos de
    recepção (detecção de batidas do Método 1 e demodulação do Método 2).
    """

    def __init__(
        self,
        config: Optional[AudioCaptureConfig] = None,
        stream_factory: Optional[Callable[[AudioCaptureConfig, Callable], object]] = None,
    ) -> None:
        self.config = config or AudioCaptureConfig()
        self._stream_factory = stream_factory
        self._stream = None
        self._frames: list = []
        self._lock = threading.Lock()
        self._is_capturing = False
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Configuração / verificação de acesso ao microfone
    # ------------------------------------------------------------------
    @staticmethod
    def check_microphone_access(device: Optional[object] = None) -> dict:
        """Verifica se um microfone (dispositivo de entrada) está acessível.

        Retorna um dicionário com informações do dispositivo padrão de
        entrada. Levanta :class:`MicrophoneUnavailableError` se a biblioteca
        de áudio não estiver instalada ou se nenhum dispositivo de entrada
        puder ser aberto (ex.: permissão negada pelo sistema operacional).
        """
        if sd is None:
            raise MicrophoneUnavailableError(
                "A biblioteca 'sounddevice' não está instalada. "
                "Instale as dependências de áudio com: pip install -e '.[audio]'"
            )
        try:
            info = sd.query_devices(device=device, kind="input")
        except Exception as exc:  # pragma: no cover - depende do hardware/SO
            raise MicrophoneUnavailableError(
                f"Não foi possível acessar o microfone: {exc}"
            ) from exc

        return {
            "name": info.get("name"),
            "max_input_channels": info.get("max_input_channels"),
            "default_samplerate": info.get("default_samplerate"),
        }

    def set_sample_rate(self, sample_rate: int) -> None:
        """Define a taxa de amostragem antes do início da captura.

        Levanta ``ValueError`` se o valor estiver fora da faixa aceitável ou
        ``RuntimeError`` se chamado durante uma captura em andamento.
        """
        if self._is_capturing:
            raise RuntimeError(
                "Não é possível alterar a taxa de amostragem durante a captura."
            )
        if not (MIN_SAMPLE_RATE <= sample_rate <= MAX_SAMPLE_RATE):
            raise ValueError(
                "A taxa de amostragem deve estar entre "
                f"{MIN_SAMPLE_RATE} Hz e {MAX_SAMPLE_RATE} Hz "
                f"(recebido: {sample_rate} Hz)."
            )
        self.config.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Início / encerramento da captura
    # ------------------------------------------------------------------
    def _callback(self, indata, frames, time_info, status):  # noqa: D401
        """Callback invocado pelo backend de áudio a cada bloco capturado."""
        with self._lock:
            if np is not None:
                self._frames.append(indata.copy())
            else:  # pragma: no cover - fallback sem numpy
                self._frames.append(list(indata))

    def start(self) -> None:
        """Concede acesso ao microfone e inicia a captura de amostras."""
        if self._is_capturing:
            return

        with self._lock:
            self._frames = []
        self._stopped_at = None

        if self._stream_factory is not None:
            self._stream = self._stream_factory(self.config, self._callback)
        else:
            if sd is None:
                raise MicrophoneUnavailableError(
                    "A biblioteca 'sounddevice' não está instalada. "
                    "Instale as dependências de áudio com: pip install -e '.[audio]'"
                )
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                blocksize=self.config.block_size,
                dtype=self.config.dtype,
                device=self.config.device,
                callback=self._callback,
            )

        self._stream.start()
        self._is_capturing = True
        self._started_at = time.monotonic()

    def stop(self):
        """Encerra a captura e retorna todas as amostras capturadas."""
        if self._is_capturing:
            self._stream.stop()
            self._stream.close()
            self._is_capturing = False
            self._stopped_at = time.monotonic()
        return self.get_captured_samples()

    def capture_for(self, duration_seconds: float):
        """Captura áudio por um período fixo (bloqueante) e retorna as amostras.

        Conveniente para testes manuais rápidos via CLI (`--test-mic`).
        """
        self.start()
        time.sleep(duration_seconds)
        return self.stop()

    # ------------------------------------------------------------------
    # Acesso aos dados capturados
    # ------------------------------------------------------------------
    def get_captured_samples(self):
        """Retorna as amostras capturadas até o momento, concatenadas.

        O formato é um array numpy de forma ``(n_amostras, canais)`` quando
        numpy está disponível, ou uma lista simples de amostras caso
        contrário.
        """
        with self._lock:
            frames = list(self._frames)

        if np is not None:
            if not frames:
                return np.zeros((0, self.config.channels), dtype=self.config.dtype)
            return np.concatenate(frames, axis=0)

        # Fallback sem numpy: achata manualmente os blocos capturados.
        flat: list = []
        for frame in frames:
            flat.extend(frame)
        return flat

    def get_capture_duration(self) -> float:
        """Duração (em segundos) da última captura realizada."""
        samples = self.get_captured_samples()
        n_samples = len(samples)
        if n_samples == 0 or self.config.sample_rate == 0:
            return 0.0
        return n_samples / self.config.sample_rate

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing


# ----------------------------------------------------------------------
# Validação para consumo pelos módulos de recepção
# ----------------------------------------------------------------------
def is_ready_for_reception(samples, min_samples: int = 1) -> bool:
    """Verifica se os dados capturados estão em condições de serem
    utilizados pelos módulos de recepção (Método 1 e Método 2).

    Critérios verificados:
        * há pelo menos ``min_samples`` amostras capturadas;
        * não há valores ``NaN``/``inf`` (o que indicaria falha do backend
          de áudio);
        * o sinal não é completamente silencioso (todas as amostras zero),
          o que normalmente indica que o microfone não captou nada.
    """
    n_samples = len(samples)
    if n_samples < min_samples:
        return False

    if np is not None:
        array = np.asarray(samples)
        if array.size == 0:
            return False
        if not np.all(np.isfinite(array)):
            return False
        if not np.any(array):
            return False
        return True

    # Fallback sem numpy.
    flat = list(samples)
    if not flat:
        return False
    if any((v != v) for v in flat):  # detecta NaN sem depender de math
        return False
    return any(v != 0 for v in flat)
