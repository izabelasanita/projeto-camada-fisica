import numpy as np

from .crc8 import identificar_quadro, validar_crc8
from .sinal_generator_2FSK import (
    DURACAO_SIMBOLO,
    FREQUENCIA_0,
    FREQUENCIA_1,
    TAXA_AMOSTRAGEM,
)


def validar_frequencias(frequencia_0, frequencia_1):
    """
    Garante que as frequências informadas para a recepção são válidas
    e suficientemente diferentes para serem distinguidas uma da outra.
    """

    if frequencia_0 <= 0 or frequencia_1 <= 0:
        raise ValueError("As frequências devem ser maiores que zero.")

    if frequencia_0 == frequencia_1:
        raise ValueError(
            "A frequência do bit 0 e a frequência do bit 1 devem ser diferentes."
        )


def energia_na_frequencia(amostras, frequencia, taxa_amostragem):
    """
    Calcula a energia do sinal em uma frequência específica utilizando
    o algoritmo de Goertzel.

    É equivalente a calcular o módulo da Transformada de Fourier (DFT)
    numa única frequência, porém muito mais barato que uma FFT completa
    quando só se quer avaliar uma ou duas frequências por vez.
    """

    amostras = np.asarray(amostras, dtype=np.float64)
    quantidade_amostras = len(amostras)

    if quantidade_amostras == 0:
        return 0.0

    indice = int(0.5 + quantidade_amostras * frequencia / taxa_amostragem)
    omega = 2 * np.pi * indice / quantidade_amostras
    coeficiente = 2 * np.cos(omega)

    s_anterior = 0.0
    s_anterior2 = 0.0

    for amostra in amostras:
        s_atual = amostra + coeficiente * s_anterior - s_anterior2
        s_anterior2 = s_anterior
        s_anterior = s_atual

    potencia = (
        s_anterior2**2
        + s_anterior**2
        - coeficiente * s_anterior * s_anterior2
    )

    return abs(potencia)


def identificar_simbolo(
    janela,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
    taxa_amostragem=TAXA_AMOSTRAGEM,
):
    """
    Identifica se uma janela de amostras corresponde ao bit 0 ou ao bit 1.

    O método para diferenciar as duas frequências é comparar a energia do
    sinal (calculada via Goertzel) nas duas frequências configuradas: a
    frequência com maior energia é considerada a frequência transmitida.

    Retorna None quando a janela não possui energia significativa em
    nenhuma das duas frequências (silêncio ou símbolo corrompido/ruído).
    """

    validar_frequencias(frequencia_0, frequencia_1)

    energia_0 = energia_na_frequencia(janela, frequencia_0, taxa_amostragem)
    energia_1 = energia_na_frequencia(janela, frequencia_1, taxa_amostragem)

    if energia_0 == 0 and energia_1 == 0:
        return None

    return 0 if energia_0 >= energia_1 else 1


def _converter_mono(amostras):
    """Converte amostras mono/multicanal para um vetor 1-D de float64."""
    amostras = np.asarray(amostras, dtype=np.float64)

    if amostras.ndim == 0:
        amostras = amostras.reshape(1)
    elif amostras.ndim > 1:
        amostras = amostras.mean(axis=1)

    return amostras


def _detectar_regioes_por_frequencia(
    amostras,
    frequencia_0,
    frequencia_1,
    taxa_amostragem,
    janela_s=0.02,
    passo_s=0.01,
    limiar_score=15.0,
):
    """Detecta regiões que realmente contêm uma das duas portadoras 2-FSK.

    A detecção por amplitude sozinha pode falhar em gravações de microfone:
    um clique, eco ou ruído pode ter amplitude maior que o tom transmitido.
    Aqui procuramos energia concentrada nas duas frequências conhecidas.
    """

    tamanho_janela = max(32, int(round(janela_s * taxa_amostragem)))
    passo = max(1, int(round(passo_s * taxa_amostragem)))

    if len(amostras) < tamanho_janela:
        return []

    ativos = []
    for inicio in range(0, len(amostras) - tamanho_janela + 1, passo):
        janela = amostras[inicio : inicio + tamanho_janela]
        energia_total = float(np.sum(janela * janela))

        if energia_total <= np.finfo(np.float64).eps:
            continue

        energia_0 = energia_na_frequencia(
            janela, frequencia_0, taxa_amostragem
        )
        energia_1 = energia_na_frequencia(
            janela, frequencia_1, taxa_amostragem
        )

        # Para um tom, a energia de Goertzel fica muito mais concentrada
        # na portadora do que para ruído de banda larga.
        score = max(energia_0, energia_1) / energia_total
        if score >= limiar_score:
            ativos.append((inicio, inicio + tamanho_janela))

    if not ativos:
        return []

    # Une blocos consecutivos e pequenas lacunas. Uma lacuna curta pode ser
    # causada pelo eco, pelo AGC do microfone ou pela troca entre símbolos.
    lacuna_maxima = max(1, int(0.05 * taxa_amostragem))
    regioes = [[ativos[0][0], ativos[0][1]]]

    for inicio, fim in ativos[1:]:
        if inicio - regioes[-1][1] <= lacuna_maxima:
            regioes[-1][1] = fim
        else:
            regioes.append([inicio, fim])

    return regioes


def detectar_intervalo_ativo(
    amostras,
    taxa_amostragem=TAXA_AMOSTRAGEM,
    janela_envoltoria_s=0.005,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
):
    """Localiza o trecho em que o sinal 2-FSK está presente.

    A captura pelo microfone normalmente começa antes da reprodução e termina
    depois dela. Primeiro é feita uma detecção simples pela envoltória. Se
    ela não encontrar um trecho confiável, é feita uma segunda detecção pela
    energia espectral das duas portadoras configuradas. Isso evita que ruído
    ou um pico de amplitude fora da transmissão faça o receptor concluir que
    não existe sinal.

    Retorna ``(inicio, fim)`` em índices de amostra, com ``fim`` exclusivo.
    Para um sinal vazio ou sem energia detectável, retorna ``(0, 0)``.
    """

    if taxa_amostragem <= 0:
        raise ValueError("A taxa de amostragem deve ser maior que zero.")

    validar_frequencias(frequencia_0, frequencia_1)
    x = _converter_mono(amostras)

    if x.size == 0:
        return 0, 0

    if not np.all(np.isfinite(x)):
        raise ValueError("As amostras contêm valores NaN ou infinitos.")

    # --- 1) Detecção pela envoltória ---------------------------------
    janela = max(1, int(round(janela_envoltoria_s * taxa_amostragem)))
    envoltoria = np.abs(x)

    if janela > 1:
        soma = np.concatenate(([0.0], np.cumsum(envoltoria)))
        indices = np.arange(len(envoltoria))
        inicio_janela = np.maximum(0, indices - janela + 1)
        envoltoria = (
            soma[indices + 1] - soma[inicio_janela]
        ) / (indices + 1 - inicio_janela)

    pico = float(np.max(envoltoria))
    regioes_amplitude = []

    if pico > np.finfo(np.float64).eps:
        piso_ruido = float(np.median(envoltoria))
        limiar = max(0.01, 0.10 * pico, 4.0 * piso_ruido)
        if limiar >= pico:
            limiar = 0.50 * pico

        acima = envoltoria >= limiar
        lacuna_maxima = max(1, int(0.020 * taxa_amostragem))
        transicoes = np.diff(
            np.concatenate(([False], acima, [False])).astype(np.int8)
        )
        inicios = np.flatnonzero(transicoes == 1)
        fins = np.flatnonzero(transicoes == -1)

        regioes = []
        for inicio, fim in zip(inicios, fins):
            inicio = int(inicio)
            fim = int(fim)
            if regioes and inicio - regioes[-1][1] <= lacuna_maxima:
                regioes[-1][1] = fim
            else:
                regioes.append([inicio, fim])

        # Não aceite uma região minúscula: isso normalmente é apenas um
        # clique/ruído, e não um quadro 2-FSK.
        duracao_minima = max(1, int(0.5 * taxa_amostragem * DURACAO_SIMBOLO))
        regioes_amplitude = [
            reg for reg in regioes if reg[1] - reg[0] >= duracao_minima
        ]

    # A detecção espectral é mais confiável para tons 2-FSK do que a
    # amplitude quando existe ruído de fundo. Usamos sempre que disponível e
    # escolhemos a região mais longa entre as candidatas.
    regioes_frequencia = _detectar_regioes_por_frequencia(
        x,
        frequencia_0,
        frequencia_1,
        taxa_amostragem,
    )

    candidatas = regioes_frequencia or regioes_amplitude
    if not candidatas:
        return 0, 0

    inicio, fim = max(candidatas, key=lambda regiao: regiao[1] - regiao[0])
    return int(inicio), int(fim)


def segmentar_simbolos(
    amostras,
    duracao_simbolo=DURACAO_SIMBOLO,
    taxa_amostragem=TAXA_AMOSTRAGEM,
    sincronizar=False,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
):
    """
    Divide o sinal em janelas completas de um símbolo.

    Por compatibilidade, ``sincronizar=False`` mantém o comportamento antigo:
    a segmentação começa na amostra 0 e qualquer sobra no final é retornada.

    Quando ``sincronizar=True``, o silêncio antes/depois da transmissão é
    detectado e removido antes da segmentação. Isso é o modo usado pela
    recepção do Método 2.
    """

    if duracao_simbolo <= 0:
        raise ValueError("A duração do símbolo deve ser maior que zero.")

    if taxa_amostragem <= 0:
        raise ValueError("A taxa de amostragem deve ser maior que zero.")

    amostras = _converter_mono(amostras)

    tamanho_simbolo = int(round(duracao_simbolo * taxa_amostragem))

    if tamanho_simbolo <= 0:
        raise ValueError(
            "A combinação de duração do símbolo e taxa de amostragem "
            "resulta em janelas vazias."
        )

    if sincronizar:
        inicio, fim = detectar_intervalo_ativo(
            amostras,
            taxa_amostragem,
            frequencia_0=frequencia_0,
            frequencia_1=frequencia_1,
        )

        if fim <= inicio:
            return [], amostras.copy()

        # O limiar de envoltória pode cortar alguns poucos milissegundos
        # no começo/fim do tom. Portanto, não usamos simplesmente
        # ``len(amostras) // tamanho_simbolo``: isso poderia perder o último
        # símbolo mesmo quando o quadro inteiro foi capturado.
        duracao_ativa = fim - inicio
        quantidade_simbolos = int(
            round(duracao_ativa / tamanho_simbolo)
        )

        if quantidade_simbolos <= 0:
            return [], amostras[inicio:fim]

        tamanho_esperado = quantidade_simbolos * tamanho_simbolo
        amostras_ativas = amostras[inicio:fim]

        # Aceita uma pequena perda na detecção das bordas. Se a perda for
        # grande demais, considera somente os símbolos completos realmente
        # presentes, evitando inventar um símbolo parcial.
        tolerancia_borda = max(1, int(0.15 * tamanho_simbolo))

        if len(amostras_ativas) < tamanho_esperado:
            falta = tamanho_esperado - len(amostras_ativas)

            if falta <= tolerancia_borda:
                amostras_ativas = np.pad(
                    amostras_ativas,
                    (0, falta),
                    mode="constant",
                )
            else:
                quantidade_simbolos -= 1
                tamanho_esperado = quantidade_simbolos * tamanho_simbolo
                amostras_ativas = amostras_ativas[:tamanho_esperado]
        else:
            amostras_ativas = amostras_ativas[:tamanho_esperado]

        amostras = amostras_ativas

    quantidade_simbolos = len(amostras) // tamanho_simbolo

    janelas = [
        amostras[indice * tamanho_simbolo : (indice + 1) * tamanho_simbolo]
        for indice in range(quantidade_simbolos)
    ]

    sobra = amostras[quantidade_simbolos * tamanho_simbolo :]

    return janelas, sobra


def detectar_bits_2fsk(
    amostras,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
    duracao_simbolo=DURACAO_SIMBOLO,
    taxa_amostragem=TAXA_AMOSTRAGEM,
):
    """
    Detecta os símbolos presentes no sinal recebido e gera a sequência
    de bits correspondente ao Método 2 (2-FSK).

    Antes de segmentar, sincroniza automaticamente o início do quadro,
    removendo o silêncio capturado antes da transmissão e ignorando o
    silêncio posterior.

    Retorna a lista de bits decodificados e as amostras residuais do trecho
    ativo que não completaram um símbolo.
    """

    janelas, sobra = segmentar_simbolos(
        amostras,
        duracao_simbolo,
        taxa_amostragem,
        sincronizar=True,
        frequencia_0=frequencia_0,
        frequencia_1=frequencia_1,
    )

    bits = [
        identificar_simbolo(
            janela,
            frequencia_0,
            frequencia_1,
            taxa_amostragem,
        )
        for janela in janelas
    ]

    return bits, sobra


def bits_para_bytes(bits):
    """
    Agrupa a sequência de bits em bytes (8 bits cada, bit mais
    significativo primeiro), descartando bits incompletos no final.

    Caso algum bit de um grupo de 8 não tenha sido identificado (símbolo
    inválido/corrompido), os dados são considerados ilegíveis e a função
    retorna None no lugar dos bytes.
    """

    quantidade_completa = len(bits) // 8 * 8
    bits_sobrando = list(bits[quantidade_completa:])

    dados = bytearray()

    for inicio in range(0, quantidade_completa, 8):
        grupo = bits[inicio : inicio + 8]

        if any(bit is None for bit in grupo):
            return None, bits_sobrando

        valor = 0

        for bit in grupo:
            valor = (valor << 1) | bit

        dados.append(valor)

    return bytes(dados), bits_sobrando


def _tentar_recuperar_crc_com_bits_faltantes(bits):
    """Tenta recuperar somente bits ausentes no final do quadro.

    O formato do Método 2 é [dados][CRC-8]. Quando a captura termina um
    pouco antes do último símbolo, é possível receber, por exemplo, 47 bits
    de um quadro de 48 bits: os 40 primeiros são os dados e os 7 seguintes
    são parte do CRC. Nessa situação, testar as poucas combinações possíveis
    do byte de CRC permite recuperar o quadro sem inventar dados.

    Retorna ``(bits_recuperados, quadro)`` quando o CRC confirma uma única
    possibilidade; caso contrário, retorna ``(None, None)``.
    """

    quantidade = len(bits)
    restante = quantidade % 8

    # Se não há byte incompleto, não existe bit final conhecido para
    # completar. A validação normal deve ser usada.
    if restante == 0 or quantidade < 8:
        return None, None

    bits_conhecidos = list(bits)
    bits_faltantes = 8 - restante

    # Só é seguro fazer esta recuperação quando todos os bytes completos
    # anteriores podem ser tratados como dados. O byte incompleto é então o
    # CRC que foi cortado no final da captura.
    prefixo = bits_conhecidos[: quantidade - restante]
    crc_parcial = bits_conhecidos[quantidade - restante :]

    # Não há espaço para uma mensagem vazia + CRC.
    if len(prefixo) < 8:
        return None, None

    candidatos = []
    for valor_complementar in range(1 << bits_faltantes):
        complemento = [
            (valor_complementar >> pos) & 1
            for pos in range(bits_faltantes - 1, -1, -1)
        ]
        candidato_bits = prefixo + crc_parcial + complemento

        dados_candidato, sobra = bits_para_bytes(candidato_bits)
        if sobra or dados_candidato is None or len(dados_candidato) < 2:
            continue

        if validar_crc8(dados_candidato):
            candidatos.append((candidato_bits, dados_candidato))

    # CRC deve apontar para uma única possibilidade. Se houver mais de uma,
    # não escolhemos arbitrariamente.
    if len(candidatos) != 1:
        return None, None

    return candidatos[0]


def decodificar_metodo2(
    amostras,
    frequencia_0=FREQUENCIA_0,
    frequencia_1=FREQUENCIA_1,
    duracao_simbolo=DURACAO_SIMBOLO,
    taxa_amostragem=TAXA_AMOSTRAGEM,
):
    """
    Executa a recepção completa do Método 2: identifica as frequências
    presentes no sinal, gera a sequência de bits e envia os bits
    decodificados para a verificação do CRC-8.

    O quadro recebido é formado por N bytes de dados seguidos de 1 byte
    de CRC-8 (formato de camada_fisica.crc8.montar_quadro).

    Retorna um dicionário com:
        bits: a sequência de bits decodificada (um item por símbolo);
        bits_sobrando: bits que não formaram um byte completo;
        dados: os bytes recebidos (None se o sinal não pôde ser lido);
        valido: True se o CRC-8 confere;
        status: "SUCESSO" ou "FALHA DE TRANSMISSÃO";
        mensagem: o texto decodificado (apenas quando válido);
        bits_recuperados_por_crc: True quando o último byte (CRC-8) foi
            completado por validação inequívoca após uma captura truncada.
    """

    validar_frequencias(frequencia_0, frequencia_1)

    bits, bits_residuais = detectar_bits_2fsk(
        amostras,
        frequencia_0,
        frequencia_1,
        duracao_simbolo,
        taxa_amostragem,
    )

    dados, bits_sobrando_byte = bits_para_bytes(bits)
    bits_recuperados_por_crc = False

    # Caso comum em captura de microfone: o último símbolo pode ser cortado
    # alguns milissegundos antes do fim. Se o número de bits não for múltiplo
    # de 8, tentamos recuperar somente a parte faltante do BYTE DE CRC.
    # Isso não altera os dados recebidos e só aceita a recuperação quando o
    # CRC-8 produz exatamente uma única solução.
    if bits_sobrando_byte and dados is not None:
        bits_recuperados, quadro_recuperado = (
            _tentar_recuperar_crc_com_bits_faltantes(bits)
        )

        if bits_recuperados is not None:
            bits = bits_recuperados
            dados = quadro_recuperado
            bits_sobrando_byte = []
            bits_recuperados_por_crc = True

    resultado = {
        "bits": bits,
        "bits_sobrando": bits_sobrando_byte,
        "dados": dados,
        "valido": False,
        "status": "FALHA DE TRANSMISSÃO",
        "mensagem": "",
        "bits_recuperados_por_crc": bits_recuperados_por_crc,
    }

    if dados is None or len(dados) < 2:
        return resultado

    resultado["valido"] = validar_crc8(dados)
    resultado["status"] = (
        "SUCESSO" if resultado["valido"] else identificar_quadro(dados)
    )

    if resultado["valido"]:
        resultado["mensagem"] = dados[:-1].decode("utf-8", errors="replace")

    return resultado


def formatar_resultado(resultado):
    """
    Monta um relatório em texto do resultado da recepção do Método 2,
    para exibição no terminal ou na interface.
    """

    simbolo = lambda bit: "?" if bit is None else str(bit)  # noqa: E731

    linhas = [
        "Bits decodificados: " + "".join(simbolo(bit) for bit in resultado["bits"]),
        f"Status: {resultado['status']}",
    ]

    if resultado["bits_sobrando"]:
        linhas.append(
            f"Aviso: {len(resultado['bits_sobrando'])} bit(s) sobrando, "
            "byte incompleto descartado."
        )

    if resultado["valido"]:
        linhas.append(f"Mensagem recebida: {resultado['mensagem']!r}")

    return "\n".join(linhas)
