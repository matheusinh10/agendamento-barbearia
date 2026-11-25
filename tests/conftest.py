import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    """Cliente de teste com banco SQLite temporário (cada teste começa vazio)."""
    main.DB_FILE = str(tmp_path / "teste.db")
    main.criar_tabelas()
    return TestClient(main.app)


@pytest.fixture()
def dados(client):
    """Fixture: 2 barbeiros, 1 serviço (40 min, R$ 50) e 3 clientes."""
    b1 = client.post("/barbeiros", json={"nome": "João"}).json()
    b2 = client.post("/barbeiros", json={"nome": "Pedro"}).json()
    s = client.post("/servicos", json={"nome": "Corte e barba", "duracao_min": 40, "preco": 50}).json()
    c = [client.post("/clientes", json={"nome": n, "telefone": f"2199999000{i}"}).json()
         for i, n in enumerate(["Ana", "Bruno", "Davi"], start=1)]
    return {"b1": b1["id"], "b2": b2["id"], "s": s["id"], "c": [x["id"] for x in c]}


@pytest.fixture()
def dia():
    """Data futura (7 dias à frente) para os testes não 'vencerem' com o tempo."""
    return (datetime.now() + timedelta(days=7)).date()


def horario(dia, hhmm):
    return f"{dia.isoformat()}T{hhmm}:00"
