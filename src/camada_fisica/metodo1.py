# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som
# Este arquivo faz parte do projeto "camada-fisica-som", distribuído sob a
# licença MIT. Consulte o arquivo LICENSE na raiz do repositório.
"""Recepção do Método 1: identificação de batidas e conversão em bits.

Pipeline (amostras de áudio -> mensagem):

1. :func:`detectar_batidas`   - mapeia os picos sonoros (batidas) no áudio;
2. :func:`agrupar_batidas`    - separa as batidas em símbolos pelos silêncios;
3. :func:`grupos_para_bits`   - padroniza os bits:
       * bit 0 = silêncio + 1 batida  + silêncio
       * bit 1 = silêncio + 2 batidas + silêncio
4. :func:`montar_quadros`     - agrupa a sequência de bits em quadros de 9 bits;
5. :func:`avaliar_quadro`     - envia cada quadro para a paridade par
   (``camada_fisica.paridade``) e marca SUCESSO ou FALHA DE TRANSMISSÃO.

:func:`decodificar_metodo1` executa todo o pipeline de uma vez.

Os tempos (janelas de silêncio, intervalo mínimo entre batidas) ficam em
:class:`ConfigMetodo1` para que possam ser calibrados com o ritmo do vídeo de
referência da atividade sem alterar o código do algoritmo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from .codec import bits_to_bytes
from .paridade import validar_paridade

BITS_DADOS = 8
BITS_QUADRO = 9

STATUS_SUCESSO = "SUCESSO"
STATUS_FALHA = "FALHA DE TRANSMISSÃO"

LIMIAR_GRUPO_PADRAO_S = 0.6
"""Maior intervalo (s) entre duas batidas para que ainda pertençam ao mesmo
bit. Usado quando não é possível estimar o limiar automaticamente."""


@dataclass
class ConfigMetodo1:
    """Parâmetros ajustáveis da detecção de batidas do Método 1."""

    janela_envoltoria_s: float = 0.005
    """Janela (s) da média móvel que suaviza o módulo do sinal (envoltória)."""

    limiar_absoluto: float = 0.05
    """Amplitude mínima (0..1) para considerar que houve batida. Abaixo disso
    tudo é tratado como ruído de fundo."""

    fracao_pico: float = 0.25
    """Fração do maior pico da gravação usada como limiar relativo. Ignora
    ecos e ruídos fracos perto de batidas fortes."""

    intervalo_minimo_s: float = 0.08
    """Picos separados por menos que isso são a mesma batida (ressonância)."""

    limiar_grupo_s: Optional[float] = None
    """Intervalo (s) que separa batidas do mesmo bit de bits diferentes.
    ``None`` = estimado automaticamente a partir da gravação."""


@dataclass
class QuadroRecebido:
    """Resultado da verificação de paridade de um quadro de 9 bits."""

    bits: List[Optional[int]]
    valido: bool
    byte: Optional[int] = None

    @property
    def status(self) -> str:
        return STATUS_SUCESSO if self.valido else STATUS_FALHA

    @property
    def caractere(self) -> Optional[str]:
        if self.byte is None:
            return None
        return chr(self.byte) if 32 <= self.byte < 127 else None


@dataclass
class ResultadoMetodo1:
    """Saída completa da recepção do Método 1."""

    tempos_batidas: List[float] = field(default_factory=list)
    grupos: List[List[float]] = field(default_factory=list)
    bits: List[Optional[int]] = field(default_factory=list)
    quadros: List[QuadroRecebido] = field(default_factory=list)
    bits_excedentes: List[Optional[int]] = field(default_factory=list)
    limiar_grupo_s: float = LIMIAR_GRUPO_PADRAO_S

    @property
    def mensagem(self) -> str:
        """Texto formado apenas pelos quadros recebidos com SUCESSO."""
        dados = bytes(q.byte for q in self.quadros if q.valido)
        return dados.decode("utf-8", errors="replace")

    @property
    def todos_validos(self) -> bool:
        return bool(self.quadros) and all(q.valido for q in self.quadros)

class ReceptorMetodo1TempoReal:
    """
    Processa a recepção do Método 1 durante a captura do áudio.

    As amostras acumuladas são analisadas periodicamente e somente grupos
    de batidas já encerrados por um período suficiente de silêncio são
    convertidos em bits.

    Isso evita interpretar uma única batida como bit 0 antes de saber se
    uma segunda batida chegará para formar o bit 1.
    """

    def __init__(
        self,
        taxa_amostragem: int,
        config: Optional[ConfigMetodo1] = None,
    ) -> None:
        if taxa_amostragem <= 0:
            raise ValueError(
                "A taxa de amostragem deve ser positiva."
            )

        self.taxa_amostragem = taxa_amostragem
        self.config = config or ConfigMetodo1()

        self.resultado = ResultadoMetodo1()

    def reset(self) -> None:
        """
        Limpa o resultado da recepção atual.
        """

        self.resultado = ResultadoMetodo1()

    def processar(
        self,
        amostras,
        finalizar: bool = False,
    ) -> ResultadoMetodo1:
        """
        Processa as amostras capturadas até o momento.

        Durante a captura, somente grupos seguidos de silêncio suficiente
        são considerados concluídos.

        Quando ``finalizar`` é True, todos os grupos encontrados são
        processados. Isso é usado ao encerrar a captura.
        """

        tempos = detectar_batidas(
            amostras,
            self.taxa_amostragem,
            self.config,
        )

        limiar = self.config.limiar_grupo_s

        if limiar is None:
            limiar = LIMIAR_GRUPO_PADRAO_S

        grupos = agrupar_batidas(
            tempos,
            limiar,
        )

        if finalizar:
            grupos_confirmados = grupos

        else:
            duracao_atual = (
                len(amostras) / self.taxa_amostragem
            )

            grupos_confirmados = [
                grupo
                for grupo in grupos
                if grupo
                and duracao_atual - grupo[-1] > limiar
            ]

        bits = grupos_para_bits(
            grupos_confirmados
        )

        quadros_bits, excedentes = montar_quadros(bits)

        self.resultado = ResultadoMetodo1(
            tempos_batidas=tempos,
            grupos=grupos_confirmados,
            bits=bits,
            quadros=[
                avaliar_quadro(quadro)
                for quadro in quadros_bits
            ],
            bits_excedentes=excedentes,
            limiar_grupo_s=limiar,
        )

        return self.resultado

# ----------------------------------------------------------------------
# 1) Mapear os picos sonoros (batidas)
# ----------------------------------------------------------------------
def _media_movel(x: np.ndarray, janela: int) -> np.ndarray:
    """Média móvel centrada, O(n), via soma acumulada."""
    if janela <= 1:
        return x
    n = len(x)
    soma = np.concatenate(([0.0], np.cumsum(x)))
    idx = np.arange(n)
    inicio = np.clip(idx - janela // 2, 0, n)
    fim = np.clip(idx - janela // 2 + janela, 0, n)
    return (soma[fim] - soma[inicio]) / (fim - inicio)


def detectar_batidas(
    amostras,
    taxa_amostragem: int,
    config: Optional[ConfigMetodo1] = None,
) -> List[float]:
    """Retorna os instantes (em segundos) em que ocorreram batidas.

    Calcula a envoltória do sinal, define um limiar (maior entre o absoluto e
    a fração do pico) e registra um instante por região acima do limiar.
    Regiões muito próximas (< ``intervalo_minimo_s``) são fundidas para que a
    ressonância de uma mesma batida não seja contada duas vezes.
    """
    cfg = config or ConfigMetodo1()
    x = np.abs(np.asarray(amostras, dtype=np.float64))
    if x.size == 0:
        return []
    if x.ndim > 1:  # vários canais: usa o mais forte em cada instante
        x = x.max(axis=1)

    janela = max(1, int(cfg.janela_envoltoria_s * taxa_amostragem))
    envoltoria = _media_movel(x, janela)

    pico = float(envoltoria.max())
    if pico < cfg.limiar_absoluto:
        return []
    limiar = max(cfg.limiar_absoluto, cfg.fracao_pico * pico)

    acima = (envoltoria > limiar).astype(np.int8)
    variacao = np.diff(acima, prepend=0, append=0)
    inicios = np.flatnonzero(variacao == 1)
    fins = np.flatnonzero(variacao == -1)  # exclusivo

    folga = int(cfg.intervalo_minimo_s * taxa_amostragem)
    regioes: List[List[int]] = []
    for ini, fim in zip(inicios, fins):
        if regioes and ini - regioes[-1][1] < folga:
            regioes[-1][1] = int(fim)
        else:
            regioes.append([int(ini), int(fim)])

    return [
        (ini + int(np.argmax(envoltoria[ini:fim]))) / taxa_amostragem
        for ini, fim in regioes
    ]


# ----------------------------------------------------------------------
# 2) e 3) Padronizar bit 0 (1 batida) e bit 1 (2 batidas consecutivas)
# ----------------------------------------------------------------------
def estimar_limiar_grupo(tempos: Sequence[float]) -> float:
    """Estima o silêncio que separa um bit do seguinte.

    Os intervalos entre batidas formam dois conjuntos: curtos (batidas do
    mesmo bit 1) e longos (silêncio entre bits). O limiar é posto na maior
    "quebra" entre eles. Sem separação clara, usa ``LIMIAR_GRUPO_PADRAO_S``.
    """
    intervalos = np.sort(np.diff(np.asarray(tempos, dtype=np.float64)))
    intervalos = intervalos[intervalos > 0]
    if len(intervalos) < 2:
        return LIMIAR_GRUPO_PADRAO_S
    razoes = intervalos[1:] / intervalos[:-1]
    i = int(np.argmax(razoes))
    if razoes[i] >= 1.6:
        return float(np.sqrt(intervalos[i] * intervalos[i + 1]))
    return LIMIAR_GRUPO_PADRAO_S


def agrupar_batidas(
    tempos: Sequence[float], limiar_grupo_s: float
) -> List[List[float]]:
    """Agrupa batidas consecutivas; um silêncio maior que o limiar inicia
    um novo símbolo (bit)."""
    grupos: List[List[float]] = []
    for t in tempos:
        if grupos and t - grupos[-1][-1] <= limiar_grupo_s:
            grupos[-1].append(t)
        else:
            grupos.append([t])
    return grupos


def grupos_para_bits(grupos: Sequence[Sequence[float]]) -> List[Optional[int]]:
    """1 batida -> bit 0; 2 batidas -> bit 1; qualquer outra quantidade é
    símbolo inválido e vira ``None`` (preserva o alinhamento dos quadros e
    faz o quadro ser reprovado)."""
    bits: List[Optional[int]] = []
    for grupo in grupos:
        if len(grupo) == 1:
            bits.append(0)
        elif len(grupo) == 2:
            bits.append(1)
        else:
            bits.append(None)
    return bits


# ----------------------------------------------------------------------
# 4) e 5) Sequência de bits -> quadros -> paridade par
# ----------------------------------------------------------------------
def montar_quadros(bits: Sequence[Optional[int]]):
    """Divide os bits em quadros de 9. Retorna ``(quadros, excedentes)``."""
    completos = len(bits) // BITS_QUADRO * BITS_QUADRO
    quadros = [list(bits[i : i + BITS_QUADRO]) for i in range(0, completos, BITS_QUADRO)]
    return quadros, list(bits[completos:])


def avaliar_quadro(quadro: Sequence[Optional[int]]) -> QuadroRecebido:
    """Envia um quadro de 9 bits para a verificação de paridade par."""
    quadro = list(quadro)
    if any(b is None for b in quadro):
        return QuadroRecebido(bits=quadro, valido=False)
    valido = validar_paridade(quadro)
    byte = bits_to_bytes(quadro[:BITS_DADOS])[0]
    return QuadroRecebido(bits=quadro, valido=valido, byte=byte)


def decodificar_metodo1(
    amostras,
    taxa_amostragem: int,
    config: Optional[ConfigMetodo1] = None,
) -> ResultadoMetodo1:
    """Executa a recepção completa do Método 1 sobre as amostras de áudio."""
    cfg = config or ConfigMetodo1()
    tempos = detectar_batidas(amostras, taxa_amostragem, cfg)

    limiar = cfg.limiar_grupo_s
    if limiar is None:
        limiar = estimar_limiar_grupo(tempos)

    grupos = agrupar_batidas(tempos, limiar)
    bits = grupos_para_bits(grupos)
    quadros_bits, excedentes = montar_quadros(bits)

    return ResultadoMetodo1(
        tempos_batidas=tempos,
        grupos=grupos,
        bits=bits,
        quadros=[avaliar_quadro(q) for q in quadros_bits],
        bits_excedentes=excedentes,
        limiar_grupo_s=limiar,
    )


def formatar_resultado(resultado: ResultadoMetodo1) -> str:
    """Relatório em texto (terminal) do resultado da recepção."""
    simbolo = lambda b: "?" if b is None else str(b)  # noqa: E731
    linhas = [
        f"Batidas detectadas: {len(resultado.tempos_batidas)}",
        f"Limiar de separação entre bits: {resultado.limiar_grupo_s:.2f}s",
        "Bits decodificados: " + "".join(simbolo(b) for b in resultado.bits),
    ]
    for n, q in enumerate(resultado.quadros, start=1):
        dados = "".join(simbolo(b) for b in q.bits[:BITS_DADOS])
        char = f" '{q.caractere}'" if q.caractere else ""
        linhas.append(
            f"Quadro {n}: {dados} | paridade {simbolo(q.bits[BITS_DADOS])}"
            f" -> {q.status}{char}"
        )
    if resultado.bits_excedentes:
        extras = "".join(simbolo(b) for b in resultado.bits_excedentes)
        linhas.append(
            f"Aviso: {len(resultado.bits_excedentes)} bit(s) sobrando "
            f"({extras}) - quadro incompleto descartado."
        )
    if not resultado.quadros:
        linhas.append(f"[{STATUS_FALHA}] Nenhum quadro completo de 9 bits recebido.")
    else:
        linhas.append(f"Mensagem recebida: {resultado.mensagem!r}")
    return "\n".join(linhas)
