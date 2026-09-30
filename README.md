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

## Recepção do Método 1 (batidas → bits)

O módulo `camada_fisica.metodo1` converte as amostras capturadas pelo
microfone na sequência de bits do Método 1 e a envia para a verificação de
paridade par:

- **Mapear os picos sonoros**: `detectar_batidas()` calcula a envoltória do
  sinal (média móvel do módulo), aplica um limiar (o maior entre um valor
  absoluto e uma fração do pico da gravação) e registra o instante de cada
  batida. Regiões a menos de 80 ms uma da outra são a mesma batida
  (ressonância do impacto).
- **Padronizar bit 0 e bit 1**: `agrupar_batidas()` separa os símbolos pelos
  silêncios e `grupos_para_bits()` aplica a regra
  `silêncio + 1 batida + silêncio = 0` e
  `silêncio + 2 batidas + silêncio = 1`. Grupos com outra quantidade de
  batidas viram símbolo inválido (`?`) e reprovam o quadro.
- **Gerar a sequência de bits**: `montar_quadros()` divide os bits em quadros
  de 9 (8 dados + paridade); bits sobrando são descartados com aviso.
- **Enviar para a paridade par**: `avaliar_quadro()` usa
  `paridade.validar_paridade()` e marca cada quadro como **SUCESSO** ou
  **FALHA DE TRANSMISSÃO**.

`decodificar_metodo1(amostras, taxa)` executa todo o pipeline.

> **Calibração:** os tempos ficam em `ConfigMetodo1`. O limiar que separa
> "duas batidas do mesmo bit" de "bits diferentes" é estimado
> automaticamente a partir dos intervalos da gravação (com padrão de 0,6 s);
> ajuste `limiar_grupo_s`, `fracao_pico` e `limiar_absoluto` conforme o ritmo
> do vídeo de referência e o ruído da sala.

### Testando

```bash
pytest tests/test_metodo1.py -v      # sinais sintéticos, sem microfone
camada-fisica --metodo1              # grava até ENTER e decodifica
streamlit run app/streamlit_app.py   # seção "Recepção — Método 1"
```

## Emissão do Método 1 (bits → batidas)

O módulo `camada_fisica.audio_generation` converte a sequência de bits do Método 1 em um sinal acústico que pode ser reproduzido pelo alto-falante:

* **Gerar a batida:** `gerar_batida()` cria uma onda senoidal na frequência definida, aplicando *fade in* e *fade out* para reduzir descontinuidades no sinal.

* **Padronizar bit 0 e bit 1:** `bit_to_audio()` representa o bit `0` como `silêncio + 1 batida + silêncio` e o bit `1` como `silêncio + 2 batidas + silêncio`, com um intervalo entre as duas batidas.

* **Gerar a sequência de bits:** `bits_to_audio()` concatena os sinais correspondentes a cada bit, formando um único sinal acústico na ordem da sequência recebida.

* **Gerar a partir de texto:** `text_to_audio()` utiliza o `codec` para converter o texto em bytes e bits e, em seguida, gera o sinal acústico correspondente.

Os parâmetros de duração, frequência e taxa de amostragem são definidos no módulo `audio_generation.py`.

### Testando

```bash
pytest tests/test_audio_generation.py -v
```

Os testes verificam a geração dos bits `0` e `1`, a concatenação de sequências, os períodos de silêncio, a rejeição de valores inválidos e a geração de sinais a partir de sequências de bits.

## Emissão do Método 2 (bits → sinal 2-FSK)

O módulo `camada_fisica.sinal_generator_2FSK` converte a sequência de bits do Método 2 em um sinal acústico utilizando modulação 2-FSK, no qual cada bit é representado por uma frequência diferente:

* **Gerar o sinal de uma frequência:** `gerar_sinal_frequencia()` cria uma onda senoidal na frequência, duração, taxa de amostragem e amplitude definidas. A fase inicial e final são utilizadas para manter a continuidade entre diferentes símbolos.

* **Gerar um bit 2-FSK:** `gerar_bit_2fsk()` converte um único bit em seu respectivo sinal acústico, utilizando uma frequência para o bit `0` e outra para o bit `1`.

* **Gerar a sequência de bits:** `gerar_sinal_2fsk()` percorre a sequência de bits e concatena os sinais correspondentes, formando um único sinal acústico 2-FSK. A fase é mantida entre os símbolos para reduzir descontinuidades no sinal.

* **Configurar os parâmetros:** as frequências dos bits `0` e `1`, a duração dos símbolos, a taxa de amostragem e a amplitude podem ser configuradas para permitir testes com diferentes condições de transmissão.

Os parâmetros padrão utilizados são `1000 Hz` para o bit `0`, `2000 Hz` para o bit `1`, duração de `0,1 s` por símbolo, taxa de amostragem de `44100 Hz` e amplitude de `0,5`.

### Testando

```bash
pytest tests/test_sinal_generator_2FSK.py -v
```

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
