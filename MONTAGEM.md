# Planejamento de montagem — dispositivo da sala (ESP32)

Este documento é o roteiro para montar o **dispositivo de uma sala**: o ESP32
que mede a temperatura e liga/desliga o ar-condicionado por infravermelho.
Cada etapa tem um **critério de pronto**, como no `BACKLOG.md`: só marque
quando conseguir demonstrar aquilo funcionando.

---

## 1. O que o dispositivo faz

```
  sensor DHT22 ──► ESP32 ──► LED infravermelho ──► ar-condicionado
                    │
                    │  cabo USB (hoje)  ou  Wi-Fi (no futuro)
                    ▼
                 api.py  ◄──►  site (painel)
```

1. Lê a **temperatura e a umidade** no DHT22 a cada 5 segundos e envia para a API.
2. Pergunta para a API se o ar **deve estar ligado**.
3. Quando a resposta muda, dispara o **LED infravermelho**, como o controle remoto faria.

---

## 2. Lista de materiais

| Item | Qtd. | Situação | Observação |
|------|------|----------|------------|
| ESP32 DevKit (30 pinos, chip USB CH340) | 1 | ✅ tenho | ESP32-D0WD-V3, MAC `a0:dd:6c:03:34:a8` |
| Cabo USB de **dados** | 1 | ✅ tenho | cabo só de carga não funciona |
| Protoboard | 1 | ✅ tenho | |
| Sensor **DHT22** (módulo de 3 pinos) | 1 | ✅ tenho | já tem o resistor interno |
| LED infravermelho | 1 | ✅ tenho | retirado de um controle remoto |
| Fios jumper macho-macho | ~8 | ✅ tenho | |
| **Transistor 2N2222** | 1 | ✅ comprado | pernas E-B-C (lado reto para você); com o ESP32 no topo, lado reto para a direita |
| **Resistor de 1 kΩ** (marrom-preto-vermelho) | 1 | ✅ comprado | base do transistor |
| **Resistor de 22 Ω** (vermelho-vermelho-preto) | 1 | ✅ comprado | limita a corrente do LED |
| **Capacitor eletrolítico 10 µF / 16 V** | 1 | ✅ comprado | entre EN (+) e GND (−): a placa entra sozinha no modo de gravação (seção 5) |
| **Receptor IR VS1838B** | 1 | ❌ não tenho | opcional: lê o código do controle original do ar (sem ele, testar as marcas pelo site ou pelo Monitor Serial) |
| Resistor de 100 Ω (marrom-preto-marrom) | 1 | opcional | só para o teste sem transistor (etapa 5) |

---

## 3. Pinos usados no ESP32

Com a placa de 30 pinos encaixada na protoboard, o lado do **3V3** fica assim
(a coluna **b** tem os pinos do ESP32 e a coluna **a** é o único furo livre):

| Linha | Pino do ESP32 | Ligado em | Uso |
|-------|---------------|-----------|-----|
| 1 | 3V3 | a1 → **+** do DHT22 | alimentação do sensor (e do LED, na etapa 6) |
| 2 | GND | a2 → **−** do DHT22 | terra comum de tudo |
| 3 | D15 | — | **não usar** (atrapalha a gravação) |
| 4 | D2 | — | **não usar** (atrapalha a gravação) |
| 5 | **D4 (GPIO 4)** | a5 → **S** do DHT22 | dados do sensor |
| 6 | **D16 (GPIO 16)** | a6 → jumper até a20 (etapa 6) | sinal do infravermelho |
| 7 | **D17 (GPIO 17)** | a7 → OUT do VS1838B (etapa 7) | ler o controle original (só no `ler_controle.ino`) |

Regras que valem para qualquer mudança futura:
- **GPIO 34, 35, 36 e 39 só leem**, não acendem nada. Não servem para o LED.
- **GPIO 0, 2, 5, 12 e 15** interferem na gravação. Evitar.
- Como a linha 1 (3V3) e a linha 2 (GND) já estão ocupadas, o LED usa o
  **mesmo +/− do módulo do sensor** (ligado na linha do pino + ou − do módulo).
- Na placa, o pino do LED vem marcado **D16** (em outras placas aparece como
  RX2): é o mesmo **GPIO 16** do código (`PINO_IR = 16`).
- A placa do ESP32 é mais comprida que a fileira de pinos e cobre algumas
  linhas depois do último pino (linha 15). O circuito do LED começa na
  primeira linha com os furos **a–e livres**, que nesta montagem é a **linha 20**
  (as linhas 16 a 19 ficam embaixo da placa).

---

## 4. Etapas de montagem

### Etapa 1 — Preparar o computador ✅
- [x] Arduino IDE com o pacote **esp32** (Espressif) instalado.
- [x] Driver do **CH340** funcionando: a placa aparece como `USB-SERIAL CH340 (COM6)`.
- [x] Bibliotecas: **IRremoteESP8266** e **DHT sensor library** (Adafruit).
- [x] Dependências do Python no `.venv`: `pip install -r requirements.txt`.

_Pronto quando:_ a IDE grava um sketch na placa sem erro.

### Etapa 2 — Sensor de temperatura ✅
- [x] DHT22 ligado: **+ → 3V3**, **− → GND**, **S → D4**.
- [x] No código: `PINO_DHT = 4` e `TIPO_DHT = DHT22`.

_Pronto quando:_ o Monitor Serial mostra uma temperatura plausível
(teste feito: **27,4 °C e 44,5 %**) e o valor sobe ao segurar o sensor.

### Etapa 3 — Levar as leituras até a API ✅ (pelo cabo USB)
- [x] No código: `MODO_USB = true`.
- [x] No PC: API rodando e a ponte `ponte_usb.py` rodando (ver seção 6).

_Pronto quando:_ o painel mostra a temperatura do sensor na sala 101 e o
dispositivo aparece **online** (teste feito: **27,1 °C**, online).

> O Wi-Fi não funcionou porque o PC está no celular pelo **cabo USB**
> (rede `10.97.37.x`) e o ESP32 no **hotspot Wi-Fi** do mesmo celular
> (rede `10.153.145.x`): o celular isola as duas redes. Detalhes na seção 7.

### Etapa 4 — Comprar o material ✅
- [x] Transistor 2N2222, resistores de 1 kΩ e 22 Ω.
- [x] Capacitor eletrolítico de 10 µF / 16 V e receptor IR VS1838B.
- [x] Jumpers macho-macho.

_Pronto quando:_ as peças estão na bancada.

### Etapa 5 — Teste rápido do LED infravermelho (opcional, sem transistor)
Serve para confirmar que o LED tirado do controle ainda funciona.

```
D16 (a6) ── resistor 100 Ω ── LED + (perna longa)
                              LED − (perna curta) ── GND (− do sensor)
```

- [ ] Identificar as pernas do LED: **+** é a mais longa; o **−** fica do
      lado reto da borda e é a peça maior por dentro.
- [ ] Montar o circuito acima. **Nunca ligar o LED sem resistor.**

_Pronto quando:_ ao clicar **Ligar/Desligar** no site, a ponte mostra
`ESP32: >>> Infravermelho (LG): LIGAR` e o LED **pisca na câmera do celular**
(de preferência a câmera frontal). Alcance esperado: só 1 a 2 metros.

### Etapa 6 — LED com transistor (alcance de até ~8 metros)
O ESP32 só dá o sinal; o transistor liga o LED direto na alimentação.

```
3V3 (+ do sensor) ── resistor 22 Ω ── LED + (perna longa)
                                      LED − (perna curta) ── C (coletor)
D16 (a6) ── jumper ── resistor 1 kΩ ────────────────────── B (base)
                                                           E (emissor) ── GND (− do sensor)
```

Posições na protoboard (o circuito começa na linha 20, a primeira com os furos a–e livres; ver seção 3):

| Peça | Posição |
|------|---------|
| Jumper do sinal | **a6** (D16) → **a20** |
| Resistor 1 kΩ | **b20** → **b23** |
| Transistor (coluna e) | **e22 = C**, **e23 = B**, **e24 = E** |
| LED IR | perna curta (−) em **c22**, perna longa (+) em **c26** |
| Resistor 22 Ω | **d26** → linha do **+** do DHT22 (3V3) |
| Jumper do emissor | **b24** → linha do **−** do DHT22 (GND) |

O que fica ligado em cada linha (as linhas 21 e 25 ficam vazias):

| Linha | Ligações |
|-------|----------|
| 20 | jumper do D16 + resistor 1 kΩ |
| 22 | coletor (C) + perna − do LED |
| 23 | base (B) + resistor 1 kΩ |
| 24 | emissor (E) + jumper do GND |
| 26 | perna + do LED + resistor 22 Ω |

Posição do transistor, com o ESP32 no topo da protoboard (o **C** tem que
ficar em cima, na linha 22, junto com a perna − do LED):

| Transistor | Lado reto virado para |
|------------|-----------------------|
| **2N2222 / PN2222 (plástico) — o usado nesta montagem** | a **direita** |
| BC547 | a **esquerda** |

O sinal vai por um **jumper**, e não direto pelo resistor, para a perna do
resistor não passar por cima dos furos **a7–a15**, que estão ligados aos
pinos do ESP32.

- [x] Circuito montado nas posições acima.
- [x] Transistor usado: **2N2222** (lado reto para a direita).
- [x] Circuito começa na **linha 20** (jumper a6 → a20).
- [ ] **Teste de energia:** ligar o ESP32 no USB e conferir que nada esquenta
      (transistor, resistor de 22 Ω e LED). Se algo esquentar, desligar na hora.
- [ ] Teste com a câmera do celular (de preferência a frontal), anotando até
      que distância o LED ainda aparece piscando.
- [x] Código: **nada muda** (o pino continua o 16).

_Pronto quando:_ o LED pisca na câmera do celular mais forte que na etapa 5.

### Etapa 7 — Escolher a marca do ar no banco de códigos
A marca **não fica mais no código do ESP32**: cada sala escolhe a sua no site
(janela da sala → **Código infravermelho**). A lista de marcas e protocolos
está em `codigos_ar.py`; a API manda o protocolo junto com o comando.

- [x] Descobrir a marca do ar de teste: o **Philco** de casa liga com o protocolo **MIRAGE**
      (achado com o teste de marcas pelo Monitor Serial). No site, escolher **Philco (protocolo Mirage)**.
- [ ] Marca que não está na lista (Elgin, Agratto, Komeco...): **pelo site**, na
      janela da sala, escolher uma marca e clicar em **Testar ligar** (o ESP32
      dispara uma vez nesse código, sem salvar). Quando o ar apitar, conferir com
      **Testar desligar** e clicar em **Salvar**. Precisa do `esp32_sala.ino`
      gravado e da ponte USB rodando (o ESP32 tem que estar **online**).
      Sem o site, dá para testar pelo Monitor Serial (abaixo).
- [ ] A temperatura do ar é escolhida no site (botões **−** e **+**, de 16 a 30 °C).
      Com o ar ligado, o ESP32 manda a temperatura nova em poucos segundos.

**Testar protocolos pelo Monitor Serial (sem o site):** o próprio
`esp32_sala.ino` aceita teclas no Monitor Serial. **Parar a ponte USB** (a COM6
só aceita um programa), deixar o ar **desligado** e o LED apontado para ele
(1 a 2 m), abrir o Monitor Serial em 115200 com **Nova linha** e digitar `p` +
Enter para mandar "ligar" no próximo protocolo da lista (`l` mostra a lista,
um número escolhe direto). Quando o ar apitar ou ligar, digitar `d` para
confirmar que ele também desliga e escolher essa marca no site.

**Ler o controle original (VS1838B, se tiver):** gravar o `esp32/ler_controle/ler_controle.ino`,
ligar o receptor (**OUT → D17**, **GND → GND**, **VCC → 3V3**; inverter VCC e GND
queima o receptor), abrir o Monitor Serial em 115200, apontar o controle e
apertar **LIGAR**. O Monitor mostra o protocolo (ex.: `>>> Use o protocolo "COOLIX"`).
Acrescentar a marca no `codigos_ar.py` com esse protocolo e gravar de novo o
`esp32_sala.ino`. Se aparecer `Protocolo desconhecido`, guardar o que foi impresso.

_Pronto quando:_ a ponte mostra `ESP32: >>> Infravermelho (MIRAGE modelo 1): LIGAR 23 C`
(com a marca e a temperatura escolhidas) ao clicar em Ligar ou mudar a temperatura.

### Etapa 8 — Teste com o ar-condicionado de verdade
- [ ] Apontar o LED para o ar, começando a 1 metro e depois afastando.
- [ ] Clicar **Ligar** e **Desligar** no site.

_Pronto quando:_ o ar liga e desliga pelo site. Anotar no `DIARIO.md` a
**distância máxima** que funcionou (bom dado para o relatório).

### Etapa 9 — Voltar para o Wi-Fi (quando houver rede em comum)
Quando o PC e o ESP32 estiverem na **mesma rede** (por exemplo, o ESP32 no
Wi-Fi do roteador onde o PC está ligado por cabo):

- [ ] No código: `MODO_USB = false`, `WIFI_NOME`, `WIFI_SENHA` e
      `URL_API = "http://<IP do PC>:8000"`.
- [ ] A rede precisa ser **2,4 GHz** (o ESP32 não conecta em 5 GHz).
- [ ] API rodando com `--host 0.0.0.0` e porta 8000 liberada no firewall.

_Pronto quando:_ o painel recebe as leituras sem a ponte USB rodando.

---

## 5. Como gravar o ESP32

1. Abrir o sketch na Arduino IDE. Placa: **ESP32 Dev Module**. Porta: **COM6**.
2. **Fechar o Monitor Serial e parar a ponte USB** (a COM6 só aceita um programa por vez).
3. Clicar em **Carregar**.
4. Se travar em `Connecting.....` ou der `Wrong boot mode`: **segurar BOOT**,
   dar um toque em **EN**, continuar segurando BOOT até começar o `Writing at...`.
   (Um capacitor de 10 µF entre EN e GND resolve isso de vez.)

---

## 6. Como colocar tudo para rodar

Em terminais separados, na pasta do projeto, com o `.venv` ativo:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000     # 1) a API
python ponte_usb.py                            # 2) a ponte USB (MODO_USB = true)
python camera.py 101 1                         # 3) a câmera (opcional)
```

Painel: **http://127.0.0.1:8000** (o `localhost` pode falhar em alguns navegadores).

> O `ponte_usb.py` está no `.gitignore`: ele existe só nesta máquina.
> Não rodar o `simulador.py` junto com o ESP32: os dois mandam leituras
> para a sala 101 e misturam dados falsos com os reais.

---

## 7. Problemas já encontrados (e como foram resolvidos)

Bom material para a seção de resultados do relatório.

| Problema | Causa | Solução |
|----------|-------|---------|
| `'estadoEnviado' was not declared` | código colado pela metade na IDE | colar o arquivo inteiro (Ctrl+A, Ctrl+V) |
| `Wrong boot mode detected` | a placa não entra sozinha no modo de gravação | segurar BOOT + toque em EN |
| `uvicorn` não reconhecido | `.venv` sem as bibliotecas | `pip install -r requirements.txt` |
| Sensor sem leitura | fio de dados no D4, código lendo o GPIO 27 | código passou a ler o GPIO 4 |
| Leitura absurda (1,6 °C e 21 %) | sensor é **DHT22**, código lia como DHT11 | `TIPO_DHT = DHT22` |
| `PINO_IR = 34` | GPIO 34 só serve para entrada | LED no D16 (GPIO 16) |
| `A API nao respondeu (codigo -1)` | firewall do Windows bloqueando a porta 8000 | regra de entrada para a porta 8000 (rede privada) |
| `codigo -1` mesmo com o firewall liberado | PC (USB) e ESP32 (hotspot) em redes isoladas pelo celular | ponte pelo cabo USB (`ponte_usb.py`) |
| `PermissionError` na COM6 | Monitor Serial da IDE usando a porta | fechar o Monitor Serial |

---

## 8. Pendências

- [ ] **Marca do ar-condicionado** (escolher no site, etapa 7).
- [ ] **Senha do Wi-Fi no repositório:** o `esp32/esp32_sala/esp32_sala.ino` está com o
      nome e a senha reais do hotspot. Trocar para `NOME_DO_WIFI` /
      `SENHA_DO_WIFI` antes do próximo commit.
- [ ] Decidir com o professor se a ponte USB vale para a entrega ou se o
      Wi-Fi é obrigatório (ver a pergunta no fim do `BACKLOG.md`).
