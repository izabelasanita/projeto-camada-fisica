import streamlit as st


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