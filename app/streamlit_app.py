# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Equipe Camada Física usando Som

import streamlit as st

from camada_fisica.audio_capture import (
    DEFAULT_SAMPLE_RATE,
    MAX_SAMPLE_RATE,
    MIN_SAMPLE_RATE,
    AudioCapture,
    MicrophoneUnavailableError,
    is_ready_for_reception,
)
from camada_fisica.audio_generation import text_to_audio
from camada_fisica.audio_output import play_audio
from camada_fisica.codec import bytes_to_bits, text_to_bytes
from camada_fisica.metodo1 import BITS_DADOS, decodificar_metodo1


st.set_page_config(
    page_title="Camada Física usando Som",
    page_icon="🔊",
    layout="wide",
)


# ---------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------

st.title("🔊 Camada Física usando Som")

st.markdown(
    """
### Trabalho de Redes de Computadores

Este projeto foi desenvolvido em 2026 pelos alunos da equipe para
estudar, na prática, a transmissão de informações pela Camada Física
do modelo ISO/OSI utilizando ondas sonoras como meio de comunicação.

O software pode funcionar como emissor e receptor, convertendo mensagens
em bits, transmitindo esses bits por sinais acústicos e reconstruindo os
dados recebidos.
"""
)

st.divider()

st.subheader("👥 Equipe")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        "#### [**Caio Botelho**](https://github.com/caiobotelho1)"
    )

with col2:
    st.markdown(
        "#### [**Isabela Kawashima**](https://github.com/isabelakawashima)"
    )

with col3:
    st.markdown(
        "#### [**Izabela Sanitá**](https://github.com/izabelasanita)"
    )

with col4:
    st.markdown(
        "#### [**Maria Mendes**](https://github.com/mendeseduarda)"
    )

st.divider()

st.subheader("📡 Métodos de comunicação")

metodo1_info, metodo2_info = st.columns(2)

with metodo1_info:
    st.markdown(
        """
### 🥁 Método 1 — Batidas

O Método 1 representa os bits por meio de eventos sonoros de impacto:

- **Bit 0:** silêncio + uma batida + silêncio;
- **Bit 1:** silêncio + duas batidas consecutivas + silêncio.

Cada grupo de 8 bits recebe um bit de paridade par, formando um quadro
de 9 bits. O receptor identifica as batidas capturadas pelo microfone,
reconstrói os bits e verifica se os dados foram recebidos corretamente.
"""
    )

with metodo2_info:
    st.markdown(
        """
### 🎵 Método 2 — Em desenvolvimento

O Método 2 será uma segunda técnica de modulação acústica com o objetivo
de alcançar uma taxa de transmissão maior.

A técnica de modulação, os parâmetros do sinal e o mecanismo de detecção
de erros ainda estão em definição pela equipe.
"""
    )

st.divider()

aba_metodo1, aba_metodo2 = st.tabs(
    [
        "🥁 Método 1 — Transmissão e Recepção",
        "🎵 Método 2 — Em desenvolvimento",
    ]
)


# ---------------------------------------------------------------------
# Método 1
# ---------------------------------------------------------------------

with aba_metodo1:
    st.header("🥁 Método 1 — Batidas")

    st.info(
        """
        Neste método, cada bit é representado por batidas sonoras:
        bit 0 corresponde a uma batida e bit 1 corresponde a duas batidas
        consecutivas.
        """
    )

    emissao, recepcao = st.columns(2)

    # -------------------------------------------------------------
    # Emissão
    # -------------------------------------------------------------

    with emissao:
        st.subheader("📤 Emissão")

        mensagem_envio = st.text_area(
            "Mensagem para transmitir",
            placeholder="Digite uma mensagem, por exemplo: OI",
            key="mensagem_envio",
        )

        if st.button(
            "🔊 Transmitir mensagem",
            type="primary",
            key="botao_transmitir",
        ):
            if not mensagem_envio:
                st.warning("Digite uma mensagem antes de transmitir.")
            else:
                try:
                    dados = text_to_bytes(mensagem_envio)
                    bits = bytes_to_bits(dados)
                    sinal = text_to_audio(mensagem_envio)

                    st.write(
                        f"**Mensagem:** `{mensagem_envio}`"
                    )
                    st.write(
                        f"**Quantidade de bits:** {len(bits)}"
                    )

                    st.write("**Bits transmitidos:**")
                    st.code(
                        "".join(str(bit) for bit in bits),
                        language="text",
                    )

                    st.write(
                        f"**Amostras de áudio geradas:** {len(sinal)}"
                    )

                    play_audio(
                        sinal,
                        sample_rate=44_100,
                    )

                    st.success(
                        "✅ Mensagem transmitida com sucesso."
                    )

                except Exception as exc:
                    st.error(
                        f"Erro durante a transmissão: {exc}"
                    )

    # -------------------------------------------------------------
    # Recepção
    # -------------------------------------------------------------

    with recepcao:
        st.subheader("🎙️ Recepção")

        st.write(
            "Inicie a captura, faça as batidas do Método 1 e encerre "
            "a captura para decodificar a mensagem."
        )

        if "audio_capture" not in st.session_state:
            st.session_state.audio_capture = AudioCapture()

        if "captured_samples" not in st.session_state:
            st.session_state.captured_samples = None

        capture: AudioCapture = st.session_state.audio_capture

        sample_rate = st.slider(
            "Taxa de amostragem (Hz)",
            min_value=MIN_SAMPLE_RATE,
            max_value=MAX_SAMPLE_RATE,
            value=DEFAULT_SAMPLE_RATE,
            step=1_000,
            disabled=capture.is_capturing,
            key="sample_rate_metodo1",
        )

        iniciar, encerrar = st.columns(2)

        with iniciar:
            if st.button(
                "▶️ Iniciar captura",
                disabled=capture.is_capturing,
                key="iniciar_captura",
            ):
                try:
                    capture.set_sample_rate(sample_rate)
                    AudioCapture.check_microphone_access()
                    capture.start()
                    st.session_state.captured_samples = None
                    st.rerun()

                except MicrophoneUnavailableError as exc:
                    st.error(
                        f"Não foi possível acessar o microfone: {exc}"
                    )

                except ValueError as exc:
                    st.error(str(exc))

        with encerrar:
            if st.button(
                "⏹️ Encerrar captura",
                disabled=not capture.is_capturing,
                key="encerrar_captura",
            ):
                st.session_state.captured_samples = capture.stop()
                st.rerun()

        if capture.is_capturing:
            st.warning(
                "🔴 Capturando áudio. Faça as batidas e depois "
                "encerre a captura."
            )

        samples = st.session_state.captured_samples

        if samples is not None:
            st.write(
                f"**Amostras capturadas:** {len(samples)}"
            )
            st.write(
                f"**Duração:** "
                f"{capture.get_capture_duration():.2f} segundos"
            )

            if is_ready_for_reception(samples):
                st.success(
                    "✅ Captura realizada. "
                    "Os dados estão prontos para decodificação."
                )

                resultado = decodificar_metodo1(
                    samples,
                    capture.config.sample_rate,
                )

                simbolo = (
                    lambda bit: "?"
                    if bit is None
                    else str(bit)
                )

                st.write(
                    f"**Batidas detectadas:** "
                    f"{len(resultado.tempos_batidas)}"
                )

                bits_decodificados = "".join(
                    simbolo(bit)
                    for bit in resultado.bits
                )

                st.write(
                    f"**Bits decodificados:** "
                    f"`{bits_decodificados or '(nenhum)'}`"
                )

                for numero, quadro in enumerate(
                    resultado.quadros,
                    start=1,
                ):
                    dados = "".join(
                        simbolo(bit)
                        for bit in quadro.bits[:BITS_DADOS]
                    )

                    paridade = simbolo(
                        quadro.bits[BITS_DADOS]
                    )

                    texto_quadro = (
                        f"Quadro {numero}: `{dados}` | "
                        f"paridade `{paridade}` → "
                        f"**{quadro.status}**"
                    )

                    if quadro.valido:
                        st.success(texto_quadro)
                    else:
                        st.error(texto_quadro)

                if resultado.bits_excedentes:
                    st.warning(
                        f"{len(resultado.bits_excedentes)} bit(s) "
                        "sobrando: quadro incompleto descartado."
                    )

                if resultado.quadros:
                    st.write(
                        f"**Mensagem recebida:** "
                        f"`{resultado.mensagem}`"
                    )
                else:
                    st.error(
                        "❌ FALHA DE TRANSMISSÃO: nenhum quadro "
                        "completo foi recebido."
                    )

            else:
                st.warning(
                    "⚠️ A captura não contém um sinal de áudio válido."
                )


# ---------------------------------------------------------------------
# Método 2
# ---------------------------------------------------------------------

with aba_metodo2:
    st.header("🎵 Método 2 — Em desenvolvimento")

    st.info(
        """
        O segundo método de transmissão acústica ainda está sendo
        desenvolvido pela equipe.
        """
    )

    st.markdown(
        """
        Nesta etapa, a equipe ainda definirá:

        - a técnica de modulação;
        - as frequências ou características dos sinais;
        - a taxa de transmissão;
        - o mecanismo de detecção de erros;
        - o funcionamento do emissor e do receptor.
        """
    )

    st.warning(
        "⚠️ Esta área ainda não está disponível para transmissão."
    )