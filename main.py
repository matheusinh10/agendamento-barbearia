"""
API de Agendamento para Barbearia - Projeto de Extensão (UniCarioca)
Stack: Python + FastAPI + SQLite
Documentação interativa automática em: http://127.0.0.1:8000/docs
"""
import sqlite3
from datetime import datetime, timedelta, date, time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from urllib.parse import quote

DB_FILE = "barbearia.db"
ABRE = time(9, 0)    # horário de abertura
FECHA = time(19, 0)  # horário de fechamento
PASSO_MIN = 30       # intervalo entre horários sugeridos

app = FastAPI(
    title="API de Agendamento - Barbearia",
    description="Back-end para cadastro de barbeiros, serviços, clientes e agendamentos, "
                "com validação de conflito de horário.",
    version="1.0.0",
)


# ---------- Banco de dados ----------
def conectar():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def criar_tabelas():
    con = conectar()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS barbeiros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        duracao_min INTEGER NOT NULL,
        preco REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barbeiro_id INTEGER NOT NULL REFERENCES barbeiros(id),
        cliente_id INTEGER NOT NULL REFERENCES clientes(id),
        servico_id INTEGER NOT NULL REFERENCES servicos(id),
        inicio TEXT NOT NULL,
        fim TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'agendado'  -- agendado | cancelado | faltou
    );
    CREATE TABLE IF NOT EXISTS lista_espera (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id),
        servico_id INTEGER NOT NULL REFERENCES servicos(id),
        data TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'aguardando'
    );
    """)
    con.commit()
    con.close()


criar_tabelas()


# ---------- Modelos de entrada ----------
class BarbeiroIn(BaseModel):
    nome: str


class ServicoIn(BaseModel):
    nome: str
    duracao_min: int
    preco: float


class ClienteIn(BaseModel):
    nome: str
    telefone: str


def sem_fuso(v: datetime) -> datetime:
    """Remove o fuso horário (o 'Z' do final), para comparar com a hora local."""
    return v.replace(tzinfo=None) if v.tzinfo else v


class AgendamentoIn(BaseModel):
    barbeiro_id: int
    cliente_id: int
    servico_id: int
    inicio: datetime  # ex.: 2026-10-20T14:00:00

    _fuso = field_validator("inicio")(sem_fuso)


class RemarcarIn(BaseModel):
    novo_inicio: datetime

    _fuso = field_validator("novo_inicio")(sem_fuso)


class EsperaIn(BaseModel):
    cliente_id: int
    servico_id: int
    data: date  # dia em que o cliente aceita ser encaixado


# ---------- Funções auxiliares ----------
def buscar_ou_404(con, tabela, id_, nome):
    linha = con.execute(f"SELECT * FROM {tabela} WHERE id = ?", (id_,)).fetchone()
    if linha is None:
        raise HTTPException(404, f"{nome} não encontrado(a)")
    return linha


def validar_horario(con, barbeiro_id, inicio, fim, ignorar_id=None):
    """Regra principal: dentro do expediente, no futuro e sem conflito."""
    if inicio < datetime.now():
        raise HTTPException(400, "Não é possível agendar no passado")
    if inicio.time() < ABRE or fim.time() > FECHA or inicio.date() != fim.date():
        raise HTTPException(400, f"Fora do expediente ({ABRE:%H:%M} às {FECHA:%H:%M})")
    conflito = con.execute(
        """SELECT id FROM agendamentos
           WHERE barbeiro_id = ? AND status = 'agendado'
             AND inicio < ? AND fim > ? AND id != ?""",
        (barbeiro_id, fim.isoformat(), inicio.isoformat(), ignorar_id or -1),
    ).fetchone()
    if conflito:
        raise HTTPException(409, "Conflito: o barbeiro já tem atendimento nesse horário")


# ---------- Barbeiros ----------
@app.post("/barbeiros", status_code=201, tags=["Barbeiros"])
def criar_barbeiro(dados: BarbeiroIn):
    con = conectar()
    cur = con.execute("INSERT INTO barbeiros (nome) VALUES (?)", (dados.nome,))
    con.commit()
    return {"id": cur.lastrowid, **dados.model_dump()}


@app.get("/barbeiros", tags=["Barbeiros"])
def listar_barbeiros():
    return [dict(l) for l in conectar().execute("SELECT * FROM barbeiros")]


# ---------- Serviços ----------
@app.post("/servicos", status_code=201, tags=["Serviços"])
def criar_servico(dados: ServicoIn):
    if dados.duracao_min <= 0 or dados.preco < 0:
        raise HTTPException(400, "Duração deve ser > 0 e preço >= 0")
    con = conectar()
    cur = con.execute(
        "INSERT INTO servicos (nome, duracao_min, preco) VALUES (?, ?, ?)",
        (dados.nome, dados.duracao_min, dados.preco),
    )
    con.commit()
    return {"id": cur.lastrowid, **dados.model_dump()}


@app.get("/servicos", tags=["Serviços"])
def listar_servicos():
    return [dict(l) for l in conectar().execute("SELECT * FROM servicos")]


# ---------- Clientes ----------
@app.post("/clientes", status_code=201, tags=["Clientes"])
def criar_cliente(dados: ClienteIn):
    con = conectar()
    cur = con.execute(
        "INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (dados.nome, dados.telefone)
    )
    con.commit()
    return {"id": cur.lastrowid, **dados.model_dump()}


@app.get("/clientes", tags=["Clientes"])
def listar_clientes():
    return [dict(l) for l in conectar().execute("SELECT * FROM clientes")]


# ---------- Agendamentos ----------
@app.post("/agendamentos", status_code=201, tags=["Agendamentos"])
def criar_agendamento(dados: AgendamentoIn):
    con = conectar()
    buscar_ou_404(con, "barbeiros", dados.barbeiro_id, "Barbeiro")
    buscar_ou_404(con, "clientes", dados.cliente_id, "Cliente")
    servico = buscar_ou_404(con, "servicos", dados.servico_id, "Serviço")
    fim = dados.inicio + timedelta(minutes=servico["duracao_min"])
    validar_horario(con, dados.barbeiro_id, dados.inicio, fim)
    cur = con.execute(
        """INSERT INTO agendamentos (barbeiro_id, cliente_id, servico_id, inicio, fim)
           VALUES (?, ?, ?, ?, ?)""",
        (dados.barbeiro_id, dados.cliente_id, dados.servico_id,
         dados.inicio.isoformat(), fim.isoformat()),
    )
    con.commit()
    return {"id": cur.lastrowid, "inicio": dados.inicio, "fim": fim, "status": "agendado"}


@app.get("/agendamentos", tags=["Agendamentos"])
def listar_agendamentos():
    return [dict(l) for l in conectar().execute("SELECT * FROM agendamentos ORDER BY inicio")]


@app.patch("/agendamentos/{agendamento_id}/cancelar", tags=["Agendamentos"])
def cancelar_agendamento(agendamento_id: int):
    con = conectar()
    ag = buscar_ou_404(con, "agendamentos", agendamento_id, "Agendamento")
    if ag["status"] != "agendado":
        raise HTTPException(400, "Só é possível cancelar agendamentos ativos")
    con.execute("UPDATE agendamentos SET status = 'cancelado' WHERE id = ?", (agendamento_id,))
    con.commit()
    return {"id": agendamento_id, "status": "cancelado", "encaixes_sugeridos": sugerir_encaixes(con, ag)}


@app.patch("/agendamentos/{agendamento_id}/faltou", tags=["Faltas e encaixes"])
def registrar_falta(agendamento_id: int):
    """Marca que o cliente faltou, libera o horário e sugere quem pode ser encaixado."""
    con = conectar()
    ag = buscar_ou_404(con, "agendamentos", agendamento_id, "Agendamento")
    if ag["status"] != "agendado":
        raise HTTPException(400, "Só é possível registrar falta em agendamentos ativos")
    con.execute("UPDATE agendamentos SET status = 'faltou' WHERE id = ?", (agendamento_id,))
    con.commit()
    return {"id": agendamento_id, "status": "faltou", "encaixes_sugeridos": sugerir_encaixes(con, ag)}


@app.patch("/agendamentos/{agendamento_id}/remarcar", tags=["Agendamentos"])
def remarcar_agendamento(agendamento_id: int, dados: RemarcarIn):
    con = conectar()
    ag = buscar_ou_404(con, "agendamentos", agendamento_id, "Agendamento")
    if ag["status"] != "agendado":
        raise HTTPException(400, "Só é possível remarcar agendamentos ativos")
    duracao = datetime.fromisoformat(ag["fim"]) - datetime.fromisoformat(ag["inicio"])
    novo_fim = dados.novo_inicio + duracao
    validar_horario(con, ag["barbeiro_id"], dados.novo_inicio, novo_fim, ignorar_id=agendamento_id)
    con.execute(
        "UPDATE agendamentos SET inicio = ?, fim = ? WHERE id = ?",
        (dados.novo_inicio.isoformat(), novo_fim.isoformat(), agendamento_id),
    )
    con.commit()
    return {"id": agendamento_id, "inicio": dados.novo_inicio, "fim": novo_fim}


# ---------- Horários disponíveis ----------
@app.get("/barbeiros/{barbeiro_id}/horarios-disponiveis", tags=["Agendamentos"])
def horarios_disponiveis(barbeiro_id: int, data: date, servico_id: int):
    """Lista os horários livres de um barbeiro em um dia, para um serviço."""
    con = conectar()
    buscar_ou_404(con, "barbeiros", barbeiro_id, "Barbeiro")
    servico = buscar_ou_404(con, "servicos", servico_id, "Serviço")
    duracao = timedelta(minutes=servico["duracao_min"])
    ocupados = [
        (datetime.fromisoformat(l["inicio"]), datetime.fromisoformat(l["fim"]))
        for l in con.execute(
            "SELECT inicio, fim FROM agendamentos WHERE barbeiro_id = ? AND status = 'agendado' "
            "AND substr(inicio, 1, 10) = ?", (barbeiro_id, data.isoformat()))
    ]
    livres = []
    atual = datetime.combine(data, ABRE)
    limite = datetime.combine(data, FECHA)
    while atual + duracao <= limite:
        fim = atual + duracao
        if atual > datetime.now() and all(not (atual < f and fim > i) for i, f in ocupados):
            livres.append(atual.strftime("%H:%M"))
        atual += timedelta(minutes=PASSO_MIN)
    return {"data": data, "barbeiro_id": barbeiro_id, "horarios_livres": livres}


# ---------- Faltas, lista de espera e notificações ----------
def link_whatsapp(telefone: str, mensagem: str) -> str:
    numero = "".join(c for c in telefone if c.isdigit())
    if not numero.startswith("55"):
        numero = "55" + numero
    return f"https://wa.me/{numero}?text={quote(mensagem)}"


def sugerir_encaixes(con, ag):
    """Quando um horário é liberado, lista clientes em espera para aquele dia
    e gera o link do WhatsApp com a mensagem pronta para oferecer o horário."""
    dia = ag["inicio"][:10]
    hora = ag["inicio"][11:16]
    espera = con.execute(
        """SELECT e.id, c.nome, c.telefone FROM lista_espera e
           JOIN clientes c ON c.id = e.cliente_id
           WHERE e.data = ? AND e.status = 'aguardando' ORDER BY e.id""", (dia,)).fetchall()
    return [
        {
            "espera_id": e["id"],
            "cliente": e["nome"],
            "whatsapp": link_whatsapp(
                e["telefone"], f"Olá {e['nome']}! Abriu um horário hoje às {hora} na barbearia. Quer encaixar?"),
        }
        for e in espera
    ]


@app.post("/lista-espera", status_code=201, tags=["Faltas e encaixes"])
def entrar_na_lista_de_espera(dados: EsperaIn):
    con = conectar()
    buscar_ou_404(con, "clientes", dados.cliente_id, "Cliente")
    buscar_ou_404(con, "servicos", dados.servico_id, "Serviço")
    cur = con.execute(
        "INSERT INTO lista_espera (cliente_id, servico_id, data) VALUES (?, ?, ?)",
        (dados.cliente_id, dados.servico_id, dados.data.isoformat()))
    con.commit()
    return {"id": cur.lastrowid, "status": "aguardando"}


@app.get("/relatorios/faltas", tags=["Faltas e encaixes"])
def relatorio_de_faltas():
    """Quantas faltas ocorreram e quanto de renda foi perdido."""
    con = conectar()
    r = con.execute(
        """SELECT COUNT(*) AS total, COALESCE(SUM(s.preco), 0) AS perdido
           FROM agendamentos a JOIN servicos s ON s.id = a.servico_id
           WHERE a.status = 'faltou'""").fetchone()
    return {"total_de_faltas": r["total"], "renda_perdida": r["perdido"]}
