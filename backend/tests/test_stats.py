from tests.conftest import assign, create_ticket, set_status


def stats(client, headers, **params):
    r = client.get("/stats", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def por_etiqueta(items):
    return {i["label"]: i["count"] for i in items}


def test_estadisticas_con_base_vacia(client, tech):
    s = stats(client, tech)
    assert s["summary"]["total_tickets"] == 0
    assert s["summary"]["avg_resolution_minutes"] is None
    # Los grupos a cero aparecen igualmente (LEFT JOIN)
    assert por_etiqueta(s["by_status"]) == {
        "Abierto": 0, "En progreso": 0, "Pendiente": 0, "Resuelto": 0, "Cerrado": 0,
    }
    assert por_etiqueta(s["by_category"]) == {"Hardware": 0, "Software": 0}
    assert s["technician_load"][0]["total_tickets"] == 0


def test_estadisticas_con_datos_conocidos(client, tech, user1):
    t1 = create_ticket(client, user1, priority_id=2, category_id=1)
    t2 = create_ticket(client, user1, priority_id=1, category_id=1)
    create_ticket(client, user1, priority_id=1, category_id=2)

    assign(client, tech, t1["id"])
    set_status(client, tech, t1["id"], "En progreso")
    set_status(client, tech, t1["id"], "Resuelto", diagnosis="Fallo", solution="Arreglo")
    assign(client, tech, t2["id"])

    s = stats(client, tech)
    assert s["summary"]["total_tickets"] == 3
    assert s["summary"]["resolved_tickets"] == 1
    assert s["summary"]["open_tickets"] == 2
    assert s["summary"]["unassigned_tickets"] == 1
    assert s["summary"]["avg_resolution_minutes"] is not None

    assert por_etiqueta(s["by_status"])["Abierto"] == 2
    assert por_etiqueta(s["by_status"])["Resuelto"] == 1
    assert por_etiqueta(s["by_priority"]) == {"Alta": 1, "Baja": 2}
    assert por_etiqueta(s["by_category"]) == {"Hardware": 2, "Software": 1}

    carga = s["technician_load"][0]
    assert carga["name"] == "Tecnico Uno"
    assert carga["total_tickets"] == 2
    assert carga["open_tickets"] == 1


def test_tickets_por_dia(client, tech, user1):
    create_ticket(client, user1)
    create_ticket(client, user1)
    dias = stats(client, tech)["per_day"]
    assert sum(d["count"] for d in dias) == 2


def test_parametro_days_validado(client, tech):
    assert client.get("/stats", params={"days": 0}, headers=tech).status_code == 422
    assert client.get("/stats", params={"days": 1000}, headers=tech).status_code == 422
    assert client.get("/stats", params={"days": 7}, headers=tech).status_code == 200
