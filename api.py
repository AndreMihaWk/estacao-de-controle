"""
api.py — o "cerebro" do sistema, na nuvem.

Este e o backend que roda no servidor (a parte "Cloud" do projeto). Ele:

  1. RECEBE  as leituras que os dispositivos enviam       -> POST /api/leituras
  2. GUARDA  cada leitura no banco de dados                -> banco.py
  3. AVALIA  se o ambiente esta quente demais (alerta)     -> avaliar_ambiente()
  4. MOSTRA  tudo num painel no navegador                  -> GET /

Feito com FastAPI. Para rodar:

    uvicorn api:app --reload

Depois abra http://127.0.0.1:8000 no navegador.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import banco

# ---------------------------------------------------------------------------
# Configuracao (Industria 4.0: a regra de decisao automatica fica aqui)
# ---------------------------------------------------------------------------
# Se a temperatura passar deste limite, o sistema dispara um alerta.
# Mude este numero para testar o alerta mais facil.
LIMITE_TEMPERATURA = 28.0  # graus Celsius


# ---------------------------------------------------------------------------
# Modelo dos dados que o dispositivo envia
# ---------------------------------------------------------------------------
class Leitura(BaseModel):
    """Formato do JSON que um dispositivo (ou o simulador) manda para a API."""
    sala: str
    temperatura: float
    umidade: float


# ---------------------------------------------------------------------------
# Regra de decisao — o coracao de "Industria 4.0"
# ---------------------------------------------------------------------------
def avaliar_ambiente(temperatura):
    """
    Decide o estado do ambiente a partir da temperatura.
    Retorna um dicionario com o status e uma mensagem para o painel.
    """
    if temperatura > LIMITE_TEMPERATURA:
        return {
            "status": "ALERTA",
            "mensagem": f"Ambiente quente ({temperatura:.1f} C). Verifique o ar-condicionado.",
        }
    return {
        "status": "OK",
        "mensagem": f"Ambiente confortavel ({temperatura:.1f} C).",
    }


# ---------------------------------------------------------------------------
# Aplicacao
# ---------------------------------------------------------------------------
app = FastAPI(title="SMAC - Sistema de Monitoramento de Ambiente na Cloud")


@app.on_event("startup")
def ao_iniciar():
    """Garante que a tabela do banco exista assim que o servidor sobe."""
    banco.iniciar_banco()


@app.post("/api/leituras")
def receber_leitura(leitura: Leitura):
    """
    Endpoint que o DISPOSITIVO chama para enviar uma medicao.
    Grava a leitura e ja devolve a avaliacao do ambiente.
    """
    registro = banco.inserir_leitura(
        leitura.sala, leitura.temperatura, leitura.umidade
    )
    avaliacao = avaliar_ambiente(leitura.temperatura)
    return {"recebido": registro, "avaliacao": avaliacao}


@app.get("/api/status")
def status(sala: str = "Sala 1"):
    """
    Endpoint que o PAINEL chama para saber a situacao atual da sala:
    ultima leitura + avaliacao (OK ou ALERTA).
    """
    leitura = banco.ultima_leitura(sala)
    if leitura is None:
        return {"sala": sala, "leitura": None, "avaliacao": None}
    avaliacao = avaliar_ambiente(leitura["temperatura"])
    return {"sala": sala, "leitura": leitura, "avaliacao": avaliacao}


@app.get("/api/leituras")
def historico(sala: str = "Sala 1", limite: int = 30):
    """Endpoint que o PAINEL chama para desenhar o grafico do historico."""
    return {"sala": sala, "leituras": banco.ultimas_leituras(sala, limite)}


@app.get("/api/salas")
def salas():
    """Lista as salas que ja mandaram dados (para um seletor no painel)."""
    return {"salas": banco.listar_salas()}


@app.get("/", response_class=HTMLResponse)
def painel():
    """Serve a pagina do painel (o arquivo templates/dashboard.html)."""
    with open("templates/dashboard.html", "r", encoding="utf-8") as arquivo:
        return arquivo.read()
