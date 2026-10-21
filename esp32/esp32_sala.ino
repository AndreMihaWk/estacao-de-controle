/*
  esp32_sala.ino — o dispositivo de verdade (um por sala).

  Faz o mesmo que o simulador.py faz hoje:
    1. pergunta para a API se o ar da sala deve estar ligado;
    2. quando a resposta muda, dispara o LED infravermelho para ligar ou
       desligar a central de ar (como se fosse o controle remoto);
    3. le a temperatura e a umidade no sensor DHT e envia para a API.

  Dois jeitos de falar com a API (escolha em MODO_USB, abaixo):
    - Wi-Fi (MODO_USB = false): o ESP32 chama a API direto pela rede.
    - cabo USB (MODO_USB = true): o ESP32 so escreve e le no cabo, e o
      ponte_usb.py, rodando no computador, repassa tudo para a API. Serve
      quando o ESP32 e o computador nao estao na mesma rede.

  Ligacao do LED infravermelho:
    GPIO 16 (RX2) -> resistor 100 ohms -> LED IR (perna longa) ; perna curta -> GND
    (para alcance maior, use um transistor ou um modulo emissor IR pronto)

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

// Marca do ar-condicionado desta sala. Cada sala pode ter um equipamento
// diferente: troque pelo protocolo da marca (LG2, SAMSUNG_AC, GREE, MIDEA,
// DAIKIN, FUJITSU_AC, ELECTROLUX_AC...). A lista completa esta na
// documentacao da biblioteca IRremoteESP8266.
const decode_type_t MARCA_DO_AR = decode_type_t::LG2;

const uint16_t PINO_IR = 16;         // GPIO do LED infravermelho (RX2)
const uint8_t  PINO_DHT = 4;         // GPIO do DATA do sensor de temperatura
const uint8_t  TIPO_DHT = DHT22;     // DHT22 (grade branca) ou DHT11 (grade azul)
const float    TEMPERATURA_AR = 23;  // temperatura pedida ao ligar
const unsigned long INTERVALO = 5000; // ms entre uma pergunta e outra

// ---------------------------------------------------------------------------
IRac ar(PINO_IR);
DHT sensor(PINO_DHT, TIPO_DHT);

// Ultimo estado enviado por infravermelho: -1 = nenhum ainda, 0 = desligado, 1 = ligado
int estadoEnviado = -1;

void conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Conectando ao Wi-Fi");
  WiFi.begin(WIFI_NOME, WIFI_SENHA);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.print(" conectado! IP do ESP32: ");
  Serial.println(WiFi.localIP());
}

// Dispara o infravermelho para ligar (true) ou desligar (false) o ar.
void enviarInfravermelho(bool ligar) {
  ar.next.protocol = MARCA_DO_AR;
  ar.next.model    = 1;
  ar.next.power    = ligar;
  ar.next.mode     = stdAc::opmode_t::kCool;
  ar.next.celsius  = true;
  ar.next.degrees  = TEMPERATURA_AR;
  ar.next.fanspeed = stdAc::fanspeed_t::kAuto;
  ar.next.swingv   = stdAc::swingv_t::kOff;
  ar.next.swingh   = stdAc::swingh_t::kOff;
  ar.sendAc();
  Serial.println(ligar ? ">>> Infravermelho: LIGAR" : ">>> Infravermelho: DESLIGAR");
}

// Pergunta para a API (pelo Wi-Fi) se o ar deve estar ligado.
// Devolve 1 (ligado), 0 (desligado) ou -1 (nao conseguiu perguntar).
int perguntarComando() {
  HTTPClient http;
  http.begin(String(URL_API) + "/api/salas/" + SALA + "/comando");
  int codigo = http.GET();
  int resultado = -1;
  if (codigo == 200) {
    // a resposta e {"ligado":true} ou {"ligado":false}
    resultado = http.getString().indexOf("true") >= 0 ? 1 : 0;
  } else {
    Serial.printf("A API nao respondeu (codigo %d)\n", codigo);
  }
  http.end();
  return resultado;
}

// No modo USB, o ponte_usb.py escreve "COMANDO 1" ou "COMANDO 0" no cabo.
// Devolve o ultimo comando recebido, ou -1 se nao chegou nada.
int lerComandoUsb() {
  int resultado = -1;
  while (Serial.available()) {
    String linha = Serial.readStringUntil('\n');
    linha.trim();
    if (linha == "COMANDO 1") resultado = 1;
    else if (linha == "COMANDO 0") resultado = 0;
  }
  return resultado;
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
}

void loop() {
  int comando;
  if (MODO_USB) {
    comando = lerComandoUsb();
  } else {
    conectarWifi();
    comando = perguntarComando();
  }

  // so dispara o infravermelho quando o estado pedido muda
  if (comando != -1 && comando != estadoEnviado) {
    enviarInfravermelho(comando == 1);
    estadoEnviado = comando;
  }

  enviarLeitura();

  delay(INTERVALO);
}
