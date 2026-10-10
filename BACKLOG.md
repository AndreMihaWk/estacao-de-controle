# Passo a passo do projeto (backlog)

Tarefas curtas, uma de cada vez. Cada uma tem um **critério de pronto**: só marque
concluída quando conseguir demonstrar aquilo funcionando. Sugestão: **1 commit por tarefa**
e, quando travar, tente sozinho por ~25 minutos antes de buscar ajuda (o aperto ajuda a aprender).

O código já vem pronto — as primeiras tarefas são para você **entender e rodar**;
as últimas são melhorias que **você** implementa para aprender de verdade.

## Etapa 1 — Colocar no ar (entender o que já existe)

- [ ] **1.1 Rodar o sistema.** Seguir o README: instalar, subir a API, abrir o painel, ligar o simulador.
      _Pronto quando:_ o painel mostra a temperatura mudando sozinho.
- [ ] **1.2 Fazer o alerta disparar.** Baixar o `LIMITE_TEMPERATURA` no `api.py` (ex.: 25).
      _Pronto quando:_ o painel fica vermelho e escreve "ALERTA".
- [ ] **1.3 Ler o código e comentar.** Abrir `banco.py`, `api.py` e `simulador.py` e escrever, no `DIARIO.md`, uma frase explicando cada arquivo com suas palavras.
      _Pronto quando:_ há 3 frases suas no diário.
- [ ] **1.4 Ver a documentação automática.** Abrir `http://127.0.0.1:8000/docs` e testar o POST por ali.
      _Pronto quando:_ você enviou uma leitura manual pela página `/docs`.

## Etapa 2 — Deixar seu (pequenas mudanças suas)

- [ ] **2.1 Trocar o nome da sala.** Rodar o simulador em outra sala (ex.: `python simulador.py 305`) e dar nome ao equipamento dela pelo site.
      _Pronto quando:_ a sala escolhida aparece com temperatura e com o nome do equipamento.
- [ ] **2.2 Mostrar a umidade no gráfico também**, ou criar um segundo cartão com a média das últimas leituras.
      _Pronto quando:_ aparece uma informação nova que você calculou.
- [ ] **2.3 Ajustar o alerta.** Fazer o alerta considerar umidade alta também (ex.: quente E úmido).
      _Pronto quando:_ a regra em `avaliar_ambiente()` usa os dois valores.

## Etapa 3 — Documentação (peso grande na nota)

- [ ] **3.1 Preencher os dados** (nome, matrícula, sala escolhida) no documento ABNT.
- [ ] **3.2 Tirar prints:** painel normal, painel em alerta, e a página `/docs`.
- [ ] **3.3 Escrever os Resultados** a partir do que está no `DIARIO.md`.
- [ ] **3.4 Revisar** contra o plano de ensino da disciplina (ODS 7 e 12, formatação ABNT).

## Etapa 4 — Evolução (opcional, se sobrar tempo)

- [ ] **4.1 MQTT.** Trocar o envio HTTP pelo protocolo MQTT (broker público de teste). É o próximo nível de IoT.
- [ ] **4.2 Hardware.** Quando o ESP32 + sensor chegarem, fazer o dispositivo real chamar `POST /api/leituras`.

---

**Dúvida boa para o professor (peça ajuda para formular se precisar):**
o projeto pode ser entregue com o **simulador em Python** substituindo o hardware,
ou o **ESP32 físico é obrigatório**? A resposta define o quanto da Etapa 4 é necessário.
