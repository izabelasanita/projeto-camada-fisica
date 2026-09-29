"""Interface de linha de comando para verificar a instalação local."""

from __future__ import annotations

import argparse

from . import __version__
from .audio_capture import (
    DEFAULT_SAMPLE_RATE,
    AudioCapture,
    MicrophoneUnavailableError,
    is_ready_for_reception,
)

from .audio_generation import text_to_audio

from .audio_output import (
    SpeakerUnavailableError,
    check_speaker_access,
    play_audio,
)

from .metodo1 import decodificar_metodo1, formatar_resultado


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="camada-fisica",
        description="Software de comunicação digital por ondas sonoras.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--check", action="store_true", help="verifica a instalação")
    parser.add_argument(
        "--test-mic",
        action="store_true",
        help="grava alguns segundos de áudio do microfone e mostra estatísticas",
    )
    parser.add_argument(
        "--metodo1",
        action="store_true",
        help="recepção do Método 1: captura as batidas até ENTER e decodifica",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="duração em segundos da gravação de teste (padrão: 3.0)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"taxa de amostragem em Hz (padrão: {DEFAULT_SAMPLE_RATE})",
    )
    parser.add_argument(
    "--send",
    metavar="TEXTO",
    help="transmite um texto pelo alto-falante usando o Método 1",
    )
    return parser


def _run_test_mic(duration: float, sample_rate: int) -> int:
    capture = AudioCapture()
    try:
        capture.set_sample_rate(sample_rate)
        info = AudioCapture.check_microphone_access()
    except MicrophoneUnavailableError as exc:
        print(f"[ERRO] {exc}")
        return 1
    except ValueError as exc:
        print(f"[ERRO] {exc}")
        return 1

    print(f"Microfone detectado: {info['name']}")
    print(f"Gravando por {duration:.1f}s a {sample_rate} Hz... fale ou bata palmas.")
    samples = capture.capture_for(duration)
    n_samples = len(samples)
    real_duration = capture.get_capture_duration()

    print(f"Amostras capturadas: {n_samples}")
    print(f"Duração efetiva da captura: {real_duration:.2f}s")

    if is_ready_for_reception(samples):
        print("[SUCESSO] Dados prontos para os módulos de recepção.")
        return 0

    print("[FALHA DE CAPTURA] Nenhum sinal de áudio válido foi detectado.")
    return 1


def _run_metodo1(sample_rate: int) -> int:
    capture = AudioCapture()
    try:
        capture.set_sample_rate(sample_rate)
        info = AudioCapture.check_microphone_access()
        print(f"Microfone detectado: {info['name']}")
        capture.start()
    except (MicrophoneUnavailableError, ValueError) as exc:
        print(f"[ERRO] {exc}")
        return 1

    input("Gravando... faça as batidas do Método 1 e pressione ENTER para encerrar.")
    samples = capture.stop()

    if not is_ready_for_reception(samples):
        print("[FALHA DE CAPTURA] Nenhum sinal de áudio válido foi detectado.")
        return 1

    resultado = decodificar_metodo1(samples, sample_rate)
    print(formatar_resultado(resultado))
    return 0 if resultado.todos_validos else 1


def _run_send(text: str, sample_rate: int) -> int:
    try:
        info = check_speaker_access()

        print(f"Alto-falante detectado: {info['name']}")
        print(f"Transmitindo: {text!r}")

        signal = text_to_audio(
            text,
            sample_rate=sample_rate,
        )

        print(f"Bits transmitidos: {len(text.encode('utf-8')) * 8}")
        print(f"Amostras geradas: {len(signal)}")

        play_audio(
            signal,
            sample_rate=sample_rate,
        )

        print("[SUCESSO] Transmissão concluída.")
        return 0

    except (SpeakerUnavailableError, ValueError) as exc:
        print(f"[ERRO] {exc}")
        return 1
    

def main() -> int:
    args = build_parser().parse_args()

    if args.metodo1:
        return _run_metodo1(args.sample_rate)

    if args.send is not None:
        return _run_send(args.send, args.sample_rate)

    if args.test_mic:
        return _run_test_mic(args.duration, args.sample_rate)

    if args.check:
        print(f"camada-fisica {__version__}: ambiente básico OK")
    else:
        build_parser().print_help()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
