"""
simulador.py — o "dispositivo de mentira".

Enquanto o hardware (ESP32 + sensor) nao chega, ESTE arquivo faz o papel dele:
gera leituras de temperatura e umidade parecidas com as reais e envia para a
API, exatamente como um sensor de verdade faria.

Isso e o que permite construir e testar o sistema INTEIRO hoje, sem comprar
nada. Quando o ESP32 chegar, e so ele passar a chamar o mesmo endpoint
(POST /api/leituras) e o resto do sistema nem percebe a diferenca.

Como usar (com a API ja rodando em outro terminal):

    python simulador.py
"""

import random
import time

import requests

# Endereco da API. Se rodar tudo na mesma maquina, deixe assim.
URL_API = "http://127.0.0.1:8000/api/leituras"

# Qual sala este "dispositivo" representa.
SALA = "Sala 1"

# Quantos segundos esperar entre uma leitura e outra.
INTERVALO = 3


def gerar_proxima(temperatura_atual):
    """
    Gera a proxima temperatura a partir da atual, com pequenas variacoes.
    De vez em quando 'esquenta' de proposito, para o alerta disparar e voce
    conseguir ver o painel ficando vermelho durante a demonstracao.
    """
    # variacao suave (passeio aleatorio)
    temperatura = temperatura_atual + random.uniform(-0.4, 0.6)

    # 1 em cada 6 vezes, um empurrao para cima (simula ar desligado / sala cheia)
    if random.randint(1, 6) == 1:
        temperatura += random.uniform(1.0, 2.5)

    # mantem dentro de uma faixa plausivel para uma sala em Boa Vista
    temperatura = max(21.0, min(34.0, temperatura))

    umidade = random.uniform(55.0, 85.0)
    return round(temperatura, 1), round(umidade, 1)


def main():
    print(f"Simulador ligado. Enviando leituras da '{SALA}' para {URL_API}")
    print("Pressione Ctrl+C para parar.\n")

    temperatura = 24.0  # ponto de partida confortavel

    while True:
        temperatura, umidade = gerar_proxima(temperatura)
        dados = {"sala": SALA, "temperatura": temperatura, "umidade": umidade}

        try:
            resposta = requests.post(URL_API, json=dados, timeout=5)
            avaliacao = resposta.json()["avaliacao"]
            print(
                f"{temperatura:5.1f} C | {umidade:4.1f}% umidade "
                f"-> {avaliacao['status']}: {avaliacao['mensagem']}"
            )
        except requests.exceptions.RequestException:
            print("Nao consegui falar com a API. Ela esta rodando? "
                  "(uvicorn api:app --reload)")

        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulador desligado.")
