# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.

import numpy as np

# Configurações padrão do Método 2
FREQUENCIA_0 = 1000
FREQUENCIA_1 = 2000
DURACAO_SIMBOLO = 0.1
TAXA_AMOSTRAGEM = 44100
AMPLITUDE = 0.5

def validar_bits(bits):
    """
    Verifica se a sequência contém apenas bits 0 e 1.
    """

    if not all(bit in (0, 1) for bit in bits):
        raise ValueError("A sequência deve conter apenas bits 0 e 1.")


def gerar_sinal_frequencia(
    frequencia,
    duracao,
    taxa_amostragem,
    amplitude,
    fase_inicial=0.0,
):
    """
    Gera uma onda senoidal com a frequência e duração informadas.

    A fase inicial pode ser utilizada para manter a continuidade
    entre diferentes símbolos.
    """

    quantidade_amostras = int(duracao * taxa_amostragem)

    tempo = np.arange(quantidade_amostras) / taxa_amostragem

    fase = (
        2 * np.pi * frequencia * tempo
        + fase_inicial
    )

    sinal = amplitude * np.sin(fase)

    fase_final = (
        fase_inicial
        + 2 * np.pi * frequencia
        * quantidade_amostras
        / taxa_amostragem
    ) % (2 * np.pi)

    return sinal, fase_final


def _gerar_bit_2fsk_com_fase(
    bit,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
    duracao=DURACAO_SIMBOLO,
    taxa_amostragem=TAXA_AMOSTRAGEM,
    amplitude=AMPLITUDE,
    fase_inicial=0.0,
):
    """
    Gera o sinal correspondente a um bit 2-FSK
    e retorna também a fase final do sinal.

    Bit 0 → frequência_0
    Bit 1 → frequência_1
    """

    if bit not in (0, 1):
        raise ValueError("O bit deve ser 0 ou 1.")

    if frequencia_0 <= 0 or frequencia_1 <= 0:
        raise ValueError(
            "As frequências devem ser maiores que zero."
        )

    if duracao <= 0:
        raise ValueError(
            "A duração do símbolo deve ser maior que zero."
        )

    if taxa_amostragem <= 0:
        raise ValueError(
            "A taxa de amostragem deve ser maior que zero."
        )

    if not 0 <= amplitude <= 1:
        raise ValueError(
            "A amplitude deve estar entre 0 e 1."
        )

    if bit == 0:
        frequencia = frequencia_0
    else:
        frequencia = frequencia_1

    return gerar_sinal_frequencia(
        frequencia,
        duracao,
        taxa_amostragem,
        amplitude,
        fase_inicial,
    )


def gerar_bit_2fsk(
    bit,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
    duracao=DURACAO_SIMBOLO,
    taxa_amostragem=TAXA_AMOSTRAGEM,
    amplitude=AMPLITUDE,
):
    """
    Converte um bit em seu respectivo sinal 2-FSK.

    Bit 0 → frequência_0
    Bit 1 → frequência_1

    Retorna somente o sinal de áudio.
    """

    sinal, _ = _gerar_bit_2fsk_com_fase(
        bit,
        frequencia_0,
        frequencia_1,
        duracao,
        taxa_amostragem,
        amplitude,
        0.0,
    )

    return sinal

def gerar_sinal_2fsk(
    bits,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
    duracao=DURACAO_SIMBOLO,
    taxa_amostragem=TAXA_AMOSTRAGEM,
    amplitude=AMPLITUDE,
):
    """
    Converte uma sequência de bits em um sinal de áudio 2-FSK.

    A fase é mantida entre os símbolos para reduzir
    descontinuidades no sinal.
    """

    validar_bits(bits)

    sinais = []
    fase = 0.0

    for bit in bits:

        sinal, fase = _gerar_bit_2fsk_com_fase(
            bit,
            frequencia_0,
            frequencia_1,
            duracao,
            taxa_amostragem,
            amplitude,
            fase,
        )

        sinais.append(sinal)

    if not sinais:
        return np.array([], dtype=float)

    return np.concatenate(sinais)