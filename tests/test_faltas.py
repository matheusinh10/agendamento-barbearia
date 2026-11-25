from conftest import horario


def criar(client, d, dia, hhmm="14:00"):
    return client.post("/agendamentos", json={
        "barbeiro_id": d["b1"], "cliente_id": d["c"][0],
        "servico_id": d["s"], "inicio": horario(dia, hhmm)}).json()


def test_falta_libera_horario_e_sugere_encaixe_com_whatsapp(client, dados, dia):
    ag = criar(client, dados, dia)
    client.post("/lista-espera", json={"cliente_id": dados["c"][2], "servico_id": dados["s"],
                                       "data": dia.isoformat()})
    r = client.patch(f"/agendamentos/{ag['id']}/faltou")
    assert r.status_code == 200 and r.json()["status"] == "faltou"
    sugestoes = r.json()["encaixes_sugeridos"]
    assert len(sugestoes) == 1 and sugestoes[0]["cliente"] == "Davi"
    assert sugestoes[0]["whatsapp"].startswith("https://wa.me/5521")


def test_sem_lista_de_espera_nao_ha_sugestoes(client, dados, dia):
    ag = criar(client, dados, dia)
    r = client.patch(f"/agendamentos/{ag['id']}/faltou")
    assert r.json()["encaixes_sugeridos"] == []


def test_lista_de_espera_de_outro_dia_nao_e_sugerida(client, dados, dia):
    ag = criar(client, dados, dia)
    client.post("/lista-espera", json={"cliente_id": dados["c"][2], "servico_id": dados["s"],
                                       "data": "2030-01-01"})
    assert client.patch(f"/agendamentos/{ag['id']}/faltou").json()["encaixes_sugeridos"] == []


def test_horario_da_falta_pode_ser_reagendado(client, dados, dia):
    ag = criar(client, dados, dia)
    client.patch(f"/agendamentos/{ag['id']}/faltou")
    r = client.post("/agendamentos", json={"barbeiro_id": dados["b1"], "cliente_id": dados["c"][1],
                                           "servico_id": dados["s"], "inicio": horario(dia, "14:00")})
    assert r.status_code == 201


def test_relatorio_de_renda_perdida(client, dados, dia):
    assert client.get("/relatorios/faltas").json() == {"total_de_faltas": 0, "renda_perdida": 0}
    a1 = criar(client, dados, dia, "10:00")
    a2 = criar(client, dados, dia, "15:00")
    client.patch(f"/agendamentos/{a1['id']}/faltou")
    client.patch(f"/agendamentos/{a2['id']}/faltou")
    assert client.get("/relatorios/faltas").json() == {"total_de_faltas": 2, "renda_perdida": 100.0}


def test_nao_registra_falta_duas_vezes(client, dados, dia):
    ag = criar(client, dados, dia)
    client.patch(f"/agendamentos/{ag['id']}/faltou")
    assert client.patch(f"/agendamentos/{ag['id']}/faltou").status_code == 400
