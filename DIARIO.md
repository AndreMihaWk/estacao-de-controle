# Diário de desenvolvimento — SMAC

> Anote aqui, com data, **o que você fez, o que travou e como resolveu**.
> Este diário é matéria-prima do relatório final: na hora de escrever a
> metodologia e os resultados, você copia daqui em vez de tentar lembrar tudo.
> Regra de ouro: uma anotação curta por dia de trabalho já basta.

---

## Modelo de anotação (copie e preencha)

### AAAA-MM-DD — título curto do que fez
- **Objetivo do dia:** o que eu queria concluir.
- **O que fiz:** o que realmente aconteceu.
- **Onde travei:** o erro ou a dúvida (cole a mensagem de erro se tiver).
- **Como resolvi:** o que destravou (link, ideia, teste).
- **Aprendi:** uma frase sobre o que ficou mais claro.

---

## Registros

### 2026-10-22 — Descobri o código do ar Philco e o site passou a controlar a temperatura
- **Objetivo do dia:** fazer o ESP32 ligar o ar-condicionado Philco de casa.
- **O que fiz:** como a Philco não tem protocolo próprio na IRremoteESP8266 e eu não tinha o receptor VS1838B, gravei um programa de teste que manda "ligar" em um protocolo de cada vez pelo Monitor Serial (hoje esse teste faz parte do `esp32_sala.ino`). O ar ligou com o protocolo **MIRAGE**. Depois o site ganhou: botões − e + para a temperatura do ar (16 a 30 °C), botões **Testar ligar / Testar desligar** para descobrir a marca pelo próprio site, e a Philco no banco de códigos.
- **Onde travei:** não havia código da Philco na biblioteca e eu não tinha o receptor para ler o controle original.
- **Como resolvi:** testei os protocolos por tentativa, começando pelos mais comuns em marcas vendidas no Brasil (Coolix, Midea, Gree, TCL...).
- **Aprendi:** muitas marcas vendidas no Brasil são fabricadas por outra empresa e usam o protocolo dela no infravermelho.
- **Próximo passo:** testar pelo site (com a ponte USB) ligar, desligar e mudar a temperatura, e anotar a distância máxima que funciona.

### 2026-10-22 — Material comprado e circuito do LED infravermelho montado
- **Objetivo do dia:** montar o LED infravermelho com transistor para alcançar o ar-condicionado a até ~8 m.
- **O que fiz:** comprei o transistor 2N2222, os resistores de 1 kΩ e 22 Ω, um capacitor de 10 µF / 16 V, um receptor IR VS1838B e jumpers macho-macho. Montei o circuito do LED na protoboard: sinal do D16 (GPIO 16) por um jumper do a6 até o a20, resistor de 1 kΩ na base do transistor, LED entre o 3V3 (com o resistor de 22 Ω) e o coletor, e emissor no GND. As posições estão na etapa 6 do `MONTAGEM.md`.
- **Onde travei:** a placa do ESP32 é mais comprida que a fileira de pinos e cobre algumas linhas depois do último pino, então não dava para montar logo abaixo. O pino que eu chamava de RX2 vem marcado como D16 na minha placa.
- **Como resolvi:** comecei o circuito na primeira linha com os furos a–e livres (a linha 20) e levei o sinal por um jumper, para a perna do resistor não passar por cima dos furos a7–a15, que estão ligados aos pinos do ESP32. O D16 é o mesmo GPIO 16, então o código não mudou.
- **Aprendi:** na protoboard, os furos a–e de uma mesma linha são ligados entre si; por isso cada perna do transistor tem que ficar numa linha diferente e nenhuma peça pode encostar nas linhas dos pinos do ESP32 sem querer.
- **Próximo passo:** teste de energia (ligar o ESP32 no USB e ver se nada esquenta) e depois o teste com a câmera do celular, anotando a distância.

### 2026-__-__ — Ambiente e primeiro contato com o projeto
- **Objetivo do dia:** rodar o projeto pela primeira vez.
- **O que fiz:** instalei as dependências, subi a API, abri o painel e liguei o simulador.
- **Onde travei:**
- **Como resolvi:**
- **Aprendi:**

<!-- adicione novos registros ACIMA desta linha, do mais novo para o mais antigo -->
