from camada_fisica.crc8 import (
    calcular_crc8,
    montar_quadro,
    validar_crc8,
    identificar_quadro,
)


def test_crc8_dados_vazios():
    crc = calcular_crc8(b"")

    assert crc == 0x00


def test_crc8_valor_conhecido():
    dados = b"123456789"
    crc = calcular_crc8(dados)

    assert crc == 0xF4


def test_montar_quadro():
    dados = b"ABC"
    quadro = montar_quadro(dados)

    assert quadro[:-1] == dados
    assert quadro[-1] == calcular_crc8(dados)


def test_quadro_valido():
    dados = b"Mensagem de teste"
    quadro = montar_quadro(dados)

    assert validar_crc8(quadro) is True


def test_quadro_corrompido():
    dados = b"Mensagem de teste"
    quadro = bytearray(montar_quadro(dados))

    quadro[0] ^= 1

    assert validar_crc8(bytes(quadro)) is False


def test_crc_corrompido():
    dados = b"Mensagem de teste"
    quadro = bytearray(montar_quadro(dados))

    quadro[-1] ^= 1

    assert validar_crc8(bytes(quadro)) is False


def test_identificar_quadro_valido():
    dados = b"Teste"
    quadro = montar_quadro(dados)

    assert identificar_quadro(quadro) == "QUADRO VÁLIDO"


def test_identificar_quadro_corrompido():
    dados = b"Teste"
    quadro = bytearray(montar_quadro(dados))

    quadro[1] ^= 1

    assert identificar_quadro(bytes(quadro)) == "QUADRO CORROMPIDO"


def test_quadro_vazio():
    try:
        validar_crc8(b"")
        assert False
    except ValueError:
        assert True


def test_quadro_sem_dados():
    try:
        validar_crc8(b"A")
        assert False
    except ValueError:
        assert True