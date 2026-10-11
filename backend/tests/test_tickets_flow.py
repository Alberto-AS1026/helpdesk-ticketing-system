from tests.conftest import assign, create_ticket, set_status


def test_crear_ticket_estado_abierto_y_a_nombre_del_token(client, user1):
    t = create_ticket(client, user1)
    assert t["status"] == "Abierto"
    assert t["created_by"] == 3
    assert t["creator_name"] == "Usuario Uno"
    assert t["technician_name"] is None
    assert t["priority_name"] == "Baja"
    assert t["category_name"] == "Hardware"


def test_no_se_puede_elegir_estado_ni_creador(client, user1):
    t = create_ticket(client, user1, status="Cerrado", created_by=4)
    assert t["status"] == "Abierto"
    assert t["created_by"] == 3


def test_flujo_completo_hasta_cerrado(client, user1, tech):
    t = create_ticket(client, user1)
    tid = t["id"]

    r = assign(client, tech, tid)
    assert r.status_code == 200
    assert r.json()["technician_name"] == "Tecnico Uno"

    assert set_status(client, tech, tid, "En progreso").status_code == 200

    r = set_status(client, tech, tid, "Resuelto", diagnosis="Cable suelto", solution="Cable reconectado")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "Resuelto"
    assert body["diagnosis"] == "Cable suelto"
    assert body["solution"] == "Cable reconectado"
    assert body["resolved_at"] is not None
    assert body["resolution_minutes"] >= 0

    r = set_status(client, tech, tid, "Cerrado")
    assert r.status_code == 200
    assert r.json()["status"] == "Cerrado"


def test_pendiente_y_vuelta_a_en_progreso(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assign(client, tech, tid)
    set_status(client, tech, tid, "En progreso")
    assert set_status(client, tech, tid, "Pendiente").status_code == 200
    assert set_status(client, tech, tid, "En progreso").status_code == 200


def test_reabrir_ticket_resuelto_vacia_fechas_y_conserva_textos(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assign(client, tech, tid)
    set_status(client, tech, tid, "En progreso")
    set_status(client, tech, tid, "Resuelto", diagnosis="Fallo A", solution="Arreglo A")

    r = set_status(client, tech, tid, "En progreso")
    assert r.status_code == 200
    body = r.json()
    assert body["resolved_at"] is None
    assert body["resolution_minutes"] is None
    assert body["diagnosis"] == "Fallo A"

    # Se puede volver a resolver sin repetir diagnóstico ni solución
    r = set_status(client, tech, tid, "Resuelto")
    assert r.status_code == 200
    assert r.json()["resolved_at"] is not None


def test_diagnostico_y_solucion_sin_cambiar_estado(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    r = client.patch(f"/tickets/{tid}/resolution", json={"diagnosis": "Fuente averiada"}, headers=tech)
    assert r.status_code == 200
    r = client.patch(f"/tickets/{tid}/resolution", json={"solution": "Cambio de fuente"}, headers=tech)
    body = r.json()
    assert body["status"] == "Abierto"
    assert body["diagnosis"] == "Fuente averiada"
    assert body["solution"] == "Cambio de fuente"
