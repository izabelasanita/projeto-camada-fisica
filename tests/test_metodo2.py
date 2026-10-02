# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.

import numpy as np
import pytest

from camada_fisica.codec import bytes_to_bits
from camada_fisica.crc8 import montar_quadro
from camada_fisica.metodo2 import (
    bits_para_bytes,
    decodificar_metodo2,
    detectar_bits_2fsk,
    energia_na_frequencia,
    identificar_simbolo,
    segmentar_simbolos,
    validar_frequencias,
)
from camada_fisica.sinal_generator_2FSK import gerar_bit_2fsk, gerar_sinal_2fsk


# ----------------------------------------------------------------------
# Validação das frequências informadas pelo usuário
# ----------------------------------------------------------------------
def test_validar_frequencias_aceita_valores_validos():
    validar_frequencias(1000, 2000)


def test_validar_frequencias_rejeita_zero_ou_negativa():
    with pytest.raises(ValueError):
        validar_frequencias(0, 2000)
    with pytest.raises(ValueError):
        validar_frequencias(1000, -500)


def test_validar_frequencias_rejeita_frequencias_iguais():
    with pytest.raises(ValueError):
        validar_frequencias(1000, 1000)


# ----------------------------------------------------------------------
# Identificação de frequências / símbolos (bit 0 e bit 1)
# ----------------------------------------------------------------------
def test_identifica_bit_0_pela_frequencia():
    janela = gerar_bit_2fsk(0, frequencia_0=1000, frequencia_1=2000)
    bit = identificar_simbolo(janela, frequencia_0=1000, frequencia_1=2000)
    assert bit == 0


def test_identifica_bit_1_pela_frequencia():
    janela = gerar_bit_2fsk(1, frequencia_0=1000, frequencia_1=2000)
    bit = identificar_simbolo(janela, frequencia_0=1000, frequencia_1=2000)
    assert bit == 1


def test_silencio_nao_identifica_simbolo():
    janela = np.zeros(4410, dtype="float32")
    bit = identificar_simbolo(janela, frequencia_0=1000, frequencia_1=2000)
    assert bit is None


def test_energia_e_maior_na_frequencia_do_sinal():
    janela = gerar_bit_2fsk(0, frequencia_0=1000, frequencia_1=2000)
    energia_alvo = energia_na_frequencia(janela, 1000, 44100)
    energia_outra = energia_na_frequencia(janela, 2000, 44100)
    assert energia_alvo > energia_outra


# ----------------------------------------------------------------------
# Segmentação do sinal em símbolos, usando a duração configurada
# ----------------------------------------------------------------------
def test_segmentar_simbolos_quantidade_de_janelas():
    bits = [0, 1, 0, 1]
    sinal = gerar_sinal_2fsk(bits, duracao=0.1, taxa_amostragem=44100)
    janelas, sobra = segmentar_simbolos(
        sinal, duracao_simbolo=0.1, taxa_amostragem=44100
    )
    assert len(janelas) == 4
    assert len(sobra) == 0


def test_segmentar_simbolos_com_sobra():
    bits = [0, 1, 0]
    sinal = gerar_sinal_2fsk(bits, duracao=0.1, taxa_amostragem=44100)
    sinal_com_sobra = np.concatenate([sinal, np.zeros(100)])
    janelas, sobra = segmentar_simbolos(
        sinal_com_sobra, duracao_simbolo=0.1, taxa_amostragem=44100
    )
    assert len(janelas) == 3
    assert len(sobra) == 100


# ----------------------------------------------------------------------
# Geração da sequência de bits a partir do sinal recebido
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "bits",
    [
        [0, 1, 1, 0],
        [0, 0, 0, 0],
        [1, 1, 1, 1],
        [1, 0, 1, 0, 1, 0, 1, 0],
        [0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0],
    ],
)
def test_detectar_bits_2fsk_com_diferentes_sequencias(bits):
    sinal = gerar_sinal_2fsk(bits, duracao=0.08, taxa_amostragem=44100)
    bits_detectados, sobra = detectar_bits_2fsk(
        sinal, duracao_simbolo=0.08, taxa_amostragem=44100
    )
    assert bits_detectados == bits
    assert len(sobra) == 0


@pytest.mark.parametrize(
    "frequencia_0,frequencia_1,duracao",
    [
        (1000, 2000, 0.1),
        (700, 1400, 0.05),
        (500, 3000, 0.2),
        (1200, 1800, 0.03),
    ],
)
def test_detectar_bits_2fsk_com_diferentes_frequencias_e_duracoes(
    frequencia_0, frequencia_1, duracao
):
    bits = [0, 1, 1, 0, 1, 0]
    sinal = gerar_sinal_2fsk(
        bits,
        frequencia_0=frequencia_0,
        frequencia_1=frequencia_1,
        duracao=duracao,
    )
    bits_detectados, _ = detectar_bits_2fsk(
        sinal,
        frequencia_0=frequencia_0,
        frequencia_1=frequencia_1,
        duracao_simbolo=duracao,
    )
    assert bits_detectados == bits


# ----------------------------------------------------------------------
# Agrupamento de bits em bytes
# ----------------------------------------------------------------------
def test_bits_para_bytes_agrupa_corretamente():
    bits = bytes_to_bits(b"AB")
    dados, sobra = bits_para_bytes(bits)
    assert dados == b"AB"
    assert sobra == []


def test_bits_para_bytes_descarta_sobra_incompleta():
    bits = bytes_to_bits(b"A") + [1, 0, 1]
    dados, sobra = bits_para_bytes(bits)
    assert dados == b"A"
    assert sobra == [1, 0, 1]


def test_bits_para_bytes_com_simbolo_invalido_falha():
    bits = bytes_to_bits(b"A")
    bits[2] = None
    dados, _ = bits_para_bytes(bits)
    assert dados is None


# ----------------------------------------------------------------------
# Pipeline completo: sinal -> bits -> verificação de CRC-8
# ----------------------------------------------------------------------
def test_pipeline_completo_recebe_mensagem():
    quadro = montar_quadro(b"Oi")
    bits = bytes_to_bits(quadro)
    sinal = gerar_sinal_2fsk(bits)

    resultado = decodificar_metodo2(sinal)

    assert resultado["bits"] == bits
    assert resultado["dados"] == quadro
    assert resultado["valido"] is True
    assert resultado["status"] == "SUCESSO"
    assert resultado["mensagem"] == "Oi"


def test_pipeline_detecta_falha_de_crc():
    quadro = bytearray(montar_quadro(b"Oi"))
    quadro[0] ^= 0xFF  # corrompe o primeiro byte de dados
    bits = bytes_to_bits(bytes(quadro))
    sinal = gerar_sinal_2fsk(bits)

    resultado = decodificar_metodo2(sinal)

    assert resultado["valido"] is False
    assert resultado["status"] == "QUADRO CORROMPIDO"
    assert resultado["mensagem"] == ""


def test_pipeline_com_frequencias_e_duracao_customizadas():
    quadro = montar_quadro(b"Hi")
    bits = bytes_to_bits(quadro)
    sinal = gerar_sinal_2fsk(
        bits, frequencia_0=700, frequencia_1=1400, duracao=0.05
    )

    resultado = decodificar_metodo2(
        sinal, frequencia_0=700, frequencia_1=1400, duracao_simbolo=0.05
    )

    assert resultado["valido"] is True
    assert resultado["mensagem"] == "Hi"


def test_pipeline_sinal_insuficiente_para_um_byte():
    bits = [0, 1, 0, 1]
    sinal = gerar_sinal_2fsk(bits)

    resultado = decodificar_metodo2(sinal)

    assert resultado["dados"] == b""
    assert resultado["valido"] is False
    assert resultado["status"] == "FALHA DE TRANSMISSÃO"


def test_detectar_bits_2fsk_ignora_silencio_antes_e_depois():
    """O sincronismo deve ignorar o atraso da captura pelo microfone."""
    bits = [0, 1, 1, 0, 1, 0, 0, 1]
    sinal = gerar_sinal_2fsk(bits, duracao=0.1, taxa_amostragem=44100)

    silencio_inicial = np.zeros(5000, dtype=float)
    silencio_final = np.zeros(7000, dtype=float)
    captura = np.concatenate(
        [silencio_inicial, sinal, silencio_final]
    )

    bits_detectados, sobra = detectar_bits_2fsk(
        captura,
        duracao_simbolo=0.1,
        taxa_amostragem=44100,
    )

    assert bits_detectados == bits
    assert len(sobra) == 0


def test_detectar_bits_2fsk_com_inicio_deslocado():
    """Um pequeno deslocamento após o início do tom não deve perder o quadro."""
    bits = [1, 0, 1, 1, 0, 0, 1, 0]
    sinal = gerar_sinal_2fsk(
        bits,
        frequencia_0=700,
        frequencia_1=1400,
        duracao=0.05,
        taxa_amostragem=44100,
    )

    captura = np.concatenate(
        [
            np.zeros(3500, dtype=float),
            sinal,
            np.zeros(3500, dtype=float),
        ]
    )

    bits_detectados, _ = detectar_bits_2fsk(
        captura,
        frequencia_0=700,
        frequencia_1=1400,
        duracao_simbolo=0.05,
        taxa_amostragem=44100,
    )

    assert bits_detectados == bits


def test_detectar_bits_2fsk_com_ruido_de_fundo():
    """A sincronização deve encontrar o tom mesmo com ruído de microfone."""
    rng = np.random.default_rng(123)
    bits = [0, 1, 1, 0, 1, 0, 0, 1]
    sinal = gerar_sinal_2fsk(bits, duracao=0.1, taxa_amostragem=44100)
    captura = np.concatenate(
        [
            rng.normal(0, 0.015, 3 * 44100),
            0.16 * sinal,
            rng.normal(0, 0.015, 3 * 44100),
        ]
    )

    bits_detectados, sobra = detectar_bits_2fsk(
        captura,
        duracao_simbolo=0.1,
        taxa_amostragem=44100,
    )

    assert bits_detectados == bits
    assert len(sobra) == 0


def test_pipeline_recupera_bits_finais_do_crc_quando_captura_termina_antes():
    """Recupera o último bit do CRC quando apenas 47 de 48 bits chegaram."""
    quadro = montar_quadro(b"teste")
    bits = bytes_to_bits(quadro)
    assert len(bits) == 48

    # Simula exatamente o caso de uma captura que perdeu o último símbolo.
    sinal = gerar_sinal_2fsk(bits[:-1])
    # Acrescenta apenas 47 símbolos: o receptor recebe todos os dados e os
    # 7 primeiros bits do CRC. O CRC-8 permite determinar o último bit.
    resultado = decodificar_metodo2(sinal)

    assert resultado["valido"] is True
    assert resultado["mensagem"] == "teste"
    assert resultado["bits_recuperados_por_crc"] is True

    # Agora simula o caso mais realista: o áudio contém o último símbolo,
    # mas a detecção do intervalo perdeu a cauda. O helper deve conseguir
    # completar o byte de CRC a partir dos 47 bits.
    from camada_fisica.metodo2 import _tentar_recuperar_crc_com_bits_faltantes

    recuperados, quadro_recuperado = _tentar_recuperar_crc_com_bits_faltantes(
        bits[:-1]
    )

    assert recuperados == bits
    assert quadro_recuperado == quadro


def test_pipeline_nao_inventa_bit_final_sem_confirmacao_do_crc():
    quadro = montar_quadro(b"teste")
    bits = bytes_to_bits(quadro)[:-1]
    bits[-1] ^= 1

    from camada_fisica.metodo2 import _tentar_recuperar_crc_com_bits_faltantes

    recuperados, quadro_recuperado = _tentar_recuperar_crc_com_bits_faltantes(bits)

    assert recuperados is None
    assert quadro_recuperado is None
