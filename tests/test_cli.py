from camada_fisica.cli import build_parser, main


def test_parser_accepts_check():
    assert build_parser().parse_args(["--check"]).check is True


def test_check_command(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["camada-fisica", "--check"])
    assert main() == 0
    assert "ambiente básico OK" in capsys.readouterr().out
