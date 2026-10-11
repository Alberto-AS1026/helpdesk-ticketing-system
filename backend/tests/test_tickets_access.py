from tests.conftest import assign, create_ticket, set_status


def test_usuario_solo_lista_sus_tickets(client, user1, user2, tech):
    create_ticket(client, user1, title="Ticket de uno")
    create_ticket(client, user2, title="Ticket de dos")

    r = client.get("/tickets", headers=user1)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "Ticket de uno"

    assert client.get("/tickets", headers=tech).json()["total"] == 2


def test_ticket_ajeno_da_404_no_403(client, user1, user2):
    tid = create_ticket(client, user1)["id"]
    assert client.get(f"/tickets/{tid}", headers=user2).status_code == 404


def test_comentarios_e_historial_ajenos_dan_404(client, user1, user2):
    tid = create_ticket(client, user1)["id"]
    assert client.get(f"/tickets/{tid}/comments", headers=user2).status_code == 404
    assert client.get(f"/tickets/{tid}/history", headers=user2).status_code == 404
    r = client.post(f"/tickets/{tid}/comments", json={"comment": "Intruso"}, headers=user2)
    assert r.status_code == 404


def test_busqueda_no_permite_saltarse_la_visibilidad(client, user1, user2):
    create_ticket(client, user1, title="Impresora rota")
    r = client.get("/tickets", params={"q": "Impresora"}, headers=user2)
    assert r.json()["total"] == 0


def test_usuario_no_puede_asignar_ni_cambiar_estado_ni_diagnosticar(client, user1):
    tid = create_ticket(client, user1)["id"]
    assert assign(client, user1, tid).status_code == 403
    assert set_status(client, user1, tid, "En progreso").status_code == 403
    r = client.patch(f"/tickets/{tid}/resolution", json={"solution": "Lo hago yo"}, headers=user1)
    assert r.status_code == 403


def test_usuario_si_puede_comentar_en_su_ticket(client, user1):
    tid = create_ticket(client, user1)["id"]
    r = client.post(f"/tickets/{tid}/comments", json={"comment": "Sigue igual"}, headers=user1)
    assert r.status_code == 201
    assert r.json()["author_name"] == "Usuario Uno"


def test_tickets_sin_token(client):
    assert client.get("/tickets").status_code == 401
    assert client.post("/tickets", json={}).status_code == 401


def test_stats_solo_personal_tecnico(client, user1, tech, admin):
    assert client.get("/stats", headers=user1).status_code == 403
    assert client.get("/stats", headers=tech).status_code == 200
    assert client.get("/stats", headers=admin).status_code == 200


def test_comentario_corto_da_422(client, user1):
    tid = create_ticket(client, user1)["id"]
    r = client.post(f"/tickets/{tid}/comments", json={"comment": "a"}, headers=user1)
    assert r.status_code == 422
