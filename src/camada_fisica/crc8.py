CRC8_POLYNOMIAL = 0x07
CRC8_INITIAL_VALUE = 0x00


def calcular_crc8(dados: bytes) -> int:
    """
    Calcula o CRC-8/SMBUS dos dados recebidos.

    Retorna um valor inteiro entre 0 e 255,
    correspondente a 1 byte de CRC.
    """

    crc = CRC8_INITIAL_VALUE

    for byte in dados:
        crc ^= byte

        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ CRC8_POLYNOMIAL) & 0xFF
            else:
                crc = (crc << 1) & 0xFF

    return crc


def montar_quadro(dados: bytes) -> bytes:
    """
    Monta um quadro adicionando o CRC-8 ao final dos dados.

    Formato:
        [dados] [CRC-8]
    """

    if not dados:
        raise ValueError("Os dados não podem estar vazios.")

    crc = calcular_crc8(dados)

    return dados + bytes([crc])


def validar_crc8(quadro: bytes) -> bool:
    """
    Verifica se o CRC-8 presente no quadro corresponde
    aos dados recebidos.

    Retorna True para um quadro válido.
    Retorna False para um quadro corrompido.
    """

    if len(quadro) < 2:
        raise ValueError(
            "O quadro deve possuir pelo menos 1 byte de dados e 1 byte de CRC."
        )

    dados = quadro[:-1]
    crc_recebido = quadro[-1]

    crc_esperado = calcular_crc8(dados)

    return crc_recebido == crc_esperado


def identificar_quadro(quadro: bytes) -> str:
    """
    Identifica se o quadro recebido é válido ou corrompido.
    """

    if validar_crc8(quadro):
        return "QUADRO VÁLIDO"

    return "QUADRO CORROMPIDO"