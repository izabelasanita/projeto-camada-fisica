"""Interface de linha de comando para verificar a instalação local."""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="camada-fisica",
        description="Software de comunicação digital por ondas sonoras.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--check", action="store_true", help="verifica a instalação")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.check:
        print(f"camada-fisica {__version__}: ambiente básico OK")
    else:
        build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
