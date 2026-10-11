import pytest

from tests.conftest import assign, create_ticket, set_status


def test_en_progreso_exige_tecnico(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    r = set_status(client, tech, tid, "En progreso")
    assert r.status_code == 409
    assert "técnico asignado" in r.json()["detail"]


@pytest.mark.parametrize("destino", ["Pendiente", "Resuelto", "Cerrado"])
def test_transiciones_ilegales_desde_abierto(client, user1, tech, destino):
    tid = create_ticket(client, user1)["id"]
    r = set_status(client, tech, tid, destino, diagnosis="Algo", solution="Algo")
    assert r.status_code == 409
    assert "Transición no permitida" in r.json()["detail"]


def test_mismo_estado_da_409(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assert set_status(client, tech, tid, "Abierto").status_code == 409


def test_estado_inventado_da_422(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assert set_status(client, tech, tid, "Cancelado").status_code == 422


def test_resolver_sin_diagnostico_ni_solucion(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assign(client, tech, tid)
    set_status(client, tech, tid, "En progreso")

    r = set_status(client, tech, tid, "Resuelto")
    assert r.status_code == 422
    assert "diagnóstico" in r.json()["detail"]

    r = set_status(client, tech, tid, "Resuelto", diagnosis="Solo diagnóstico")
    assert r.status_code == 422
    assert "solución" in r.json()["detail"]


def test_ticket_cerrado_es_estado_final(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assign(client, tech, tid)
    set_status(client, tech, tid, "En progreso")
    set_status(client, tech, tid, "Resuelto", diagnosis="Fallo", solution="Arreglo")
    set_status(client, tech, tid, "Cerrado")

    assert set_status(client, tech, tid, "En progreso").status_code == 409
    assert assign(client, tech, tid).status_code == 409
    r = client.patch(f"/tickets/{tid}/resolution", json={"solution": "Cambio"}, headers=tech)
    assert r.status_code == 409
    r = client.post(f"/tickets/{tid}/comments", json={"comment": "¿Sigue?"}, headers=tech)
    assert r.status_code == 409


def test_no_se_asigna_ticket_resuelto(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assign(client, tech, tid)
    set_status(client, tech, tid, "En progreso")
    set_status(client, tech, tid, "Resuelto", diagnosis="Fallo", solution="Arreglo")
    assert assign(client, tech, tid).status_code == 409


def test_asignar_tecnico_inexistente(client, user1, tech):
    tid = create_ticket(client, user1)["id"]
    assert assign(client, tech, tid, technician_id=99).status_code == 422


def test_asignar_tecnico_inactivo(client, user1, tech, admin):
    tid = create_ticket(client, user1)["id"]
    r = client.patch("/technicians/1", json={"is_active": False}, headers=admin)
    assert r.status_code == 200
    assert assign(client, tech, tid).status_code == 422


@pytest.mark.parametrize(
    "cambio",
    [
        {"title": "x"},
        {"description": "abcd"},
        {"priority_id": 99},
        {"category_id": 99},
        {"computer_id": 99},
    ],
)
def test_crear_ticket_con_datos_invalidos(client, user1, cambio):
    body = {
        "title": "Título válido",
        "description": "Descripción válida",
        "priority_id": 1,
        "category_id": 1,
    }
    body.update(cambio)
    r = client.post("/tickets", json=body, headers=user1)
    assert r.status_code == 422


def test_ticket_inexistente(client, tech):
    assert client.get("/tickets/999", headers=tech).status_code == 404
    assert set_status(client, tech, 999, "En progreso").status_code == 404


def test_descripcion_de_cinco_caracteres_es_valida(client, user1):
    body = {"title": "Título válido", "description": "abcde", "priority_id": 1, "category_id": 1}
    assert client.post("/tickets", json=body, headers=user1).status_code == 201
