"""
api.py — o "cerebro" do sistema, na nuvem.

Este e o backend que roda no servidor (a parte "Cloud" do projeto). Ele:

  1. RECEBE  as leituras que os dispositivos enviam        -> POST /api/leituras
  2. GUARDA  tudo no banco de dados                         -> banco.py
  3. CONTROLA o ar de cada sala (site, agenda ou presenca)  -> mudar_energia()
  4. DECIDE  se desliga o ar de uma sala vazia              -> avaliar_presenca()
  5. MOSTRA  tudo num painel no navegador                   -> GET /

Quem conversa com a API:

  - o SITE        liga/desliga, programa horario e mostra os avisos
  - o ESP32       pergunta "o ar deve estar ligado?" e dispara o infravermelho
  - a CAMERA      pergunta "e hora de verificar?" e responde quantas pessoas viu

Feito com FastAPI. Para rodar:

    uvicorn api:app --reload

Depois abra http://127.0.0.1:8000 no navegador.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import banco

# ---------------------------------------------------------------------------
# Configuracao (Industria 4.0: as regras de decisao automatica ficam aqui)
# ---------------------------------------------------------------------------
# Se a temperatura passar deste limite, o sistema dispara um alerta.
LIMITE_TEMPERATURA = 28.0  # graus Celsius

# Verificacao de presenca pela camera.
# Para demonstrar sem esperar, troque por valores pequenos (ex.: 2 e 1).
MINUTOS_COM_PESSOAS = 1  # viu gente: so verifica de novo depois deste tempo
MINUTOS_SEM_PESSOAS = 1  # nao viu ninguem: confere de novo depois deste tempo

# Texto gravado quando a regra de presenca desliga o ar (aparece no site).
MOTIVO_SALA_VAZIA = "Desligado automaticamente: sala vazia em duas verificações seguidas."

# Um dispositivo e considerado "online" se falou com a API nos ultimos segundos.
SEGUNDOS_ONLINE = 30

# Guarda quando cada ESP32 e cada camera falaram com a API pela ultima vez.
ultimo_contato = {"dispositivo": {}, "camera": {}}


# ---------------------------------------------------------------------------
# Modelos dos dados que chegam na API
# ---------------------------------------------------------------------------
class Leitura(BaseModel):
    """Formato do JSON que um dispositivo (ou o simulador) manda para a API."""
    sala: str
    temperatura: float
    umidade: float


class Energia(BaseModel):
    """Pedido do site para ligar (true) ou desligar (false) o ar."""
    ligado: bool


class Agenda(BaseModel):
    """Horarios diarios no formato "HH:MM". Vazio (null) = sem horario."""
    hora_ligar: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    hora_desligar: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class Equipamento(BaseModel):
    """Nome/modelo do equipamento instalado na sala."""
    equipamento: str = Field(min_length=1, max_length=60)


class Presenca(BaseModel):
    """Resultado de uma verificacao da camera."""
    pessoas: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Regras de decisao — o coracao de "Industria 4.0"
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


def daqui_a(minutos):
    """Data e hora de agora + N minutos, no formato de texto do banco."""
    return (datetime.now() + timedelta(minutes=minutos)).isoformat(timespec="seconds")


def mudar_energia(sala, ligar, tipo, motivo):
    """
    UNICO lugar que liga ou desliga o ar de uma sala. O site, a agenda e a
    regra de presenca passam todos por aqui. O ESP32 fica sabendo na proxima
    vez que perguntar o comando e entao dispara o infravermelho.
    """
    if bool(sala["ligado"]) == ligar:
        return  # ja esta no estado pedido, nada a fazer

    banco.atualizar_sala(
        sala["numero"],
        ligado=int(ligar),
        motivo=motivo,
        mudou_em=banco.agora(),
        ausencias=0,
        # ao ligar, a camera ja faz a primeira verificacao; desligado nao verifica
        proxima_verificacao=banco.agora() if ligar else None,
    )
    banco.registrar_evento(sala["numero"], tipo, motivo)


def avaliar_presenca(sala, pessoas):
    """
    Regra da sala vazia, aplicada a cada verificacao da camera:

      - viu gente       -> tudo certo, verifica de novo em 1 hora
      - nao viu ninguem -> confere de novo em 30 minutos
      - nao viu ninguem na conferencia tambem -> desliga o ar e avisa no site
    """
    numero = sala["numero"]
    banco.atualizar_sala(numero, pessoas=pessoas, ultima_verificacao=banco.agora())

    if not sala["ligado"]:
        return "Ar desligado: nada a fazer."

    if pessoas > 0:
        banco.atualizar_sala(
            numero, ausencias=0, proxima_verificacao=daqui_a(MINUTOS_COM_PESSOAS)
        )
        return f"{pessoas} pessoa(s) na sala. Nova verificação em {MINUTOS_COM_PESSOAS} min."

    if sala["ausencias"] == 0:
        mensagem = f"Ninguém detectado. Nova verificação em {MINUTOS_SEM_PESSOAS} min."
        banco.atualizar_sala(
            numero, ausencias=1, proxima_verificacao=daqui_a(MINUTOS_SEM_PESSOAS)
        )
        banco.registrar_evento(numero, "VAZIA", mensagem)
        return mensagem

    mudar_energia(sala, False, "DESLIGADO_AUTO", MOTIVO_SALA_VAZIA)
    return MOTIVO_SALA_VAZIA


def aplicar_agenda(hora):
    """Liga/desliga as salas cujo horario programado e igual a 'hora' ("HH:MM")."""
    for sala in banco.listar_salas():
        if sala["hora_ligar"] == hora:
            mudar_energia(sala, True, "LIGADO", f"Ligado pelo horário programado ({hora}).")
        elif sala["hora_desligar"] == hora:
            mudar_energia(sala, False, "DESLIGADO", f"Desligado pelo horário programado ({hora}).")


def vigiar_agenda():
    """Roda em segundo plano: a cada minuto novo, aplica a agenda das salas."""
    ultimo_minuto = None
    while True:
        minuto = datetime.now().strftime("%H:%M")
        if minuto != ultimo_minuto:
            ultimo_minuto = minuto
            try:
                aplicar_agenda(minuto)
            except Exception as erro:  # um erro aqui nao pode parar o relogio
                print(f"Erro ao aplicar a agenda das {minuto}: {erro}")
        time.sleep(10)


# ---------------------------------------------------------------------------
# Funcoes de apoio dos endpoints
# ---------------------------------------------------------------------------
def sala_ou_404(numero):
    """Busca a sala; se o numero nao existir, responde erro 404."""
    sala = banco.buscar_sala(numero)
    if sala is None:
        raise HTTPException(status_code=404, detail=f"Sala {numero} não existe.")
    return sala


def esta_online(tipo, numero):
    """True se o ESP32 ("dispositivo") ou a "camera" da sala falou ha pouco."""
    visto = ultimo_contato[tipo].get(numero)
    return visto is not None and time.time() - visto < SEGUNDOS_ONLINE


def para_o_painel(sala):
    """Completa os dados da sala com o que o painel precisa mostrar."""
    numero = sala["numero"]
    sala["ligado"] = bool(sala["ligado"])
    # True quando foi a regra de presenca que desligou (o painel destaca isso)
    sala["desligado_por_sala_vazia"] = (
        not sala["ligado"] and sala["motivo"] == MOTIVO_SALA_VAZIA
    )
    sala["dispositivo_online"] = esta_online("dispositivo", numero)
    sala["camera_online"] = esta_online("camera", numero)
    temperatura = sala.get("temperatura")
    sala["alerta"] = temperatura is not None and temperatura > LIMITE_TEMPERATURA
    return sala


# ---------------------------------------------------------------------------
# Aplicacao
# ---------------------------------------------------------------------------
app = FastAPI(title="SMAC - Sistema de Monitoramento de Ambiente na Cloud")

# Arquivos de aparencia do site (CSS) ficam na pasta static/
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def ao_iniciar():
    """Prepara o banco e liga o relogio da agenda assim que o servidor sobe."""
    banco.iniciar_banco()
    threading.Thread(target=vigiar_agenda, daemon=True).start()


# ---- usados pelo SITE ------------------------------------------------------
@app.get("/api/salas")
def salas():
    """Todas as salas, com o estado do ar, agenda, presenca e temperatura."""
    return {
        "limite_temperatura": LIMITE_TEMPERATURA,
        "salas": [para_o_painel(sala) for sala in banco.listar_salas()],
    }


@app.post("/api/salas/{numero}/energia")
def controlar_energia(numero: str, pedido: Energia):
    """Liga ou desliga o ar da sala de forma remota (botao do site)."""
    sala = sala_ou_404(numero)
    if pedido.ligado:
        mudar_energia(sala, True, "LIGADO", "Ligado pelo site.")
    else:
        mudar_energia(sala, False, "DESLIGADO", "Desligado pelo site.")
    return para_o_painel(banco.buscar_sala(numero))


@app.put("/api/salas/{numero}/agenda")
def programar_horario(numero: str, agenda: Agenda):
    """Define (ou limpa) o horario diario de ligar e de desligar o ar."""
    sala_ou_404(numero)
    if agenda.hora_ligar and agenda.hora_ligar == agenda.hora_desligar:
        raise HTTPException(
            status_code=422, detail="Os horários de ligar e desligar não podem ser iguais."
        )
    banco.atualizar_sala(
        numero, hora_ligar=agenda.hora_ligar, hora_desligar=agenda.hora_desligar
    )
    return para_o_painel(banco.buscar_sala(numero))


@app.put("/api/salas/{numero}/equipamento")
def renomear_equipamento(numero: str, dados: Equipamento):
    """Troca o nome/modelo do equipamento da sala."""
    sala_ou_404(numero)
    banco.atualizar_sala(numero, equipamento=dados.equipamento.strip())
    return para_o_painel(banco.buscar_sala(numero))


@app.get("/api/eventos")
def eventos(limite: int = 20, sala: Optional[str] = None):
    """Ultimos acontecimentos (avisos do painel). Opcional: so de uma sala."""
    return {"eventos": banco.ultimos_eventos(limite, sala)}


@app.get("/api/leituras")
def historico(sala: str = "101", limite: int = 30):
    """Endpoint que o PAINEL chama para desenhar o grafico do historico."""
    return {"sala": sala, "leituras": banco.ultimas_leituras(sala, limite)}


@app.get("/api/status")
def status(sala: str = "101"):
    """Ultima leitura da sala + avaliacao da temperatura (OK ou ALERTA)."""
    leitura = banco.ultima_leitura(sala)
    if leitura is None:
        return {"sala": sala, "leitura": None, "avaliacao": None}
    avaliacao = avaliar_ambiente(leitura["temperatura"])
    return {"sala": sala, "leitura": leitura, "avaliacao": avaliacao}


# ---- usados pelo ESP32 -----------------------------------------------------
@app.get("/api/salas/{numero}/comando")
def comando(numero: str):
    """
    O ESP32 chama este endereco de tempos em tempos para saber se o ar deve
    estar ligado. Quando a resposta muda, ele dispara o infravermelho.
    """
    sala = sala_ou_404(numero)
    ultimo_contato["dispositivo"][numero] = time.time()
    return {"ligado": bool(sala["ligado"])}


@app.post("/api/leituras")
def receber_leitura(leitura: Leitura):
    """
    Endpoint que o DISPOSITIVO chama para enviar uma medicao.
    Grava a leitura e ja devolve a avaliacao do ambiente.
    """
    sala_ou_404(leitura.sala)
    registro = banco.inserir_leitura(
        leitura.sala, leitura.temperatura, leitura.umidade
    )
    avaliacao = avaliar_ambiente(leitura.temperatura)
    return {"recebido": registro, "avaliacao": avaliacao}


# ---- usados pela CAMERA ----------------------------------------------------
@app.get("/api/salas/{numero}/verificacao")
def hora_de_verificar(numero: str):
    """A camera pergunta: "ja esta na hora de olhar a sala?"."""
    sala = sala_ou_404(numero)
    ultimo_contato["camera"][numero] = time.time()
    proxima = sala["proxima_verificacao"]
    verificar = bool(sala["ligado"]) and proxima is not None and banco.agora() >= proxima
    return {"verificar": verificar}


@app.post("/api/salas/{numero}/presenca")
def informar_presenca(numero: str, presenca: Presenca):
    """A camera informa quantas pessoas viu; a API decide o que fazer."""
    sala = sala_ou_404(numero)
    ultimo_contato["camera"][numero] = time.time()
    decisao = avaliar_presenca(sala, presenca.pessoas)
    return {"decisao": decisao, "sala": para_o_painel(banco.buscar_sala(numero))}


# ---- pagina ----------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def painel():
    """Serve a pagina do painel (o arquivo templates/dashboard.html)."""
    with open("templates/dashboard.html", "r", encoding="utf-8") as arquivo:
        return arquivo.read()
