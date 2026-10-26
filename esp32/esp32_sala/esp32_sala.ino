/*
  esp32_sala.ino — o dispositivo de verdade (um por sala).

  Faz o mesmo que o simulador.py faz hoje:
    1. pergunta para a API se o ar da sala deve estar ligado, em quantos
       graus e em qual codigo infravermelho (protocolo da marca do ar) falar;
    2. quando a resposta muda, dispara o LED infravermelho para ligar,
       desligar ou trocar a temperatura do ar (como se fosse o controle remoto);
    3. quando o site pede um teste de marca, dispara o infravermelho uma vez
       no codigo testado (serve para descobrir a marca do ar);
    4. le a temperatura e a umidade no sensor DHT e envia para a API.

  A marca e a temperatura do ar de cada sala sao escolhidas no site (banco de
  codigos em codigos_ar.py): o ESP32 nao precisa ser regravado para mudar.

  Dois jeitos de falar com a API (escolha em MODO_USB, abaixo):
    - Wi-Fi (MODO_USB = false): o ESP32 chama a API direto pela rede.
    - cabo USB (MODO_USB = true): o ESP32 so escreve e le no cabo, e o
      ponte_usb.py, rodando no computador, repassa tudo para a API. Serve
      quando o ESP32 e o computador nao estao na mesma rede.

  Teste de marcas sem o site (pelo Monitor Serial, 115200, com "Nova linha"):
  serve para descobrir a marca de um ar quando o site nao esta disponivel. No
  modo USB, pare a ponte antes (a porta so aceita um programa por vez).
  Com o ar DESLIGADO e o LED apontado para ele (1 a 2 metros), digite:
    p        manda LIGAR no proximo protocolo da lista
    numero   manda LIGAR no protocolo daquele numero (ex.: 13)
    a        manda LIGAR no protocolo atual (sem teste: o da sala)
    d        manda DESLIGAR no protocolo atual (para confirmar)
    l        mostra a lista
  O teste dispara uma vez e nao muda a marca da sala: quando o ar responder,
  escolha essa marca no site. (Foi assim que o ar Philco de teste ligou com MIRAGE.)

  Ligacao do LED infravermelho (com transistor, etapa 6 do MONTAGEM.md):
    GPIO 16 (D16) -> resistor 1k -> base do 2N2222 ; LED entre 3V3 (com 22 ohms)
    e o coletor ; emissor -> GND

  Ligacao do sensor DHT (DHT22 ou DHT11, modulo de 3 pinos):
    VCC -> 3V3 ; GND -> GND ; DATA -> GPIO 4
    (o sensor sem placa, de 4 pernas, precisa de um resistor de 10k entre
     DATA e 3V3; o modulo de 3 pinos ja vem com ele)

  Bibliotecas (Arduino IDE > Gerenciador de Bibliotecas):
    - IRremoteESP8266   (funciona no ESP32 tambem)
    - DHT sensor library, da Adafruit (aceite instalar o Adafruit Unified Sensor junto)

  Antes de gravar em cada ESP32, ajuste o bloco "Configuracao" abaixo.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <IRremoteESP8266.h>
#include <IRac.h>
#include <IRutils.h>
#include <DHT.h>

// ---------------------------------------------------------------------------
// Configuracao — muda de sala para sala
// ---------------------------------------------------------------------------
// true = fala com a API pelo cabo USB (precisa do ponte_usb.py rodando no PC)
// false = fala com a API pelo Wi-Fi
const bool MODO_USB = true;

const char* WIFI_NOME  = "POCO X6 Pro 5G";
const char* WIFI_SENHA = "12345678";

// IP do computador onde a API esta rodando (uvicorn api:app --host 0.0.0.0)
const char* URL_API = "http://10.97.37.183:8000";

// Numero da sala onde este ESP32 esta instalado
const char* SALA = "101";

// Marca e temperatura usadas so se a API nao mandar (ou mandar algo invalido).
// As de verdade de cada sala sao escolhidas no site.
const decode_type_t MARCA_PADRAO  = decode_type_t::MIRAGE;  // o ar de teste (Philco) usa MIRAGE
const int16_t       MODELO_PADRAO = 1;
const int           GRAUS_PADRAO  = 23;

const uint16_t PINO_IR = 16;          // GPIO do LED infravermelho (D16)
const uint8_t  PINO_DHT = 4;          // GPIO do DATA do sensor de temperatura
const uint8_t  TIPO_DHT = DHT22;      // DHT22 (grade branca) ou DHT11 (grade azul)
const unsigned long INTERVALO = 5000; // ms entre uma leitura do sensor e outra

// Protocolos do teste de marcas pelo Monitor Serial, dos mais comuns em marcas
// vendidas no Brasil (Philco, Elgin, Agratto...) para os menos. Todos estao
// tambem no banco de codigos do site (codigos_ar.py).
struct Tentativa {
  const char* protocolo;
  int16_t     modelo;
};
const Tentativa LISTA[] = {
  {"COOLIX", 1},       {"MIDEA", 1},          {"GREE", 1},         {"GREE", 2},
  {"TCL112AC", 1},     {"TCL96AC", 1},        {"ELECTRA_AC", 1},   {"HAIER_AC", 1},
  {"HAIER_AC_YRW02", 1}, {"HAIER_AC176", 1},  {"KELON", 1},        {"KELVINATOR", 1},
  {"MIRAGE", 1},       {"VOLTAS", 1},         {"TECO", 1},         {"LG", 1},
  {"LG2", 2},          {"SAMSUNG_AC", 1},     {"CARRIER_AC64", 1}, {"DAIKIN", 1},
  {"WHIRLPOOL_AC", 1}, {"YORK", 1},           {"AIRWELL", 1},      {"TROTEC", 1},
  {"FUJITSU_AC", 1},   {"HITACHI_AC", 1},     {"PANASONIC_AC", 1}, {"TOSHIBA_AC", 1},
  {"MITSUBISHI_AC", 1}, {"SHARP_AC", 1},
};
const int TOTAL = sizeof(LISTA) / sizeof(LISTA[0]);

// ---------------------------------------------------------------------------
IRac ar(PINO_IR);
DHT sensor(PINO_DHT, TIPO_DHT);

// O que a API mandou fazer.
struct Comando {
  int    ligado;          // 1 = ligado, 0 = desligado, -1 = nao chegou comando
  String protocolo;       // ex.: "MIRAGE", "GREE", "LG" (vem do banco de codigos)
  int    modelo;          // variante do controle remoto dentro do protocolo
  int    graus;           // temperatura pedida ao ar (escolhida no site)
  int    testeLigado;     // teste de marca: 1 = ligar, 0 = desligar, -1 = nenhum
  String testeProtocolo;  // codigo que o site quer testar
  int    testeModelo;
};

// Ultimo comando enviado por infravermelho (estado -1 = nenhum ainda)
int    estadoEnviado = -1;
String protocoloEnviado = "";
int    modeloEnviado = 0;
int    grausEnviados = 0;

int grausDoSite = GRAUS_PADRAO;  // ultima temperatura pedida no site (usada no teste pelo teclado)
int posicaoTeste = -1;           // posicao na LISTA do ultimo protocolo testado pelo teclado

unsigned long ultimaLeitura = 0;  // millis() da ultima leitura do sensor

Comando comandoVazio() {
  return {-1, "", MODELO_PADRAO, GRAUS_PADRAO, -1, "", MODELO_PADRAO};
}

// Tenta conectar por 10 s. Sem Wi-Fi, o teste de marcas pelo teclado funciona
// assim mesmo, e o ESP32 continua tentando reconectar sozinho.
void conectarWifi() {
  Serial.print("Conectando ao Wi-Fi");
  WiFi.begin(WIFI_NOME, WIFI_SENHA);
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 10000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(" conectado! IP do ESP32: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" sem Wi-Fi por enquanto (o teste de marcas funciona assim mesmo)");
  }
}

// Dispara o infravermelho para ligar (true) ou desligar (false) o ar, no
// codigo da marca pedida (ex.: "MIRAGE") e na temperatura pedida.
// Marca desconhecida usa a padrao; temperatura fora da faixa usa a padrao.
void enviarInfravermelho(bool ligar, const String& protocolo, int modelo, int graus) {
  decode_type_t marca = strToDecodeType(protocolo.c_str());
  if (!IRac::isProtocolSupported(marca)) {
    if (protocolo.length() > 0) {
      Serial.printf("Codigo infravermelho desconhecido (%s), usando o padrao\n", protocolo.c_str());
    }
    marca  = MARCA_PADRAO;
    modelo = MODELO_PADRAO;
  }
  if (graus < 16 || graus > 30) graus = GRAUS_PADRAO;

  ar.next.protocol = marca;
  ar.next.model    = modelo;
  ar.next.power    = ligar;
  ar.next.mode     = stdAc::opmode_t::kCool;
  ar.next.celsius  = true;
  ar.next.degrees  = graus;
  ar.next.fanspeed = stdAc::fanspeed_t::kAuto;
  ar.next.swingv   = stdAc::swingv_t::kOff;
  ar.next.swingh   = stdAc::swingh_t::kOff;
  ar.sendAc();
  Serial.printf(">>> Infravermelho (%s modelo %d): %s %d C\n",
                typeToString(marca).c_str(), modelo, ligar ? "LIGAR" : "DESLIGAR", graus);
}

// Pega o valor de um campo num JSON simples, como {"protocolo":"LG","modelo":1}.
String campoJson(const String& json, const char* campo) {
  String chave = String("\"") + campo + "\":";
  int inicio = json.indexOf(chave);
  if (inicio < 0) return "";
  inicio += chave.length();
  int fim = inicio;
  while (fim < (int)json.length() && json[fim] != ',' && json[fim] != '}') fim++;
  String valor = json.substring(inicio, fim);
  valor.replace("\"", "");
  valor.trim();
  return valor;
}

// Numero de um campo do JSON, ou 'padrao' se o campo nao veio.
int numeroJson(const String& json, const char* campo, int padrao) {
  String valor = campoJson(json, campo);
  return valor.length() > 0 ? valor.toInt() : padrao;
}

// Pergunta para a API (pelo Wi-Fi) o que fazer com o ar.
// Se nao conseguir perguntar, devolve o comando com ligado = -1.
Comando perguntarComando() {
  Comando comando = comandoVazio();
  HTTPClient http;
  http.begin(String(URL_API) + "/api/salas/" + SALA + "/comando");
  int codigo = http.GET();
  if (codigo == 200) {
    // a resposta e {"ligado":true,"protocolo":"MIRAGE","modelo":1,"graus":23,
    //               "teste_ligado":-1,"teste_protocolo":"","teste_modelo":0}
    String resposta = http.getString();
    comando.ligado         = campoJson(resposta, "ligado") == "true" ? 1 : 0;
    comando.protocolo      = campoJson(resposta, "protocolo");
    comando.modelo         = numeroJson(resposta, "modelo", MODELO_PADRAO);
    comando.graus          = numeroJson(resposta, "graus", GRAUS_PADRAO);
    comando.testeLigado    = numeroJson(resposta, "teste_ligado", -1);
    comando.testeProtocolo = campoJson(resposta, "teste_protocolo");
    comando.testeModelo    = numeroJson(resposta, "teste_modelo", MODELO_PADRAO);
  } else {
    Serial.printf("A API nao respondeu (codigo %d)\n", codigo);
  }
  http.end();
  return comando;
}

void mostrarLista() {
  Serial.println("Protocolos (numero: nome modelo):");
  for (int i = 0; i < TOTAL; i++) {
    Serial.printf("  %2d: %s %d\n", i + 1, LISTA[i].protocolo, LISTA[i].modelo);
  }
  Serial.println("Comandos: p = proximo | numero = escolher | a = ligar | d = desligar | l = lista");
}

// Teste de marcas digitado no Monitor Serial (p, numero, a, d, l).
// Dispara uma vez e nao muda a marca da sala (essa e escolhida no site).
void comandoDoTeclado(const String& tecla) {
  if (tecla == "l") {
    mostrarLista();
    return;
  }
  if (tecla == "p") {
    posicaoTeste = (posicaoTeste + 1) % TOTAL;
  } else if (tecla.toInt() >= 1 && tecla.toInt() <= TOTAL) {
    posicaoTeste = tecla.toInt() - 1;
  } else if (tecla != "a" && tecla != "d") {
    Serial.println("Comando desconhecido. Use p, a, d, l ou um numero de 1 a " + String(TOTAL));
    return;
  }
  bool ligar = tecla != "d";

  // a / d antes de testar qualquer protocolo: usa a marca da sala
  if (posicaoTeste < 0) {
    enviarInfravermelho(ligar, protocoloEnviado, modeloEnviado, grausDoSite);
    return;
  }

  const Tentativa& tentativa = LISTA[posicaoTeste];
  if (!IRac::isProtocolSupported(strToDecodeType(tentativa.protocolo))) {
    Serial.printf("%2d: %s nao existe nesta versao da biblioteca, pulando\n",
                  posicaoTeste + 1, tentativa.protocolo);
    return;
  }
  Serial.printf("Teste %d/%d: ", posicaoTeste + 1, TOTAL);
  enviarInfravermelho(ligar, tentativa.protocolo, tentativa.modelo, grausDoSite);
}

// Le as linhas que chegam pelo cabo USB. Podem vir:
//   - da ponte_usb.py (o que o site mandou):
//       "COMANDO <ligado> <protocolo> <modelo> <graus>", ex.: "COMANDO 1 MIRAGE 1 23"
//       "TESTE <ligado> <protocolo> <modelo> <graus>",   ex.: "TESTE 1 COOLIX 1 23"
//   - de voce, no Monitor Serial: p, numero, a, d ou l (teste de marcas).
// Devolve o que a ponte mandou (ligado = -1 e testeLigado = -1 se nada).
Comando lerSerial() {
  Comando comando = comandoVazio();
  while (Serial.available()) {
    String linha = Serial.readStringUntil('\n');
    linha.trim();
    if (linha.length() == 0) continue;
    int ligado = -1, modelo = MODELO_PADRAO, graus = GRAUS_PADRAO;
    char protocolo[32] = "";
    if (sscanf(linha.c_str(), "COMANDO %d %31s %d %d", &ligado, protocolo, &modelo, &graus) >= 1) {
      comando.ligado    = ligado;
      comando.protocolo = protocolo;
      comando.modelo    = modelo;
      comando.graus     = graus;
    } else if (sscanf(linha.c_str(), "TESTE %d %31s %d %d", &ligado, protocolo, &modelo, &graus) >= 2) {
      comando.testeLigado    = ligado;
      comando.testeProtocolo = protocolo;
      comando.testeModelo    = modelo;
      comando.graus          = graus;
    } else {
      comandoDoTeclado(linha);
    }
  }
  return comando;
}

// Faz o que a API mandou: o teste de marca (se houver) e o estado do ar.
void obedecer(const Comando& comando) {
  if (comando.testeLigado != -1) {
    Serial.print("Teste de marca pedido no site: ");
    enviarInfravermelho(comando.testeLigado == 1, comando.testeProtocolo,
                        comando.testeModelo, comando.graus);
  }
  if (comando.ligado == -1) return;
  grausDoSite = comando.graus;

  // so dispara o infravermelho quando muda o estado pedido, o codigo da marca
  // ou, com o ar ligado, a temperatura (trocar a marca no site manda o estado
  // da sala de novo, no codigo novo)
  bool mudou = comando.ligado != estadoEnviado
            || comando.protocolo != protocoloEnviado
            || comando.modelo != modeloEnviado
            || (comando.ligado == 1 && comando.graus != grausEnviados);
  if (mudou) {
    enviarInfravermelho(comando.ligado == 1, comando.protocolo, comando.modelo, comando.graus);
    estadoEnviado    = comando.ligado;
    protocoloEnviado = comando.protocolo;
    modeloEnviado    = comando.modelo;
    grausEnviados    = comando.graus;
  }
}

// Le o sensor e envia a temperatura e a umidade para a API.
void enviarLeitura() {
  float temperatura = sensor.readTemperature();
  float umidade     = sensor.readHumidity();
  if (isnan(temperatura) || isnan(umidade)) {
    Serial.println("Nao consegui ler o sensor de temperatura (confira a ligacao)");
    return;
  }

  if (MODO_USB) {
    // o ponte_usb.py le esta linha no cabo e repassa para a API
    Serial.printf("LEITURA %.1f %.1f\n", temperatura, umidade);
    return;
  }

  // o mesmo JSON que o simulador manda: {"sala":"101","temperatura":27.0,"umidade":60.0}
  String json = String("{\"sala\":\"") + SALA + "\""
              + ",\"temperatura\":" + String(temperatura, 1)
              + ",\"umidade\":" + String(umidade, 1) + "}";

  // mostra a leitura antes de enviar, assim da para testar o sensor sem a API
  Serial.printf("%.1f C | %.1f%% umidade", temperatura, umidade);

  HTTPClient http;
  http.begin(String(URL_API) + "/api/leituras");
  http.addHeader("Content-Type", "application/json");
  int codigo = http.POST(json);
  if (codigo == 200) {
    Serial.println(" -> enviado");
  } else {
    Serial.printf(" -> a API nao aceitou (codigo %d)\n", codigo);
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  sensor.begin();
  if (!MODO_USB) conectarWifi();
  Serial.println("Teste de marcas pelo Monitor Serial: digite l para ver a lista");
}

void loop() {
  // o cabo e atendido o tempo todo: os comandos do site (pela ponte) e as
  // teclas do teste de marcas sao obedecidos assim que chegam
  obedecer(lerSerial());

  if (ultimaLeitura != 0 && millis() - ultimaLeitura < INTERVALO) {
    delay(50);
    return;
  }
  ultimaLeitura = millis();

  // no Wi-Fi, pergunta a API junto com cada leitura (a cada INTERVALO);
  // sem Wi-Fi, pula a pergunta (o ESP32 reconecta sozinho quando der)
  if (!MODO_USB && WiFi.status() == WL_CONNECTED) {
    obedecer(perguntarComando());
  }
  enviarLeitura();
}
