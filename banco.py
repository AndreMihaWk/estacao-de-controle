"""
banco.py — camada de acesso ao banco de dados.

Usa o SQLite, que já vem embutido no Python (biblioteca padrao sqlite3).
Nao precisa instalar nem rodar nenhum servidor de banco: os dados ficam
gravados no arquivo 'smac.db', criado automaticamente na primeira execucao.

Aqui ficam TODAS as funcoes que conversam com o banco. O resto do sistema
(a API) nunca escreve SQL direto: sempre chama uma funcao daqui. Isso mantem
o codigo organizado e facil de explicar no relatorio.
"""

import sqlite3
from datetime import datetime

# Nome do arquivo do banco. Fica na mesma pasta do projeto.
ARQUIVO_BANCO = "smac.db"


def conectar():
    """Abre uma conexao com o banco e faz as linhas virem como dicionario."""
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    conexao.row_factory = sqlite3.Row  # permite acessar coluna pelo nome
    return conexao


def iniciar_banco():
    """
    Cria a tabela de leituras se ela ainda nao existir.
    Deve ser chamada uma vez quando o sistema sobe.
    """
    conexao = conectar()
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS leituras (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sala        TEXT    NOT NULL,
            temperatura REAL    NOT NULL,
            umidade     REAL    NOT NULL,
            momento     TEXT    NOT NULL
        )
        """
    )
    conexao.commit()
    conexao.close()


def inserir_leitura(sala, temperatura, umidade):
    """Grava uma nova leitura vinda de um dispositivo (ou do simulador)."""
    momento = datetime.now().isoformat(timespec="seconds")
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


def listar_salas():
    """Retorna a lista de salas que ja enviaram alguma leitura."""
    conexao = conectar()
    linhas = conexao.execute(
        "SELECT DISTINCT sala FROM leituras ORDER BY sala"
    ).fetchall()
    conexao.close()
    return [linha["sala"] for linha in linhas]
