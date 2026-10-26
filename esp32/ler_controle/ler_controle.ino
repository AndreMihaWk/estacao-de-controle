/*
  ler_controle.ino — descobre o codigo infravermelho do controle de um ar.

  Uso: para marcas sem protocolo proprio no banco de codigos (Philco, Elgin,
  Agratto...). Grave este sketch, aponte o controle original do ar para o
  receptor e aperte LIGAR. O Monitor Serial (115200) mostra qual protocolo da
  IRremoteESP8266 o controle usa; e esse protocolo que vai no codigos_ar.py.
  Depois, grave de novo o esp32_sala.ino.

  Ligacao do receptor VS1838B (olhando a bolinha de frente, pernas para baixo):
    perna esquerda (OUT) -> D17 (GPIO 17)
    perna do meio  (GND) -> GND
    perna direita  (VCC) -> 3V3
  (no modulo com placa, siga as letras impressas: S/OUT, -, +)
  Inverter VCC e GND queima o receptor: confira antes de ligar o USB.

  Bibliotecas: IRremoteESP8266 (a mesma do esp32_sala.ino).
*/

#include <IRremoteESP8266.h>
#include <IRrecv.h>
#include <IRac.h>
#include <IRutils.h>

const uint16_t PINO_RECEPTOR = 17;   // OUT do VS1838B
const uint16_t TAMANHO_BUFFER = 1024; // controles de ar mandam mensagens longas
const uint8_t  TEMPO_LIMITE = 50;     // ms de silencio que encerram uma mensagem

IRrecv receptor(PINO_RECEPTOR, TAMANHO_BUFFER, TEMPO_LIMITE, true);
decode_results resultado;

void setup() {
  Serial.begin(115200);
  receptor.enableIRIn();
  Serial.println();
  Serial.println("Aponte o controle do ar para o receptor e aperte LIGAR.");
}

void loop() {
  if (!receptor.decode(&resultado)) return;

  Serial.println("----------------------------------------");
  Serial.print(resultToHumanReadableBasic(&resultado));

  // para protocolos de ar conhecidos, mostra o estado lido (modo, temperatura...)
  String estado = IRAcUtils::resultAcToString(&resultado);
  if (estado.length() > 0) Serial.println("Estado: " + estado);

  if (resultado.decode_type == decode_type_t::UNKNOWN) {
    Serial.println("Protocolo desconhecido. Copie as linhas abaixo e guarde:");
    Serial.println(resultToSourceCode(&resultado));
  } else if (IRac::isProtocolSupported(resultado.decode_type)) {
    Serial.printf(">>> Use o protocolo \"%s\" no codigos_ar.py\n",
                  typeToString(resultado.decode_type).c_str());
  } else {
    Serial.printf(">>> Protocolo %s reconhecido, mas o IRac nao sabe controlar ar com ele\n",
                  typeToString(resultado.decode_type).c_str());
  }
  yield();
}
