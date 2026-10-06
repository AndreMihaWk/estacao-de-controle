# SMAC — Sistema de Monitoramento de Ambiente na Cloud

Projeto de extensão para a disciplina **Aplic. de Cloud, IoT e Indústria 4.0 em Python** (Estácio).

Um dispositivo IoT mede a **temperatura** e a **umidade** de uma sala e envia
para a nuvem. Um servidor em Python **guarda** os dados, **decide** se o
ambiente está quente demais e mostra tudo num **painel** que atualiza sozinho.
Quando a temperatura passa do limite, o painel dispara um **alerta**.

> Enquanto o hardware (ESP32 + sensor) não chega, um **simulador em Python**
> faz o papel do dispositivo. Assim dá para construir e testar o sistema
> inteiro hoje, sem comprar nada. Quando o ESP32 chegar, ele passa a chamar o
> mesmo endpoint e o resto do sistema nem percebe a diferença.

## Como o sistema é dividido

```
  simulador.py            api.py (FastAPI)            dashboard.html
  (o dispositivo)  --->   recebe / guarda / decide -> painel no navegador
                          usa banco.py + smac.db
```

| Camada da matéria | O que faz o papel no projeto |
|-------------------|------------------------------|
| **IoT**           | `simulador.py` (hoje) → ESP32 + sensor (depois) |
| **Cloud**         | `api.py` (FastAPI) + banco de dados `smac.db`   |
| **Indústria 4.0** | a regra automática `avaliar_ambiente()` que gera o alerta |
| **Python**        | tudo, do começo ao fim |

## Como rodar (passo a passo)

Precisa ter o **Python 3.10+** instalado.

**1. Instalar as bibliotecas** (uma vez só):

```bash
pip install -r requirements.txt
```

**2. Ligar o servidor** (deixe este terminal aberto):

```bash
uvicorn api:app --reload
```

**3. Abrir o painel** no navegador:

```
http://127.0.0.1:8000
```

**4. Ligar o simulador** em **outro** terminal (para os dados começarem a chegar):

```bash
python simulador.py
```

Pronto: o painel começa a se atualizar a cada 3 segundos. Para ver o **alerta**
disparar, espere o simulador "esquentar" a sala, ou abra o `api.py` e baixe o
`LIMITE_TEMPERATURA` para um valor mais baixo (ex.: `25.0`).

## Endereços da API (para explicar no relatório)

| Método | Endereço | Para que serve |
|--------|----------|----------------|
| POST | `/api/leituras` | o dispositivo envia uma medição |
| GET  | `/api/status`   | o painel pega a situação atual da sala |
| GET  | `/api/leituras` | o painel pega o histórico p/ o gráfico |
| GET  | `/`             | abre o painel |

Com o servidor no ar, a documentação automática da API fica em
`http://127.0.0.1:8000/docs` (um recurso pronto do FastAPI — ótimo print para o relatório).

## Ligação com os ODS (nota acadêmica)

- **ODS 7 — Energia limpa e acessível:** avisar quando a sala está quente ajuda
  a usar o ar-condicionado de forma consciente, evitando desperdício.
- **ODS 12 — Consumo e produção responsáveis:** monitorar o ambiente incentiva
  o uso responsável dos recursos da instituição.

## Próximo passo (evolução)

Trocar o envio por HTTP pelo protocolo **MQTT** (o mais usado em IoT) e, por
fim, substituir o simulador pelo **ESP32** de verdade. A estrutura já está
pronta para isso — só muda quem envia os dados.
