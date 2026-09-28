# 🔊 Camada Física usando Som

Projeto desenvolvido para a disciplina de **Redes de Computadores**, com o objetivo de explorar na prática conceitos relacionados à **Camada Física do modelo ISO/OSI**.

O projeto consiste no desenvolvimento de um sistema de comunicação digital capaz de **transmitir e receber informações binárias utilizando ondas sonoras como meio físico de transmissão**.

Serão implementados dois métodos de comunicação acústica: um baseado em **eventos sonoros por impacto (batidas)** e um segundo método de modulação acústica voltado à obtenção de uma maior taxa de transmissão de dados.

>  **Projeto em desenvolvimento**
>
> Este repositório ainda está em fase de desenvolvimento. A implementação, documentação técnica, resultados dos experimentos e demonstração serão adicionados conforme o andamento do projeto.

## Desenvolvimento local

O projeto utiliza Python 3.9 ou superior. A dependência de áudio fica opcional neste início para manter a estrutura independente da escolha do segundo método.

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
camada-fisica --check
```

### Estrutura

```text
src/camada_fisica/  código do pacote
tests/               testes automatizados
pyproject.toml       configuração, dependências e ferramentas
app/                 interface em streamlit
```

O segundo método de modulação será definido posteriormente; por isso, a base não assume FSK, ASK, PSK ou outra técnica.

## Captura de áudio (Microfone)

O módulo `camada_fisica.audio_capture` implementa o acesso ao microfone e a
captura das amostras de áudio brutas que alimentam os módulos de recepção
(decodificação dos Métodos 1 e 2):

- **Configurar acesso ao microfone**: `AudioCapture.check_microphone_access()`
  verifica se há um dispositivo de entrada disponível e retorna suas
  informações (nome, canais, taxa padrão), levantando
  `MicrophoneUnavailableError` caso o microfone não esteja acessível.
- **Definir a taxa de amostragem inicial**: `AudioCapture.set_sample_rate(hz)`
  configura a taxa (padrão: `44100 Hz`), validando a faixa aceitável
  (`8000`–`96000 Hz`) antes do início da captura.
- **Capturar amostras de áudio / iniciar e encerrar a captura**:
  `capture.start()` inicia a gravação em um `sounddevice.InputStream`;
  `capture.stop()` encerra a captura e retorna as amostras acumuladas
  (`numpy.ndarray`). Há também `capture.capture_for(segundos)` para uma
  captura bloqueante de duração fixa.
- **Verificar se os dados podem ser usados pela recepção**:
  `is_ready_for_reception(amostras)` confirma que os dados não estão vazios,
  não contêm `NaN`/`inf` e não são silêncio total — sinalizando `SUCESSO`
  ou `FALHA DE CAPTURA` antes de repassar os dados aos decodificadores.

Para testes automatizados (sem hardware de áudio), a classe aceita um
`stream_factory` que injeta um backend falso no lugar do PortAudio real —
veja `tests/test_audio_capture.py`.

### Testando manualmente pelo terminal

```bash
camada-fisica --test-mic --duration 3 --sample-rate 44100
```

### Testando pela interface Streamlit

```bash
streamlit run app/streamlit_app.py
```

Na seção **"🎙️ Captura de áudio (Microfone) — Recepção"**, ajuste a taxa de
amostragem, clique em **Iniciar captura**, emita o sinal sonoro desejado e
clique em **Encerrar captura** para ver as amostras, a duração e o status de
validação (pronto ou não para a recepção).

## Detecção de erros por paridade (Método 1)

O módulo `camada_fisica.paridade` implementa o mecanismo de detecção de
erros por paridade par utilizado nos quadros do Método 1. Cada quadro é
formado por 8 bits de dados e 1 bit de paridade:

- **Calcular o bit de paridade**: `calcular_paridade(bits)` recebe os 8 bits
  de dados e calcula o bit de paridade par. Quando a quantidade de bits `1`
  nos dados é par, a paridade é `0`; quando é ímpar, a paridade é `1`.
- **Montar o quadro de 9 bits**: `montar_quadro(bits)` utiliza os 8 bits de
  dados e adiciona o bit de paridade calculado, formando o quadro completo
  de 9 bits.
- **Validar a paridade de um quadro recebido**: `validar_paridade(quadro)`
  separa os 8 bits de dados do bit de paridade recebido, calcula a paridade
  esperada e compara os dois valores.
- **Identificar quadros válidos e corrompidos**: a validação retorna `True`
  quando a paridade recebida está correta e `False` quando há divergência,
  permitindo identificar se o quadro está válido ou corrompido.

Para testes automatizados, foram criados testes para diferentes sequências
de 8 bits, verificando o cálculo da paridade, a montagem dos quadros e a
validação de quadros válidos e corrompidos. Os testes estão disponíveis em
`tests/test_paridade.py`.

## Equipe

| Integrante | GitHub |
| --- | --- |
| Caio Botelho | [@caiobotelho1](https://github.com/caiobotelho1) |
| Isabela Kawashima | [@isabelakawashima](https://github.com/isabelakawashima) |
| Izabela Sanitá | [@izabelasanita](https://github.com/izabelasanita) |
| Maria Mendes | [@mendeseduarda](https://github.com/mendeseduarda) |

## Licença

Este projeto é distribuído sob a **MIT License**.

Consulte o arquivo [`LICENSE`](LICENSE) para mais informações.
