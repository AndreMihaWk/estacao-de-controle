/*
  esp32_sala.ino — o dispositivo de verdade (um por sala).

  Faz o mesmo que o simulador.py faz hoje:
    1. pergunta para a API se o ar da sala deve estar ligado;
    2. quando a resposta muda, dispara o LED infravermelho para ligar ou
       desligar a central de ar (como se fosse o controle remoto).

  Ligacao do LED infravermelho:
    GPIO 4 -> resistor 100 ohms -> LED IR (perna longa) ; perna curta -> GND
    (para alcance maior, use um transistor ou um modulo emissor IR pronto)

  Bibliotecas (Arduino IDE > Gerenciador de Bibliotecas):
    - IRremoteESP8266   (funciona no ESP32 tambem)

  Antes de gravar em cada ESP32, ajuste o bloco "Configuracao" abaixo.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <IRremoteESP8266.h>
#include <IRac.h>

// ---------------------------------------------------------------------------
// Configuracao — muda de sala para sala
// ---------------------------------------------------------------------------
const char* WIFI_NOME  = "NOME_DO_WIFI";
const char* WIFI_SENHA = "SENHA_DO_WIFI";

// IP do computador onde a API esta rodando (uvicorn api:app --host 0.0.0.0)
const char* URL_API = "http://192.168.0.10:8000";

// Numero da sala onde este ESP32 esta instalado
const char* SALA = "101";

// Marca do ar-condicionado desta sala. Cada sala pode ter um equipamento
// diferente: troque pelo protocolo da marca (LG2, SAMSUNG_AC, GREE, MIDEA,
// DAIKIN, FUJITSU_AC, ELECTROLUX_AC...). A lista completa esta na
// documentacao da biblioteca IRremoteESP8266.
const decode_type_t MARCA_DO_AR = decode_type_t::LG2;

const uint16_t PINO_IR = 4;          // GPIO do LED infravermelho
const float    TEMPERATURA_AR = 23;  // temperatura pedida ao ligar
const unsigned long INTERVALO = 5000; // ms entre uma pergunta e outra

// ---------------------------------------------------------------------------
IRac ar(PINO_IR);

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
  Serial.println(" conectado!");
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

// Pergunta para a API se o ar deve estar ligado.
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

void setup() {
  Serial.begin(115200);
  conectarWifi();
}

void loop() {
  conectarWifi();

  int comando = perguntarComando();
  // so dispara o infravermelho quando o estado pedido muda
  if (comando != -1 && comando != estadoEnviado) {
    enviarInfravermelho(comando == 1);
    estadoEnviado = comando;
  }

  delay(INTERVALO);
}
