"""
codigos_ar.py — o banco de codigos do infravermelho.

Cada marca de ar-condicionado "fala" uma lingua diferente no infravermelho
(o protocolo do controle remoto). Aqui fica a lista das marcas que o sistema
sabe controlar e, para cada uma, o protocolo correspondente na biblioteca
IRremoteESP8266, que roda no ESP32.

Como funciona:
  - cada sala guarda o id da sua marca (coluna marca_ar no banco);
  - quando o ESP32 pergunta o comando, a API responde se o ar deve estar
    ligado E qual protocolo/modelo usar;
  - o ESP32 so obedece: monta o sinal daquele protocolo e dispara o LED.
Assim, trocar a marca de uma sala e so escolher no site, sem regravar o ESP32.

Para incluir uma marca nova, acrescente uma linha em MARCAS usando um
protocolo suportado pela IRremoteESP8266 (lista em IRac::isProtocolSupported,
no arquivo src/IRac.cpp da biblioteca). O "modelo" escolhe a variante do
controle remoto dentro do protocolo: 1 e o modelo padrao da biblioteca.

Marcas vendidas no Brasil sem protocolo proprio (Elgin, Agratto, Komeco,
Britania, Electrolux...) costumam ser fabricadas por outra empresa: no site,
use "Testar ligar" com Coolix, Midea, Gree, TCL, Mirage... ate o ar responder.
A Philco foi descoberta assim: o ar de teste ligou com o protocolo MIRAGE.
"""

# id -> nome mostrado no site, protocolo na IRremoteESP8266 e modelo do controle
MARCAS = {
    "lg":               {"nome": "LG",                          "protocolo": "LG",                   "modelo": 1},
    "lg2":              {"nome": "LG (variante LG2)",           "protocolo": "LG2",                  "modelo": 2},
    "samsung":          {"nome": "Samsung",                     "protocolo": "SAMSUNG_AC",           "modelo": 1},
    "gree":             {"nome": "Gree",                        "protocolo": "GREE",                 "modelo": 1},
    "gree_ybofb":       {"nome": "Gree (controle YBOFB)",       "protocolo": "GREE",                 "modelo": 2},
    "midea":            {"nome": "Midea / Springer Midea",      "protocolo": "MIDEA",                "modelo": 1},
    "coolix":           {"nome": "Coolix (Midea e Springer antigos)", "protocolo": "COOLIX",         "modelo": 1},
    "carrier":          {"nome": "Carrier",                     "protocolo": "CARRIER_AC64",         "modelo": 1},
    "daikin":           {"nome": "Daikin",                      "protocolo": "DAIKIN",               "modelo": 1},
    "fujitsu":          {"nome": "Fujitsu",                     "protocolo": "FUJITSU_AC",           "modelo": 1},
    "hitachi":          {"nome": "Hitachi",                     "protocolo": "HITACHI_AC",           "modelo": 1},
    "panasonic":        {"nome": "Panasonic",                   "protocolo": "PANASONIC_AC",         "modelo": 1},
    "toshiba":          {"nome": "Toshiba",                     "protocolo": "TOSHIBA_AC",           "modelo": 1},
    "mitsubishi":       {"nome": "Mitsubishi Electric",         "protocolo": "MITSUBISHI_AC",        "modelo": 1},
    "mitsubishi_heavy": {"nome": "Mitsubishi Heavy",            "protocolo": "MITSUBISHI_HEAVY_152", "modelo": 1},
    "haier":            {"nome": "Haier",                       "protocolo": "HAIER_AC",             "modelo": 1},
    "hisense":          {"nome": "Hisense (Kelon)",             "protocolo": "KELON",                "modelo": 1},
    "tcl":              {"nome": "TCL",                         "protocolo": "TCL112AC",             "modelo": 1},
    "sharp":            {"nome": "Sharp",                       "protocolo": "SHARP_AC",             "modelo": 1},
    "whirlpool":        {"nome": "Whirlpool",                   "protocolo": "WHIRLPOOL_AC",         "modelo": 1},
    "electra":          {"nome": "Electra / AUX",               "protocolo": "ELECTRA_AC",           "modelo": 1},
    "york":             {"nome": "York",                        "protocolo": "YORK",                 "modelo": 1},
    "philco":           {"nome": "Philco (protocolo Mirage)",   "protocolo": "MIRAGE",               "modelo": 1},
    # protocolos sem marca conhecida no Brasil: servem para testar marcas novas
    "mirage":           {"nome": "Mirage",                      "protocolo": "MIRAGE",               "modelo": 1},
    "tcl96":            {"nome": "TCL (variante 96)",           "protocolo": "TCL96AC",              "modelo": 1},
    "haier_yrw02":      {"nome": "Haier (controle YR-W02)",     "protocolo": "HAIER_AC_YRW02",       "modelo": 1},
    "haier176":         {"nome": "Haier (variante 176)",        "protocolo": "HAIER_AC176",          "modelo": 1},
    "kelvinator":       {"nome": "Kelvinator",                  "protocolo": "KELVINATOR",           "modelo": 1},
    "voltas":           {"nome": "Voltas",                      "protocolo": "VOLTAS",               "modelo": 1},
    "teco":             {"nome": "Teco",                        "protocolo": "TECO",                 "modelo": 1},
    "airwell":          {"nome": "Airwell",                     "protocolo": "AIRWELL",              "modelo": 1},
    "trotec":           {"nome": "Trotec",                      "protocolo": "TROTEC",               "modelo": 1},
}

# Marca usada pelas salas que ainda nao escolheram a sua.
PADRAO = "lg"


def buscar(id_marca):
    """Dados de uma marca do banco de codigos, ou None se o id nao existir."""
    if id_marca not in MARCAS:
        return None
    return {"id": id_marca, **MARCAS[id_marca]}


def listar():
    """Todas as marcas, na ordem acima (para o seletor do site)."""
    return [buscar(id_marca) for id_marca in MARCAS]


def da_sala(sala):
    """Codigo que a sala usa: a marca escolhida ou, se nao tiver, a padrao."""
    return buscar(sala.get("marca_ar")) or buscar(PADRAO)
