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
