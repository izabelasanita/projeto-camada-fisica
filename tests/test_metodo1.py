# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
"""Testes da recepção do Método 1 (batidas -> bits -> paridade).

Usam sinais sintéticos (silêncio + ruído fraco + "batidas" curtas), portanto
não dependem de microfone.
"""

import numpy as np

from camada_fisica.codec import bytes_to_bits
from camada_fisica.metodo1 import (
    STATUS_FALHA,
    STATUS_SUCESSO,
    ReceptorMetodo1TempoReal,
    agrupar_batidas,
    avaliar_quadro,
    decodificar_metodo1,
    detectar_batidas,
    formatar_resultado,
    grupos_para_bits,
    montar_quadros,
)
from camada_fisica.paridade import montar_quadro

SR = 44_100
GAP_INTRA = 0.25  # entre as 2 batidas do bit 1
GAP_BIT = 1.0  # silêncio entre bits


def gerar_batida(sr=SR, dur=0.03, amp=0.8, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    return amp * rng.uniform(-1, 1, n) * np.exp(-np.linspace(0, 6, n))


def gerar_sinal(bits, sr=SR, ruido=0.005, inicio=0.5, extras=None):
    """Gera áudio com o padrão do Método 1 para a lista de bits."""
    instantes = []
    t = inicio
    for b in bits:
        instantes.append(t)
        if b == 1:
            instantes.append(t + GAP_INTRA)
            t += GAP_INTRA
        t += GAP_BIT
    if extras:
        instantes += extras
    total = int((max(instantes) + 1.0) * sr)
    rng = np.random.default_rng(42)
    sinal = ruido * rng.standard_normal(total)
    batida = gerar_batida(sr)
    for ti in instantes:
        i = int(ti * sr)
        sinal[i : i + len(batida)] += batida
    return sinal.astype("float32").reshape(-1, 1)


def test_detecta_batidas_nos_instantes_corretos():
    sinal = gerar_sinal([0, 1])  # batidas em 0.5 | 1.5 e 1.75
    tempos = detectar_batidas(sinal, SR)
    assert len(tempos) == 3
    esperados = [0.5, 1.5, 1.75]
    for t, e in zip(tempos, esperados):
        assert abs(t - e) < 0.05


def test_silencio_e_ruido_nao_geram_batidas():
    rng = np.random.default_rng(1)
    ruido = (0.005 * rng.standard_normal(SR * 2)).astype("float32")
    assert detectar_batidas(ruido, SR) == []
    assert detectar_batidas(np.zeros((0, 1)), SR) == []


def test_ressonancia_nao_conta_batida_dupla():
    # uma única batida com "cauda": deve ser 1 batida
    sinal = gerar_sinal([0])
    assert len(detectar_batidas(sinal, SR)) == 1


def test_agrupamento_gera_bits_0_e_1():
    grupos = agrupar_batidas([0.5, 1.5, 1.75, 2.75], limiar_grupo_s=0.6)
    assert grupos == [[0.5], [1.5, 1.75], [2.75]]
    assert grupos_para_bits(grupos) == [0, 1, 0]


def test_tres_batidas_e_simbolo_invalido():
    assert grupos_para_bits([[0.1, 0.3, 0.5]]) == [None]


def test_montar_quadros_separa_excedentes():
    quadros, sobra = montar_quadros([1] * 20)
    assert len(quadros) == 2 and all(len(q) == 9 for q in quadros)
    assert sobra == [1, 1]


def test_avaliar_quadro_valido_e_corrompido():
    quadro = montar_quadro(bytes_to_bits(b"A"))
    ok = avaliar_quadro(quadro)
    assert ok.valido and ok.status == STATUS_SUCESSO and ok.caractere == "A"

    quadro[3] ^= 1  # inverte um bit de dados
    ruim = avaliar_quadro(quadro)
    assert not ruim.valido and ruim.status == STATUS_FALHA


def test_quadro_com_simbolo_invalido_falha():
    quadro = montar_quadro(bytes_to_bits(b"A"))
    quadro[0] = None
    assert avaliar_quadro(quadro).valido is False


def test_pipeline_completo_recebe_mensagem():
    bits = []
    for byte in b"Hi":
        bits += montar_quadro(bytes_to_bits(bytes([byte])))
    resultado = decodificar_metodo1(gerar_sinal(bits), SR)

    assert resultado.bits == bits
    assert len(resultado.quadros) == 2
    assert resultado.todos_validos
    assert resultado.mensagem == "Hi"


def test_pipeline_detecta_falha_de_paridade():
    quadro = montar_quadro(bytes_to_bits(b"A"))
    quadro[8] ^= 1  # corrompe o bit de paridade
    resultado = decodificar_metodo1(gerar_sinal(quadro), SR)

    assert len(resultado.quadros) == 1
    assert resultado.quadros[0].status == STATUS_FALHA
    assert resultado.mensagem == ""
    assert STATUS_FALHA in formatar_resultado(resultado)


def test_pipeline_com_batida_extra_reprova_quadro():
    quadro = montar_quadro(bytes_to_bits(b"A"))
    # 3ª batida junto ao bit 1 (índice 1 de "A"= 01000001 é 1)
    extra = [0.5 + GAP_BIT + 0.5]  # cai entre batidas e forma grupo de 3
    resultado = decodificar_metodo1(gerar_sinal(quadro, extras=extra), SR)
    assert not resultado.todos_validos


def test_sem_quadro_completo_informa_falha():
    resultado = decodificar_metodo1(gerar_sinal([0, 1, 0]), SR)
    assert resultado.quadros == []
    assert len(resultado.bits_excedentes) == 3
    texto = formatar_resultado(resultado)
    assert STATUS_FALHA in texto

def test_tempo_real_nao_confirma_bit_antes_do_silencio():
    sinal = gerar_sinal([0])

    receptor = ReceptorMetodo1TempoReal(SR)

    fim = int(0.7 * SR)

    resultado = receptor.processar(
        sinal[:fim]
    )

    assert resultado.bits == []


def test_tempo_real_confirma_bit_apos_silencio():
    sinal = gerar_sinal([0, 1])

    receptor = ReceptorMetodo1TempoReal(SR)

    fim_primeiro_bit = int(1.2 * SR)

    resultado = receptor.processar(
        sinal[:fim_primeiro_bit]
    )

    assert resultado.bits == [0]

    fim_segundo_bit = int(2.5 * SR)

    resultado = receptor.processar(
        sinal[:fim_segundo_bit]
    )

    assert resultado.bits == [0, 1]


def test_tempo_real_finaliza_ultimo_bit():
    sinal = gerar_sinal([0])

    receptor = ReceptorMetodo1TempoReal(SR)

    fim = int(0.7 * SR)

    resultado = receptor.processar(
        sinal[:fim],
        finalizar=True,
    )

    assert resultado.bits == [0]


def test_tempo_real_monta_quadro_completo():
    bits = montar_quadro(
        bytes_to_bits(b"A")
    )

    sinal = gerar_sinal(bits)

    receptor = ReceptorMetodo1TempoReal(SR)

    resultado = receptor.processar(sinal)

    assert resultado.bits == bits
    assert len(resultado.quadros) == 1
    assert resultado.quadros[0].valido
    assert resultado.mensagem == "A"