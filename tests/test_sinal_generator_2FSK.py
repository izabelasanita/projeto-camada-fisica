import numpy as np

from camada_fisica.sinal_generator_2FSK import (
    gerar_bit_2fsk,
    gerar_sinal_2fsk,
)


# Teste 1 - bit 0
def test_bit_0():

    sinal = gerar_bit_2fsk(0)

    assert isinstance(sinal, np.ndarray)
    assert len(sinal) > 0


# Teste 2 - bit 1
def test_bit_1():

    sinal = gerar_bit_2fsk(1)

    assert isinstance(sinal, np.ndarray)
    assert len(sinal) > 0


# Teste 3 - sequência com múltiplos bits
def test_sequencia_multiplos_bits():

    bits = [0, 1, 1, 0]

    sinal = gerar_sinal_2fsk(bits)

    assert isinstance(sinal, np.ndarray)
    assert len(sinal) > 0


# Teste 4 - sequência com apenas 0
def test_sequencia_apenas_zeros():

    bits = [0, 0, 0, 0]

    sinal = gerar_sinal_2fsk(bits)

    assert isinstance(sinal, np.ndarray)
    assert len(sinal) > 0

# Teste 5 - sequência com apenas 1
def test_sequencia_apenas_uns():

    bits = [1, 1, 1, 1]

    sinal = gerar_sinal_2fsk(bits)

    assert isinstance(sinal, np.ndarray)
    assert len(sinal) > 0

# Teste 6 - diferentes durações de símbolo
def test_diferentes_duracoes():

    bits = [0, 1, 0, 1]

    sinal_curto = gerar_sinal_2fsk(
        bits,
        duracao=0.05,
    )

    sinal_longo = gerar_sinal_2fsk(
        bits,
        duracao=0.1,
    )

    assert len(sinal_curto) < len(sinal_longo)


# Teste 7 - diferentes frequências
def test_diferentes_frequencias():

    bits = [0, 1, 0, 1]

    sinal_1 = gerar_sinal_2fsk(
        bits,
        frequencia_0=800,
        frequencia_1=1600,
    )

    sinal_2 = gerar_sinal_2fsk(
        bits,
        frequencia_0=1000,
        frequencia_1=2000,
    )

    assert isinstance(sinal_1, np.ndarray)
    assert isinstance(sinal_2, np.ndarray)

    assert not np.array_equal(sinal_1, sinal_2)


# Teste 8 - combinação de frequências e duração
def test_configuracao_2fsk():

    bits = [0, 1, 1, 0]

    sinal = gerar_sinal_2fsk(
        bits,
        frequencia_0=700,
        frequencia_1=1400,
        duracao=0.05,
    )

    print("Bits:", bits)
    print("Bit 0 → 700 Hz")
    print("Bit 1 → 1400 Hz")
    print("Duração de cada símbolo: 0.05 s")
    print("Taxa teórica:", 1 / 0.05, "bits/s")
    print("Quantidade de amostras:", len(sinal))

    assert isinstance(sinal, np.ndarray)
    assert len(sinal) > 0
