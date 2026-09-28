from camada_fisica.paridade import (
    calcular_paridade, 
    montar_quadro, 
    validar_paridade
)

# Teste 1
bits = [0, 0, 0, 0, 0, 0, 0, 0]
paridade = calcular_paridade(bits)
assert paridade == 0

# Teste 2
bits = [1, 0, 0, 0, 0, 0, 0, 0]
paridade = calcular_paridade(bits)
assert paridade == 1

# Teste 3
bits = [1, 1, 0, 0, 0, 0, 0, 0]
paridade = calcular_paridade(bits)
assert paridade == 0

# Teste 4
bits = [1, 1, 1, 0, 0, 0, 0, 0]
paridade = calcular_paridade(bits)
assert paridade == 1

# Teste 5 - montagem do quadro
bits = [1, 1, 1, 0, 0, 0, 0, 0]
quadro = montar_quadro(bits)
assert quadro == [1, 1, 1, 0, 0, 0, 0, 0, 1]

# Teste 6 - quadro válido
quadro = [1, 1, 1, 0, 0, 0, 0, 0, 1]
resultado = validar_paridade(quadro)
assert resultado is True

# Teste 7 - quadro corrompido
quadro = [1, 1, 1, 0, 0, 0, 0, 0, 0]
resultado = validar_paridade(quadro)
assert resultado is False

# Teste 8 - quantidade incorreta de bits
bits = [1, 0, 1, 0, 1]

try:
    calcular_paridade(bits)
    assert False
except ValueError:
    assert True