"""
banco.py — camada de acesso ao banco de dados.

Usa o SQLite, que já vem embutido no Python (biblioteca padrao sqlite3).
Nao precisa instalar nem rodar nenhum servidor de banco: os dados ficam
gravados no arquivo 'smac.db', criado automaticamente na primeira execucao.

Aqui ficam TODAS as funcoes que conversam com o banco. O resto do sistema
(a API) nunca escreve SQL direto: sempre chama uma funcao daqui. Isso mantem
o codigo organizado e facil de explicar no relatorio.

Tabelas:
  salas    -> uma linha por sala (estado do ar, agenda, presenca)
  leituras -> historico de temperatura/umidade enviado pelos dispositivos
  eventos  -> tudo o que aconteceu (ligou, desligou, sala vazia...)
"""

import sqlite3
from datetime import datetime

# Nome do arquivo do banco. Fica na mesma pasta do projeto.
ARQUIVO_BANCO = "smac.db"

# Quantas salas cada bloco tem. A letra do bloco define a centena:
# Bloco A -> 101, 102...   Bloco B -> 201, 202...   Bloco F -> 601, 602...
BLOCOS = {"A": 10, "B": 10, "C": 20, "D": 20, "E": 20, "F": 20}


def agora():
    """Data e hora atuais no formato de texto usado em todo o banco."""
    return datetime.now().isoformat(timespec="seconds")


def gerar_salas():
    """Monta a lista (numero, bloco) de todas as salas, seguindo o padrao."""
    salas = []
    for posicao, (bloco, quantidade) in enumerate(BLOCOS.items(), start=1):
        for n in range(1, quantidade + 1):
            salas.append((str(posicao * 100 + n), bloco))
    return salas


def conectar():
    """Abre uma conexao com o banco e faz as linhas virem como dicionario."""
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    conexao.row_factory = sqlite3.Row  # permite acessar coluna pelo nome
    return conexao


def iniciar_banco():
    """
    Cria as tabelas se ainda nao existirem e cadastra todas as salas.
    Deve ser chamada uma vez quando o sistema sobe.
    """
    conexao = conectar()
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS leituras (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sala        TEXT    NOT NULL,
            temperatura REAL    NOT NULL,
            umidade     REAL    NOT NULL,
            momento     TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS leituras_por_sala ON leituras (sala, id);

        CREATE TABLE IF NOT EXISTS salas (
            numero              TEXT    PRIMARY KEY,
            bloco               TEXT    NOT NULL,
            equipamento         TEXT    NOT NULL,
            ligado              INTEGER NOT NULL DEFAULT 0,
            motivo              TEXT,     -- por que esta ligado/desligado
            mudou_em            TEXT,     -- quando ligou/desligou pela ultima vez
            hora_ligar          TEXT,     -- agenda diaria, "HH:MM" ou vazio
            hora_desligar       TEXT,
            pessoas             INTEGER,  -- resultado da ultima verificacao da camera
            ultima_verificacao  TEXT,
            proxima_verificacao TEXT,
            ausencias           INTEGER NOT NULL DEFAULT 0  -- verificacoes seguidas sem ninguem
        );

        CREATE TABLE IF NOT EXISTS eventos (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            sala     TEXT NOT NULL,
            tipo     TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            momento  TEXT NOT NULL
        );
        """
    )
    # INSERT OR IGNORE: so cadastra as salas que ainda nao estao na tabela
    conexao.executemany(
        "INSERT OR IGNORE INTO salas (numero, bloco, equipamento) VALUES (?, ?, ?)",
        [(numero, bloco, "Central de ar") for numero, bloco in gerar_salas()],
    )
    conexao.commit()
    conexao.close()


# ---------------------------------------------------------------------------
# Leituras (temperatura e umidade)
# ---------------------------------------------------------------------------
def inserir_leitura(sala, temperatura, umidade):
    """Grava uma nova leitura vinda de um dispositivo (ou do simulador)."""
    momento = agora()
    conexao = conectar()
    conexao.execute(
        "INSERT INTO leituras (sala, temperatura, umidade, momento) VALUES (?, ?, ?, ?)",
        (sala, temperatura, umidade, momento),
    )
    conexao.commit()
    conexao.close()
    return {"sala": sala, "temperatura": temperatura, "umidade": umidade, "momento": momento}


def ultima_leitura(sala):
    """Retorna a leitura mais recente de uma sala, ou None se nao houver nenhuma."""
    conexao = conectar()
    linha = conexao.execute(
        "SELECT * FROM leituras WHERE sala = ? ORDER BY id DESC LIMIT 1",
        (sala,),
    ).fetchone()
    conexao.close()
    return dict(linha) if linha else None


def ultimas_leituras(sala, limite=30):
    """
    Retorna as ultimas 'limite' leituras da sala, em ordem cronologica
    (da mais antiga para a mais nova), pronta para desenhar o grafico.
    """
    conexao = conectar()
    linhas = conexao.execute(
        "SELECT * FROM leituras WHERE sala = ? ORDER BY id DESC LIMIT ?",
        (sala, limite),
    ).fetchall()
    conexao.close()
    # vem do banco da mais nova para a mais antiga; invertemos para o grafico
    return [dict(linha) for linha in reversed(linhas)]


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------
def listar_salas():
    """Retorna todas as salas com seu estado e a ultima temperatura medida."""
    conexao = conectar()
    linhas = conexao.execute(
        """
        SELECT s.*,
               (SELECT temperatura FROM leituras l
                 WHERE l.sala = s.numero ORDER BY l.id DESC LIMIT 1) AS temperatura
          FROM salas s
         ORDER BY CAST(s.numero AS INTEGER)
        """
    ).fetchall()
    conexao.close()
    return [dict(linha) for linha in linhas]


def buscar_sala(numero):
    """Retorna uma sala pelo numero (ex.: "101"), ou None se nao existir."""
    conexao = conectar()
    linha = conexao.execute(
        "SELECT * FROM salas WHERE numero = ?", (numero,)
    ).fetchone()
    conexao.close()
    return dict(linha) if linha else None


def atualizar_sala(numero, **campos):
    """
    Altera uma ou mais colunas de uma sala. Exemplo:
        atualizar_sala("101", ligado=1, motivo="Ligado pelo site")
    """
    colunas = ", ".join(f"{nome} = ?" for nome in campos)
    conexao = conectar()
    conexao.execute(
        f"UPDATE salas SET {colunas} WHERE numero = ?",
        (*campos.values(), numero),
    )
    conexao.commit()
    conexao.close()


# ---------------------------------------------------------------------------
# Eventos (o "diario" do sistema, mostrado no site)
# ---------------------------------------------------------------------------
def registrar_evento(sala, tipo, mensagem):
    """Anota algo que aconteceu numa sala (ligou, desligou, sala vazia...)."""
    conexao = conectar()
    conexao.execute(
        "INSERT INTO eventos (sala, tipo, mensagem, momento) VALUES (?, ?, ?, ?)",
        (sala, tipo, mensagem, agora()),
    )
    conexao.commit()
    conexao.close()


def ultimos_eventos(limite=20, sala=None):
    """Retorna os eventos mais recentes (de todas as salas ou de uma so)."""
    conexao = conectar()
    if sala is None:
        linhas = conexao.execute(
            "SELECT * FROM eventos ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    else:
        linhas = conexao.execute(
            "SELECT * FROM eventos WHERE sala = ? ORDER BY id DESC LIMIT ?",
            (sala, limite),
        ).fetchall()
    conexao.close()
    return [dict(linha) for linha in linhas]
