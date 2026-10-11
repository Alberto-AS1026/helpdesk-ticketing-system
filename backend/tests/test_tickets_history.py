from tests.conftest import assign, create_ticket, set_status


def history(client, headers, tid):
    r = client.get(f"/tickets/{tid}/history", headers=headers)
    assert r.status_code == 200
    return r.json()


def test_historial_registra_quien_y_que(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assign(client, tech, tid)
    set_status(client, tech, tid, "En progreso")
    client.patch(f"/tickets/{tid}/resolution", json={"diagnosis": "Fallo X"}, headers=tech)
    set_status(client, tech, tid, "Resuelto", solution="Arreglo X")

    h = history(client, tech, tid)
    campos = [e["field_name"] for e in h]
    assert campos == ["creado", "assigned_to", "status", "diagnosis", "solution", "status"]

    assert h[0]["user_name"] == "Usuario Uno"
    assert h[0]["new_value"] == "Abierto"
    assert all(e["user_name"] == "Tecnico Uno" for e in h[1:])
    assert (h[2]["old_value"], h[2]["new_value"]) == ("Abierto", "En progreso")
    assert (h[5]["old_value"], h[5]["new_value"]) == ("En progreso", "Resuelto")


def test_historial_no_duplica_si_el_valor_no_cambia(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    for _ in range(2):
        client.patch(f"/tickets/{tid}/resolution", json={"diagnosis": "Igual"}, headers=tech)
    campos = [e["field_name"] for e in history(client, tech, tid)]
    assert campos.count("diagnosis") == 1


def test_usuario_ve_el_historial_de_su_ticket(client, user1):
    tid = create_ticket(client, user1)["id"]
    assert len(history(client, user1, tid)) == 1


def test_comentarios_en_orden_cronologico(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    client.post(f"/tickets/{tid}/comments", json={"comment": "Primero"}, headers=user1)
    client.post(f"/tickets/{tid}/comments", json={"comment": "Segundo"}, headers=tech)

    r = client.get(f"/tickets/{tid}/comments", headers=tech)
    textos = [c["comment"] for c in r.json()]
    assert textos == ["Primero", "Segundo"]
    assert r.json()[1]["author_name"] == "Tecnico Uno"
