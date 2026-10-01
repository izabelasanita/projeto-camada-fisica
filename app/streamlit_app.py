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
from camada_fisica.audio_generation import (
    text_to_audio,
    text_to_frame_bits
)
from camada_fisica.audio_output import play_audio

from camada_fisica.metodo1 import (
    BITS_DADOS,
    ReceptorMetodo1TempoReal
    )

from camada_fisica.codec import text_to_bytes
from camada_fisica.crc8 import montar_quadro as montar_quadro_crc8
from camada_fisica.codec import bytes_to_bits
from camada_fisica.metodo2 import decodificar_metodo2, formatar_resultado as formatar_resultado_metodo2
from camada_fisica.sinal_generator_2FSK import (
    DURACAO_SIMBOLO as DEFAULT_DURACAO_SIMBOLO,
    FREQUENCIA_0 as DEFAULT_FREQUENCIA_0,
    FREQUENCIA_1 as DEFAULT_FREQUENCIA_1,
    gerar_sinal_2fsk,
)


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
### 🎵 Método 2 — 2-FSK

O Método 2 utiliza modulação por chaveamento de frequência (2-FSK):
cada bit é representado por um tom de frequência diferente, mantido
por uma duração fixa (o "símbolo").

- **Bit 0:** tom na frequência configurada para o bit 0;
- **Bit 1:** tom na frequência configurada para o bit 1.

Os dados (texto) seguidos de 1 byte de CRC-8 são transmitidos como uma
sequência de símbolos. O receptor identifica a frequência dominante em
cada janela de tempo (algoritmo de Goertzel) e verifica a integridade
dos dados recebidos pelo CRC-8.
"""
    )

st.divider()

aba_metodo1, aba_metodo2 = st.tabs(
    [
        "🥁 Método 1 — Transmissão e Recepção",
        "🎵 Método 2 — Transmissão e Recepção",
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
                    bits = text_to_frame_bits(mensagem_envio)
                    sinal = text_to_audio(mensagem_envio)

                    st.write(
                        f"**Mensagem:** `{mensagem_envio}`"
                    )
                    st.write(
                        f"**Quantidade de bits transmitidos:** {len(bits)}"
                    )

                    st.write("**Quadros transmitidos:**")

                    for inicio in range(0, len(bits), 9):
                        quadro = bits[inicio:inicio + 9]

                        dados_quadro = quadro[:8]
                        paridade = quadro[8]

                        st.code(
                            f"{''.join(str(bit) for bit in dados_quadro)} | {paridade}",
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
            "Inicie a captura e faça as batidas do Método 1. "
            "Os bits identificados aparecerão em tempo real."
        )

        if "audio_capture" not in st.session_state:
            st.session_state.audio_capture = AudioCapture()

        if "captured_samples" not in st.session_state:
            st.session_state.captured_samples = None

        if "resultado_metodo1" not in st.session_state:
            st.session_state.resultado_metodo1 = None

        if "receptor_metodo1_live" not in st.session_state:
            st.session_state.receptor_metodo1_live = None

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

                    st.session_state.receptor_metodo1_live = (
                        ReceptorMetodo1TempoReal(
                            sample_rate
                        )
                    )

                    st.session_state.resultado_metodo1 = None
                    st.session_state.captured_samples = None

                    capture.start()

                    st.rerun()

                except MicrophoneUnavailableError as exc:
                    st.error(
                        "Não foi possível acessar o "
                        f"microfone: {exc}"
                    )

                except ValueError as exc:
                    st.error(str(exc))

        with encerrar:
            if st.button(
                "⏹️ Encerrar captura",
                disabled=not capture.is_capturing,
                key="encerrar_captura",
            ):
                samples = capture.stop()

                st.session_state.captured_samples = samples

                receptor = (
                    st.session_state.receptor_metodo1_live
                )

                if receptor is None:
                    receptor = ReceptorMetodo1TempoReal(
                        capture.config.sample_rate
                    )

                    st.session_state.receptor_metodo1_live = (
                        receptor
                    )

                st.session_state.resultado_metodo1 = (
                    receptor.processar(
                        samples,
                        finalizar=True,
                    )
                )

                st.rerun()

        def mostrar_resultado_metodo1(resultado):
            simbolo = (
                lambda bit: "?"
                if bit is None
                else str(bit)
            )

            bits_decodificados = "".join(
                simbolo(bit)
                for bit in resultado.bits
            )

            st.write("**Bits identificados:**")

            st.code(
                bits_decodificados or "(nenhum)",
                language="text",
            )

            st.caption(
                f"{len(resultado.bits)} bit(s) "
                "confirmado(s)"
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

            if resultado.quadros:
                st.write(
                    "**Mensagem recebida:** "
                    f"`{resultado.mensagem}`"
                )

        run_every = (
            0.2
            if capture.is_capturing
            else None
        )

        @st.fragment(run_every=run_every)
        def painel_recepcao_tempo_real():
            if capture.is_capturing:
                samples = (
                    capture.get_captured_samples()
                )

                receptor = (
                    st.session_state
                    .receptor_metodo1_live
                )

                st.warning(
                    "🔴 Capturando áudio..."
                )

                st.write(
                    f"**Amostras capturadas:** "
                    f"{len(samples)}"
                )

                duracao = (
                    len(samples)
                    / capture.config.sample_rate
                )

                st.write(
                    f"**Duração:** "
                    f"{duracao:.2f} segundos"
                )

                if (
                    receptor is not None
                    and len(samples) > 0
                ):
                    resultado = receptor.processar(
                        samples
                    )

                    mostrar_resultado_metodo1(
                        resultado
                    )

                else:
                    st.write(
                        "**Bits identificados:**"
                    )

                    st.code(
                        "(aguardando sinal)",
                        language="text",
                    )

            else:
                resultado = (
                    st.session_state
                    .resultado_metodo1
                )

                samples = (
                    st.session_state
                    .captured_samples
                )

                if (
                    resultado is not None
                    and samples is not None
                ):
                    st.write(
                        f"**Amostras capturadas:** "
                        f"{len(samples)}"
                    )

                    duracao = (
                        len(samples)
                        / capture.config.sample_rate
                    )

                    st.write(
                        f"**Duração:** "
                        f"{duracao:.2f} segundos"
                    )

                    if is_ready_for_reception(
                        samples
                    ):
                        st.success(
                            "✅ Captura encerrada."
                        )

                        mostrar_resultado_metodo1(
                            resultado
                        )

                    else:
                        st.warning(
                            "⚠️ A captura não contém "
                            "um sinal de áudio válido."
                        )

        painel_recepcao_tempo_real()

# ---------------------------------------------------------------------
# Método 2
# ---------------------------------------------------------------------

with aba_metodo2:
    st.header("🎵 Método 2 — 2-FSK")

    st.info(
        """
        Neste método, cada bit é representado por um tom de frequência
        diferente (bit 0 e bit 1 têm frequências próprias), mantido pela
        duração de símbolo configurada. Os dados são verificados com
        CRC-8 ao final da recepção.
        """
    )

    st.caption(
        "As frequências e a duração do símbolo abaixo valem tanto para a "
        "emissão quanto para a recepção — configure-as antes de transmitir "
        "ou capturar."
    )

    freq0_m2, freq1_m2, duracao_m2 = st.columns(3)

    with freq0_m2:
        frequencia_0_m2 = st.number_input(
            "Frequência do bit 0 (Hz)",
            min_value=100.0,
            max_value=20_000.0,
            value=float(DEFAULT_FREQUENCIA_0),
            step=100.0,
            key="frequencia_0_metodo2",
        )

    with freq1_m2:
        frequencia_1_m2 = st.number_input(
            "Frequência do bit 1 (Hz)",
            min_value=100.0,
            max_value=20_000.0,
            value=float(DEFAULT_FREQUENCIA_1),
            step=100.0,
            key="frequencia_1_metodo2",
        )

    with duracao_m2:
        duracao_simbolo_m2 = st.number_input(
            "Duração do símbolo (s)",
            min_value=0.01,
            max_value=1.0,
            value=float(DEFAULT_DURACAO_SIMBOLO),
            step=0.01,
            key="duracao_simbolo_metodo2",
        )

    if frequencia_0_m2 == frequencia_1_m2:
        st.error(
            "A frequência do bit 0 e a frequência do bit 1 devem ser "
            "diferentes para que a recepção consiga distingui-las."
        )

    emissao_m2, recepcao_m2 = st.columns(2)

    # -------------------------------------------------------------
    # Emissão
    # -------------------------------------------------------------

    with emissao_m2:
        st.subheader("📤 Emissão")

        mensagem_envio_m2 = st.text_area(
            "Mensagem para transmitir",
            placeholder="Digite uma mensagem, por exemplo: OI",
            key="mensagem_envio_metodo2",
        )

        if st.button(
            "🎵 Transmitir mensagem",
            type="primary",
            key="botao_transmitir_metodo2",
            disabled=frequencia_0_m2 == frequencia_1_m2,
        ):
            if not mensagem_envio_m2:
                st.warning("Digite uma mensagem antes de transmitir.")
            else:
                try:
                    quadro = montar_quadro_crc8(
                        text_to_bytes(mensagem_envio_m2)
                    )
                    bits = bytes_to_bits(quadro)

                    sinal = gerar_sinal_2fsk(
                        bits,
                        frequencia_0=frequencia_0_m2,
                        frequencia_1=frequencia_1_m2,
                        duracao=duracao_simbolo_m2,
                    )

                    st.write(f"**Mensagem:** `{mensagem_envio_m2}`")
                    st.write(f"**Bytes (dados + CRC-8):** {quadro.hex(' ')}")
                    st.write(f"**Quantidade de bits transmitidos:** {len(bits)}")
                    st.write(f"**Amostras de áudio geradas:** {len(sinal)}")

                    play_audio(sinal, sample_rate=44_100)

                    st.success("✅ Mensagem transmitida com sucesso.")

                except Exception as exc:
                    st.error(f"Erro durante a transmissão: {exc}")

    # -------------------------------------------------------------
    # Recepção
    # -------------------------------------------------------------

    with recepcao_m2:
        st.subheader("🎙️ Recepção")

        st.write(
            "Inicie a captura enquanto o Método 2 é transmitido "
            "(pela equipe ou por outro computador)."
        )

        if "audio_capture_metodo2" not in st.session_state:
            st.session_state.audio_capture_metodo2 = AudioCapture()

        if "captured_samples_metodo2" not in st.session_state:
            st.session_state.captured_samples_metodo2 = None

        capture_m2: AudioCapture = st.session_state.audio_capture_metodo2

        iniciar_m2, encerrar_m2 = st.columns(2)

        with iniciar_m2:
            if st.button(
                "▶️ Iniciar captura",
                disabled=capture_m2.is_capturing,
                key="iniciar_captura_metodo2",
            ):
                try:
                    capture_m2.set_sample_rate(DEFAULT_SAMPLE_RATE)
                    AudioCapture.check_microphone_access()
                    st.session_state.captured_samples_metodo2 = None
                    capture_m2.start()
                except MicrophoneUnavailableError as exc:
                    st.error(f"Não foi possível acessar o microfone: {exc}")
                except ValueError as exc:
                    st.error(str(exc))

        with encerrar_m2:
            if st.button(
                "⏹️ Encerrar captura",
                disabled=not capture_m2.is_capturing,
                key="encerrar_captura_metodo2",
            ):
                st.session_state.captured_samples_metodo2 = capture_m2.stop()

        if capture_m2.is_capturing:
            st.warning("🔴 Capturando áudio...")

        samples_m2 = st.session_state.captured_samples_metodo2

        if samples_m2 is not None:
            st.write(f"**Amostras capturadas:** {len(samples_m2)}")

            if not is_ready_for_reception(samples_m2):
                st.warning(
                    "⚠️ A captura não contém um sinal de áudio válido."
                )
            else:
                resultado_m2 = decodificar_metodo2(
                    samples_m2,
                    frequencia_0=frequencia_0_m2,
                    frequencia_1=frequencia_1_m2,
                    duracao_simbolo=duracao_simbolo_m2,
                    taxa_amostragem=capture_m2.config.sample_rate,
                )

                simbolo_m2 = lambda bit: "?" if bit is None else str(bit)  # noqa: E731
                bits_m2 = "".join(simbolo_m2(bit) for bit in resultado_m2["bits"])

                st.write("**Bits identificados:**")
                st.code(bits_m2 or "(nenhum)", language="text")

                if resultado_m2.get("bits_recuperados_por_crc"):
                    st.info(
                        "ℹ️ A captura terminou antes do último bit do CRC-8. "
                        "O bit faltante foi recuperado de forma determinística "
                        "pela validação do CRC."
                    )

                if resultado_m2["bits_sobrando"]:
                    st.warning(
                        f"{len(resultado_m2['bits_sobrando'])} bit(s) "
                        "sobrando: byte incompleto descartado."
                    )

                texto_status_m2 = f"Status: **{resultado_m2['status']}**"

                if resultado_m2["valido"]:
                    st.success(texto_status_m2)
                    st.write(
                        f"**Mensagem recebida:** `{resultado_m2['mensagem']}`"
                    )
                else:
                    st.error(texto_status_m2)
