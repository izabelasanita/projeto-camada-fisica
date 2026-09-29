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
from camada_fisica.metodo1 import (
    BITS_DADOS,
    decodificar_metodo1,
)
from camada_fisica.audio_generation import text_to_audio
from camada_fisica.audio_output import play_audio
from camada_fisica.codec import text_to_bytes, bytes_to_bits

st.set_page_config(
    page_title="Camada Física usando Som",
    page_icon="🔊",
)

st.title("🔊 Camada Física usando Som")
st.write(
    "Interface inicial para o projeto de comunicação digital por ondas sonoras."
)

st.subheader("Teste da aplicação")

mensagem = st.text_input(
    "Digite uma mensagem:",
    placeholder="Exemplo: Olá, mundo!",
)

if st.button("Enviar"):
    if mensagem:
        st.success(f"Mensagem recebida: {mensagem}")
    else:
        st.warning("Digite uma mensagem antes de enviar.")

st.divider()
st.subheader("🎙️ Captura de áudio (Microfone) — Recepção")
st.caption(
    "Concede acesso ao microfone e captura as amostras de áudio que serão "
    "usadas pelos módulos de recepção (Método 1 - batidas, e Método 2)."
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
    help="Define a taxa de amostragem inicial da captura. Não pode ser "
    "alterada durante uma captura em andamento.",
)

col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Iniciar captura", disabled=capture.is_capturing):
        try:
            capture.set_sample_rate(sample_rate)
            AudioCapture.check_microphone_access()
            capture.start()
            st.session_state.captured_samples = None
        except MicrophoneUnavailableError as exc:
            st.error(f"Não foi possível acessar o microfone: {exc}")
        except ValueError as exc:
            st.error(str(exc))

with col2:
    if st.button("⏹️ Encerrar captura", disabled=not capture.is_capturing):
        samples = capture.stop()
        st.session_state.captured_samples = samples

if capture.is_capturing:
    st.info("🔴 Gravando... fale, bata palmas ou use o padrão de batidas do Método 1.")

samples = st.session_state.captured_samples
if samples is not None:
    n_samples = len(samples)
    duration = capture.get_capture_duration()
    st.write(f"**Amostras capturadas:** {n_samples}")
    st.write(f"**Duração da captura:** {duration:.2f} s")

    if n_samples > 0:
        try:
            # Renderizar todas as amostras brutas (ex.: 132k pontos em 3s a
            # 44100 Hz) deixa o gráfico no navegador extremamente lento.
            # Por isso, reduzimos (downsample) apenas para fins de
            # visualização — as amostras reais usadas pela recepção
            # continuam intactas em `samples`.
            max_points = 2_000
            if n_samples > max_points:
                step = n_samples // max_points
                chart_data = samples[::step]
            else:
                chart_data = samples
            st.line_chart(chart_data)
        except Exception:  # pragma: no cover - apenas visual
            pass

    if is_ready_for_reception(samples):
        st.success(
            "✅ SUCESSO: dados capturados são válidos e estão prontos para "
            "serem processados pelos módulos de recepção."
        )
    else:
        st.warning(
            "⚠️ FALHA DE CAPTURA: nenhum sinal de áudio válido foi detectado "
            "(silêncio, dados vazios ou inválidos). Tente novamente."
        )

    if is_ready_for_reception(samples):
        st.divider()
        st.subheader("🥁 Recepção — Método 1 (batidas)")
        resultado = decodificar_metodo1(samples, capture.config.sample_rate)
        simbolo = lambda b: "?" if b is None else str(b)  # noqa: E731

        st.write(f"**Batidas detectadas:** {len(resultado.tempos_batidas)}")
        st.write(
            "**Bits decodificados:** "
            f"`{''.join(simbolo(b) for b in resultado.bits) or '(nenhum)'}`"
        )

        for n, quadro in enumerate(resultado.quadros, start=1):
            dados = "".join(simbolo(b) for b in quadro.bits[:BITS_DADOS])
            texto = (
                f"Quadro {n}: `{dados}` | paridade "
                f"`{simbolo(quadro.bits[BITS_DADOS])}` → **{quadro.status}**"
            )
            if quadro.valido:
                st.success(texto)
            else:
                st.error(texto)

        if resultado.bits_excedentes:
            st.warning(
                f"{len(resultado.bits_excedentes)} bit(s) sobrando: quadro "
                "incompleto descartado."
            )
        if resultado.quadros:
            st.write(f"**Mensagem recebida:** {resultado.mensagem!r}")
        else:
            st.warning("FALHA DE TRANSMISSÃO: nenhum quadro completo de 9 bits.")

st.subheader("📡 Emissão — Método 1")

st.write(
    "Digite uma mensagem para convertê-la em bits e transmitir "
    "por meio de sinais acústicos."
)

mensagem = st.text_input(
    "Mensagem",
    placeholder="Digite a mensagem que deseja transmitir..."
)

if st.button("Transmitir", type="primary"):
    if not mensagem:
        st.warning("Digite uma mensagem antes de transmitir.")
    else:
        try:
            # Texto → bytes → bits
            dados = text_to_bytes(mensagem)
            bits = bytes_to_bits(dados)

            st.subheader("Dados da transmissão")

            st.write(f"**Mensagem:** {mensagem}")
            st.write(f"**Quantidade de bits:** {len(bits)}")

            st.code(
                "".join(str(bit) for bit in bits),
                language="text"
            )

            # Bits → sinal acústico
            sinal = text_to_audio(mensagem)

            st.write(f"**Amostras geradas:** {len(sinal)}")

            # Reprodução pelo alto-falante
            play_audio(
                sinal,
                sample_rate=44_100
            )

            st.success("Transmissão concluída!")

        except Exception as exc:
            st.error(f"Erro durante a transmissão: {exc}")
