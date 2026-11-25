from conftest import horario


def agendar(client, d, barbeiro, cliente, hhmm):
    return client.post("/agendamentos", json={
        "barbeiro_id": barbeiro, "cliente_id": cliente,
        "servico_id": d["s"], "inicio": horario(hhmm[0], hhmm[1])})


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_cria_agendamento_e_calcula_fim(client, dados, dia):
    r = agendar(client, dados, dados["b1"], dados["c"][0], (dia, "14:00"))
    assert r.status_code == 201
    assert r.json()["fim"].endswith("14:40:00")  # 14:00 + 40 min


def test_conflito_de_horario_retorna_409(client, dados, dia):
    assert agendar(client, dados, dados["b1"], dados["c"][0], (dia, "14:00")).status_code == 201
    r = agendar(client, dados, dados["b1"], dados["c"][1], (dia, "14:20"))
    assert r.status_code == 409


def test_outro_barbeiro_no_mesmo_horario_e_permitido(client, dados, dia):
    agendar(client, dados, dados["b1"], dados["c"][0], (dia, "14:00"))
    r = agendar(client, dados, dados["b2"], dados["c"][1], (dia, "14:00"))
    assert r.status_code == 201


def test_horario_exatamente_apos_o_fim_e_permitido(client, dados, dia):
    agendar(client, dados, dados["b1"], dados["c"][0], (dia, "14:00"))
    assert agendar(client, dados, dados["b1"], dados["c"][1], (dia, "14:40")).status_code == 201


def test_fora_do_expediente_retorna_400(client, dados, dia):
    assert agendar(client, dados, dados["b1"], dados["c"][0], (dia, "08:00")).status_code == 400
    assert agendar(client, dados, dados["b1"], dados["c"][0], (dia, "18:40")).status_code == 400  # termina 19:20


def test_passado_retorna_400(client, dados):
    r = client.post("/agendamentos", json={
        "barbeiro_id": dados["b1"], "cliente_id": dados["c"][0],
        "servico_id": dados["s"], "inicio": "2020-01-01T10:00:00"})
    assert r.status_code == 400


def test_horario_com_fuso_z_e_aceito(client, dados, dia):
    r = client.post("/agendamentos", json={
        "barbeiro_id": dados["b1"], "cliente_id": dados["c"][0],
        "servico_id": dados["s"], "inicio": f"{dia.isoformat()}T14:00:00.000Z"})
    assert r.status_code == 201


def test_ids_inexistentes_retornam_404(client, dados, dia):
    assert agendar(client, dados, 999, dados["c"][0], (dia, "14:00")).status_code == 404


def test_horarios_disponiveis_excluem_ocupados(client, dados, dia):
    agendar(client, dados, dados["b1"], dados["c"][0], (dia, "14:00"))
    r = client.get(f"/barbeiros/{dados['b1']}/horarios-disponiveis",
                   params={"data": dia.isoformat(), "servico_id": dados["s"]})
    livres = r.json()["horarios_livres"]
    assert "14:00" not in livres and "14:30" not in livres
    assert "09:00" in livres and "15:00" in livres


def test_remarcar_e_cancelar(client, dados, dia):
    ag = agendar(client, dados, dados["b1"], dados["c"][0], (dia, "14:00")).json()
    r = client.patch(f"/agendamentos/{ag['id']}/remarcar", json={"novo_inicio": horario(dia, "16:00")})
    assert r.status_code == 200 and r.json()["inicio"].endswith("16:00:00")
    assert client.patch(f"/agendamentos/{ag['id']}/cancelar").json()["status"] == "cancelado"
    # horário cancelado volta a ficar livre
    assert agendar(client, dados, dados["b1"], dados["c"][1], (dia, "16:00")).status_code == 201
    # não cancela duas vezes
    assert client.patch(f"/agendamentos/{ag['id']}/cancelar").status_code == 400
