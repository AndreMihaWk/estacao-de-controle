# SMAC — Sistema de Monitoramento de Ambiente na Cloud

Projeto de extensão para a disciplina **Aplic. de Cloud, IoT e Indústria 4.0 em Python** (Estácio).

Uma **estação de controle** das centrais de ar das salas da faculdade. Pelo
site dá para **ligar e desligar** o ar de cada sala de forma remota,
**programar horário** e acompanhar a temperatura. Uma **webcam** verifica se
há pessoas na sala e, se ela estiver vazia, o sistema **desliga o ar sozinho**
por infravermelho e avisa no site.

> Enquanto o hardware (ESP32 + sensor + LED infravermelho) não chega, um
> **simulador em Python** faz o papel do dispositivo. Quando o ESP32 chegar,
> ele passa a chamar os mesmos endereços e o resto do sistema nem percebe.

## As salas

| Bloco | Salas | Bloco | Salas |
|-------|-------|-------|-------|
| A | 101 a 110 | D | 401 a 420 |
| B | 201 a 210 | E | 501 a 520 |
| C | 301 a 320 | F | 601 a 620 |

A letra do bloco define a centena (A = 100, B = 200...). Para mudar a
quantidade de salas, edite `BLOCOS` no `banco.py`.

## A regra da sala vazia

Com o ar ligado, a câmera verifica a sala:

1. **Viu pessoas** → só verifica de novo depois de **1 hora**.
2. **Não viu ninguém** → confere de novo depois de **30 minutos**.
3. **Não viu ninguém na conferência também** → desliga o ar por infravermelho
   e o site mostra o aviso "Desligado automaticamente".

A regra fica em `avaliar_presenca()` no `api.py`. Para demonstrar sem esperar,
troque `MINUTOS_COM_PESSOAS` e `MINUTOS_SEM_PESSOAS` por valores pequenos.

## Como o sistema é dividido

```
  simulador.py / ESP32  <--->  api.py (FastAPI)  <--->  site (dashboard.html)
  (infravermelho + sensor)     guarda / decide          liga, desliga, agenda
                                     ^
  camera.py (webcam)  ---------------+   usa banco.py + smac.db
  (conta as pessoas)
```

| Arquivo | Papel |
|---------|-------|
| `api.py` | o servidor: recebe dados, aplica as regras e a agenda |
| `banco.py` | todas as funções que falam com o banco `smac.db` |
| `codigos_ar.py` | banco de códigos: marca do ar → protocolo infravermelho |
| `templates/dashboard.html` | o site (estrutura e comportamento) |
| `static/dashboard_style.css` | a aparência do site |
| `simulador.py` | dispositivo de mentira de uma sala |
| `camera.py` | conta as pessoas pela webcam |
| `esp32/esp32_sala/esp32_sala.ino` | código do ESP32 de verdade (um por sala) |
| `ponte_usb.py` | liga o ESP32 à API pelo cabo USB, quando não há rede em comum |

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

**3. Abrir o site** no navegador: `http://127.0.0.1:8000`

**4. Ligar o simulador** em **outro** terminal (faz o papel do ESP32 da sala 101):

```bash
python simulador.py          # ou: python simulador.py 305
```

**5. Ligar a câmera** em **outro** terminal (vigia a sala 101 pela webcam):

```bash
python camera.py --teste     # mostra o que cada webcam do computador vê
python camera.py 101 1       # vigia a sala 101 usando a webcam 1
```

No site, clique na sala 101 e em **Ligar**: o simulador mostra o disparo do
infravermelho e a câmera faz a primeira verificação.

Para o ESP32 e outros computadores alcançarem a API pela rede, suba o
servidor com `uvicorn api:app --host 0.0.0.0`.

Se o ESP32 e o computador não estiverem na mesma rede (por exemplo: o PC no
celular pelo cabo USB e o ESP32 no hotspot Wi-Fi), use a ponte pelo cabo:
grave o ESP32 com `MODO_USB = true`, feche o Monitor Serial da Arduino IDE e rode

```bash
python ponte_usb.py          # ESP32 na COM6, sala 101
```

## Endereços da API (para explicar no relatório)

| Método | Endereço | Quem usa | Para que serve |
|--------|----------|----------|----------------|
| GET  | `/api/salas` | site | estado de todas as salas |
| POST | `/api/salas/{sala}/energia` | site | ligar / desligar o ar |
| PUT  | `/api/salas/{sala}/agenda` | site | programar horário |
| PUT  | `/api/salas/{sala}/equipamento` | site | nome do equipamento da sala |
| GET  | `/api/marcas` | site | banco de códigos: marcas de ar que o infravermelho controla |
| PUT  | `/api/salas/{sala}/marca` | site | escolher a marca do ar (código infravermelho) da sala |
| POST | `/api/salas/{sala}/teste-marca` | site | testar uma marca: o ESP32 manda ligar/desligar uma vez nela |
| PUT  | `/api/salas/{sala}/temperatura-ar` | site | temperatura que o ar deve manter (16 a 30 °C) |
| GET  | `/api/eventos` | site | avisos (o que o sistema fez) |
| GET  | `/api/salas/{sala}/comando` | ESP32 | "o ar deve estar ligado? em quantos graus? em qual código?" |
| POST | `/api/leituras` | ESP32 | enviar temperatura e umidade |
| GET  | `/api/salas/{sala}/verificacao` | câmera | "é hora de verificar?" |
| POST | `/api/salas/{sala}/presenca` | câmera | informar quantas pessoas viu |

Com o servidor no ar, a documentação automática da API fica em
`http://127.0.0.1:8000/docs` (um recurso pronto do FastAPI — ótimo print para o relatório).

## Ligação com os ODS (nota acadêmica)

- **ODS 7 — Energia limpa e acessível:** avisar quando a sala está quente ajuda
  a usar o ar-condicionado de forma consciente, evitando desperdício.
- **ODS 12 — Consumo e produção responsáveis:** monitorar o ambiente incentiva
  o uso responsável dos recursos da instituição.

## Próximo passo (evolução)

Gravar o `esp32/esp32_sala/esp32_sala.ino` em um ESP32 de verdade (ajustando Wi-Fi, sala
e a marca do ar-condicionado) e, depois, trocar o envio por HTTP pelo
protocolo **MQTT** (o mais usado em IoT).
