# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.

from camada_fisica.cli import build_parser, main


def test_parser_accepts_check():
    assert build_parser().parse_args(["--check"]).check is True


def test_check_command(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["camada-fisica", "--check"])
    assert main() == 0
    assert "ambiente básico OK" in capsys.readouterr().out


def test_parser_accepts_test_mic_options():
    args = build_parser().parse_args(
        ["--test-mic", "--duration", "1.5", "--sample-rate", "16000"]
    )
    assert args.test_mic is True
    assert args.duration == 1.5
    assert args.sample_rate == 16000


def test_parser_accepts_metodo1():
    args = build_parser().parse_args(["--metodo1", "--sample-rate", "22050"])
    assert args.metodo1 is True
    assert args.sample_rate == 22050
