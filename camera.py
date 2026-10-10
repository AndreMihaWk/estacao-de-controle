"""
camera.py — o "olho" da sala (verificacao de presenca pela webcam).

Roda no computador que tem a webcam da sala. Ele NAO decide nada: so pergunta
para a API se ja esta na hora de verificar, olha a sala, conta as pessoas e
responde. Quem decide (esperar 1 hora, conferir em 30 minutos ou desligar o
ar) e a regra avaliar_presenca() no api.py.

A camera so e aberta no momento da verificacao e nenhuma imagem e gravada
nem enviada: da maquina sai apenas o NUMERO de pessoas.

Como usar (com a API ja rodando):

    python camera.py             # vigia a sala 101 com a webcam 0
    python camera.py 305         # vigia outra sala
    python camera.py 101 1       # vigia a sala 101 com a webcam 1
    python camera.py --teste     # testa todas as webcams e mostra o que cada uma ve
"""

import sys
import time

import cv2
import requests

# Endereco da API. Se a API estiver em outro computador, troque pelo IP dele.
URL_API = "http://127.0.0.1:8000"

# Qual sala esta camera vigia (pode trocar pela linha de comando).
argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
SALA = argumentos[0] if argumentos else "101"

# Numero da webcam no computador (0 = a primeira). Se o computador tiver mais
# de uma (ou uma camera virtual), descubra o numero certo com --teste.
CAMERA = int(argumentos[1]) if len(argumentos) > 1 else 0

# Quantas webcams o --teste procura.
MAXIMO_CAMERAS = 4

# Imagem com brilho medio abaixo disto (0 a 255) e considerada "preta":
# lente tampada ou camera virtual. Nao vale como verificacao.
BRILHO_MINIMO = 2

# De quantos em quantos segundos perguntar para a API se e hora de verificar.
INTERVALO = 10

# Quantas fotos analisar em cada verificacao (vale a que tiver mais gente).
QUADROS = 8

# Detectores que ja vem dentro do OpenCV (nao precisa baixar nada):
# corpo inteiro (HOG) para quem esta em pe e rosto (Haar) para quem esta sentado.
detector_corpo = cv2.HOGDescriptor()
detector_corpo.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
detector_rosto = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def pessoas_no_quadro(quadro):
    """Conta as pessoas em uma imagem (o maior entre corpos e rostos achados)."""
    quadro = cv2.resize(quadro, (640, 480))
    corpos, _ = detector_corpo.detectMultiScale(
        quadro, winStride=(8, 8), padding=(8, 8), scale=1.05
    )
    cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
    rostos = detector_rosto.detectMultiScale(
        cinza, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
    )
    return max(len(corpos), len(rostos))


def contar_pessoas(numero_camera=CAMERA):
    """
    Abre a webcam, analisa alguns quadros e devolve quantas pessoas viu.
    Devolve None se a camera falhar ou so mostrar imagem preta — falha NAO e
    o mesmo que sala vazia, e nesse caso nada e enviado para a API (o ar nao
    e desligado por engano).
    """
    camera = cv2.VideoCapture(numero_camera)
    if not camera.isOpened():
        return None

    maximo = None
    try:
        for _ in range(20):  # a camera leva alguns quadros para ajustar a luz
            camera.read()
        for _ in range(QUADROS):
            ok, quadro = camera.read()
            if ok and quadro.mean() >= BRILHO_MINIMO:
                maximo = max(maximo or 0, pessoas_no_quadro(quadro))
            time.sleep(0.3)
    finally:
        camera.release()
    return maximo


def testar_cameras():
    """Mostra o que cada webcam do computador esta vendo agora."""
    for numero in range(MAXIMO_CAMERAS):
        pessoas = contar_pessoas(numero)
        if pessoas is None:
            print(f"Webcam {numero}: nao abriu ou a imagem esta preta")
        else:
            print(f"Webcam {numero}: imagem ok, {pessoas} pessoa(s) detectada(s)")


def main():
    print(f"Camera ligada. Vigiando a sala {SALA} com a webcam {CAMERA} para {URL_API}")
    print("Pressione Ctrl+C para parar.\n")

    while True:
        try:
            resposta = requests.get(f"{URL_API}/api/salas/{SALA}/verificacao", timeout=5)
            resposta.raise_for_status()

            if resposta.json()["verificar"]:
                pessoas = contar_pessoas()
                if pessoas is None:
                    print(f"A webcam {CAMERA} nao abriu ou a imagem esta preta. "
                          "Verificacao adiada.")
                else:
                    resposta = requests.post(
                        f"{URL_API}/api/salas/{SALA}/presenca",
                        json={"pessoas": pessoas},
                        timeout=5,
                    )
                    resposta.raise_for_status()
                    print(f"{time.strftime('%H:%M:%S')} | {pessoas} pessoa(s) "
                          f"-> {resposta.json()['decisao']}")
        except requests.exceptions.HTTPError as erro:
            print(f"A API recusou o pedido ({erro}). A sala {SALA} existe?")
        except requests.exceptions.RequestException:
            print("Nao consegui falar com a API. Ela esta rodando? "
                  "(uvicorn api:app --reload)")

        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        if "--teste" in sys.argv:
            testar_cameras()
        else:
            main()
    except KeyboardInterrupt:
        print("\nCamera desligada.")
