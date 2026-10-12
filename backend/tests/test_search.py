import pytest

from tests.conftest import assign, create_ticket, set_status


def listar(client, headers, **params):
    r = client.get("/tickets", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def datos(client, user1, user2, tech):
    """Cinco tickets con distintas características."""
    a = create_ticket(client, user1, title="Wifi lenta en sala 1", priority_id=2, category_id=2)
    b = create_ticket(client, user1, title="Descuento 50% no aplica", priority_id=2, category_id=1)
    c = create_ticket(client, user2, title="Descuento 500 euros", priority_id=1, category_id=1)
    d = create_ticket(client, user2, title="Impresora atascada", priority_id=1, category_id=2)
    e = create_ticket(client, user1, title="Monitor_parpadea", priority_id=1, category_id=1)
    assign(client, tech, a["id"])
    set_status(client, tech, a["id"], "En progreso")
    return {"a": a, "b": b, "c": c, "d": d, "e": e}


def test_sin_filtros_devuelve_estructura_de_pagina(client, tech, datos):
    r = listar(client, tech)
    assert set(r) == {"total", "limit", "offset", "items"}
    assert r["total"] == 5
    assert r["limit"] == 20 and r["offset"] == 0


def test_busqueda_sin_distinguir_mayusculas(client, tech, datos):
    assert listar(client, tech, q="WIFI")["total"] == 1


def test_busqueda_en_descripcion(client, tech, user1):
    create_ticket(client, user1, title="Problema", description="Falla el teclado numérico")
    assert listar(client, tech, q="teclado")["total"] == 1


def test_comodin_porcentaje_se_busca_literal(client, tech, datos):
    r = listar(client, tech, q="50%")
    assert r["total"] == 1
    assert r["items"][0]["title"] == "Descuento 50% no aplica"


def test_comodin_guion_bajo_se_busca_literal(client, tech, datos):
    r = listar(client, tech, q="r_p")
    assert r["total"] == 1
    assert r["items"][0]["title"] == "Monitor_parpadea"


def test_filtros_por_estado_prioridad_y_categoria(client, tech, datos):
    assert listar(client, tech, status="En progreso")["total"] == 1
    assert listar(client, tech, status="Abierto")["total"] == 4
    assert listar(client, tech, priority_id=2)["total"] == 2
    assert listar(client, tech, category_id=2)["total"] == 2
    assert listar(client, tech, priority_id=1, category_id=1)["total"] == 2


def test_filtro_por_tecnico_y_sin_asignar(client, tech, datos):
    assert listar(client, tech, technician_id=1)["total"] == 1
    assert listar(client, tech, unassigned="true")["total"] == 4


def test_filtro_por_fechas(client, tech, datos):
    from datetime import datetime, timedelta, timezone

    # La API interpreta los días en UTC, así que el test también
    hoy = datetime.now(timezone.utc).date()
    assert listar(client, tech, created_from=hoy.isoformat(), created_to=hoy.isoformat())["total"] == 5
    ayer = (hoy - timedelta(days=1)).isoformat()
    assert listar(client, tech, created_to=ayer)["total"] == 0
    manana = (hoy + timedelta(days=1)).isoformat()
    assert listar(client, tech, created_from=manana)["total"] == 0


def test_paginacion_sin_repetidos_y_total_constante(client, tech, datos):
    p1 = listar(client, tech, limit=2, offset=0)
    p2 = listar(client, tech, limit=2, offset=2)
    p3 = listar(client, tech, limit=2, offset=4)
    assert p1["total"] == p2["total"] == p3["total"] == 5
    ids = [t["id"] for p in (p1, p2, p3) for t in p["items"]]
    assert len(ids) == 5 and len(set(ids)) == 5


def test_ordenacion(client, tech, datos):
    asc = [t["id"] for t in listar(client, tech, sort="id", order="asc")["items"]]
    desc = [t["id"] for t in listar(client, tech, sort="id", order="desc")["items"]]
    assert asc == sorted(asc)
    assert desc == sorted(desc, reverse=True)


def test_usuario_ve_solo_los_suyos_con_filtros(client, user2, datos):
    r = listar(client, user2)
    assert r["total"] == 2
    assert {t["creator_name"] for t in r["items"]} == {"Usuario Dos"}
    assert listar(client, user2, q="Wifi")["total"] == 0


@pytest.mark.parametrize(
    "params",
    [
        {"status": "Cancelado"},
        {"limit": 500},
        {"limit": 0},
        {"offset": -1},
        {"sort": "password"},
        {"order": "random"},
        {"q": "a"},
        {"created_from": "ayer"},
    ],
)
def test_parametros_invalidos_dan_422(client, tech, params):
    assert client.get("/tickets", params=params, headers=tech).status_code == 422
