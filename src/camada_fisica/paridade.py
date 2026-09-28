def calcular_paridade(bits):
    """
    Calcula o bit de paridade par para 8 bits de dados.

    Se a quantidade de 1 for par, a paridade será 0.
    Se a quantidade de 1 for ímpar, a paridade será 1.
    """

    if len(bits) != 8:
        raise ValueError("Devem ser fornecidos exatamente 8 bits.")

    quantidade_uns = sum(bits)

    return quantidade_uns % 2


def montar_quadro(bits):
    """
    Monta um quadro de 9 bits:
    8 bits de dados + 1 bit de paridade.
    """

    paridade = calcular_paridade(bits)

    quadro = bits + [paridade]

    return quadro


def validar_paridade(quadro):
    """
    Verifica se um quadro de 9 bits possui a paridade correta.

    Retorna True se o quadro for válido.
    Retorna False se o quadro estiver corrompido.
    """

    if len(quadro) != 9:
        raise ValueError("O quadro deve possuir exatamente 9 bits.")

    dados = quadro[:8]
    paridade_recebida = quadro[8]

    paridade_esperada = calcular_paridade(dados)

    return paridade_recebida == paridade_esperada


def identificar_quadro(quadro):
    """
    Identifica se o quadro recebido é válido ou corrompido.
    """

    if validar_paridade(quadro):
        return "QUADRO VÁLIDO"

    return "QUADRO CORROMPIDO"