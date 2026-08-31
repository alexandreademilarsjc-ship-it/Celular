import sqlite3
import threading

CAMINHO_DB = "leads.db"
_lock = threading.Lock()


def _conectar():
    conexao = sqlite3.connect(CAMINHO_DB)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    with _conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                telefone TEXT PRIMARY KEY,
                nome TEXT,
                quente INTEGER NOT NULL DEFAULT 0,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefone TEXT NOT NULL,
                role TEXT NOT NULL,
                texto TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def obter_ou_criar_lead(telefone, nome):
    with _lock, _conectar() as conexao:
        conexao.execute("INSERT OR IGNORE INTO leads (telefone, nome) VALUES (?, ?)", (telefone, nome))
        if nome:
            conexao.execute(
                "UPDATE leads SET nome = ? WHERE telefone = ? AND nome IS NULL", (nome, telefone)
            )
        linha = conexao.execute(
            "SELECT telefone, nome, quente FROM leads WHERE telefone = ?", (telefone,)
        ).fetchone()
        return dict(linha)


def salvar_mensagem(telefone, role, texto):
    with _lock, _conectar() as conexao:
        conexao.execute(
            "INSERT INTO mensagens (telefone, role, texto) VALUES (?, ?, ?)", (telefone, role, texto)
        )


def obter_historico(telefone, limite=30):
    with _conectar() as conexao:
        linhas = conexao.execute(
            "SELECT role, texto FROM mensagens WHERE telefone = ? ORDER BY id ASC LIMIT ?",
            (telefone, limite),
        ).fetchall()
        return [dict(linha) for linha in linhas]


def marcar_quente(telefone):
    with _lock, _conectar() as conexao:
        conexao.execute("UPDATE leads SET quente = 1 WHERE telefone = ?", (telefone,))
