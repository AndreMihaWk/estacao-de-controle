"""
simulador.py — o "dispositivo de mentira".

Enquanto o hardware (ESP32 + sensor + LED infravermelho) nao chega, ESTE
arquivo faz o papel dele em uma sala:

  1. gera leituras de temperatura e umidade e envia para a API;
  2. pergunta para a API se o ar deve estar ligado e, quando a resposta muda,
     "dispara o infravermelho" (aqui, so escreve na tela).

Isso e o que permite construir e testar o sistema INTEIRO hoje, sem comprar
nada. Quando o ESP32 chegar, e so ele passar a chamar os mesmos enderecos
(veja esp32/esp32_sala.ino) e o resto do sistema nem percebe a diferenca.

Como usar (com a API ja rodando em outro terminal):

    python simulador.py          # simula a sala 101
    python simulador.py 305      # simula outra sala
"""

import random
import sys
import time

import requests

# Endereco da API. Se rodar tudo na mesma maquina, deixe assim.
URL_API = "http://127.0.0.1:8000"

# Qual sala este "dispositivo" representa (pode trocar pela linha de comando).
SALA = sys.argv[1] if len(sys.argv) > 1 else "101"

# Quantos segundos esperar entre uma leitura e outra.
INTERVALO = 3


def gerar_proxima(temperatura_atual, ar_ligado):
    """
    Gera a proxima temperatura a partir da atual, com pequenas variacoes.
    Com o ar ligado a sala esfria aos poucos; desligado, ela esquenta — assim
    da para ver no painel o efeito de ligar e desligar.
    """
    # variacao suave (passeio aleatorio) puxando para baixo ou para cima
    tendencia = -0.3 if ar_ligado else 0.3
    temperatura = temperatura_atual + tendencia + random.uniform(-0.3, 0.3)

    # mantem dentro de uma faixa plausivel para uma sala em Boa Vista
    temperatura = max(21.0, min(34.0, temperatura))

    umidade = random.uniform(55.0, 85.0)
    return round(temperatura, 1), round(umidade, 1)


def main():
    print(f"Simulador ligado. Fazendo o papel do dispositivo da sala {SALA} em {URL_API}")
    print("Pressione Ctrl+C para parar.\n")

    temperatura = 27.0  # ponto de partida: sala com o ar desligado
    ar_ligado = False

    while True:
        try:
            # 1) o ar deve estar ligado? (o mesmo que o ESP32 pergunta)
            resposta = requests.get(f"{URL_API}/api/salas/{SALA}/comando", timeout=5)
            resposta.raise_for_status()
            deve_ligar = resposta.json()["ligado"]
            if deve_ligar != ar_ligado:
                ar_ligado = deve_ligar
                print(f">>> Infravermelho: {'LIGAR' if ar_ligado else 'DESLIGAR'} a central de ar")

            # 2) envia a leitura do sensor
            temperatura, umidade = gerar_proxima(temperatura, ar_ligado)
            dados = {"sala": SALA, "temperatura": temperatura, "umidade": umidade}
            resposta = requests.post(f"{URL_API}/api/leituras", json=dados, timeout=5)
            resposta.raise_for_status()
            avaliacao = resposta.json()["avaliacao"]
            print(
                f"{temperatura:5.1f} C | {umidade:4.1f}% umidade "
                f"| ar {'ligado   ' if ar_ligado else 'desligado'} "
                f"-> {avaliacao['status']}"
            )
        except requests.exceptions.HTTPError as erro:
            print(f"A API recusou o pedido ({erro}). A sala {SALA} existe?")
        except requests.exceptions.RequestException:
            print("Nao consegui falar com a API. Ela esta rodando? "
                  "(uvicorn api:app --reload)")

        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulador desligado.")
