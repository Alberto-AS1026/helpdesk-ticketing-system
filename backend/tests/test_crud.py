def test_departamentos_crud_completo(client, admin):
    r = client.post("/departments", json={"name": "Logística", "description": "Almacén"}, headers=admin)
    assert r.status_code == 201
    did = r.json()["id"]

    assert client.post("/departments", json={"name": "Logística"}, headers=admin).status_code == 409
    assert client.post("/departments", json={"name": "A"}, headers=admin).status_code == 422

    r = client.patch(f"/departments/{did}", json={"description": "Nueva"}, headers=admin)
    assert r.status_code == 200 and r.json()["description"] == "Nueva"
    assert r.json()["name"] == "Logística"

    assert client.get(f"/departments/{did}", headers=admin).status_code == 200
    assert client.get("/departments/999", headers=admin).status_code == 404
    assert client.delete(f"/departments/{did}", headers=admin).status_code == 204
    assert client.get(f"/departments/{did}", headers=admin).status_code == 404


def test_departamento_con_usuarios_no_se_borra(client, admin):
    client.post(
        "/users",
        json={"full_name": "Con Depto", "email": "d@test.example", "password": "Secreto1234", "department_id": 1},
        headers=admin,
    )
    assert client.delete("/departments/1", headers=admin).status_code == 409


def test_categorias_duplicada_y_borrado_con_tickets(client, admin, user1):
    assert client.post("/categories", json={"name": "Hardware"}, headers=admin).status_code == 409
    client.post(
        "/tickets",
        json={"title": "Algo roto", "description": "Descripción larga", "priority_id": 1, "category_id": 1},
        headers=user1,
    )
    assert client.delete("/categories/1", headers=admin).status_code == 409


def test_prioridades_validacion_en_dos_capas(client, admin):
    # Pydantic corta antes de llegar a la base de datos
    assert client.post("/priorities", json={"name": "Imposible", "level": 9}, headers=admin).status_code == 422
    # La base de datos protege el nivel repetido
    assert client.post("/priorities", json={"name": "Otra", "level": 3}, headers=admin).status_code == 409


def test_prioridades_ordenadas_por_nivel(client, admin):
    niveles = [p["level"] for p in client.get("/priorities", headers=admin).json()]
    assert niveles == sorted(niveles)


def test_usuarios_nunca_exponen_hash(client, admin):
    r = client.post(
        "/users",
        json={"full_name": "Nuevo", "email": "nuevo@test.example", "password": "Secreto1234"},
        headers=admin,
    )
    assert r.status_code == 201
    assert "password_hash" not in r.json() and "password" not in r.json()
    for u in client.get("/users", headers=admin).json():
        assert "password_hash" not in u


def test_usuarios_validaciones(client, admin):
    base = {"full_name": "Prueba", "email": "p@test.example", "password": "Secreto1234"}
    assert client.post("/users", json={**base, "email": "no-es-email"}, headers=admin).status_code == 422
    assert client.post("/users", json={**base, "password": "123"}, headers=admin).status_code == 422
    assert client.post("/users", json={**base, "role": "jefe"}, headers=admin).status_code == 422
    assert client.post("/users", json={**base, "department_id": 99}, headers=admin).status_code == 422
    assert client.post("/users", json=base, headers=admin).status_code == 201
    assert client.post("/users", json=base, headers=admin).status_code == 409


def test_cambiar_contrasena_permite_nuevo_login(client, admin):
    client.patch("/users/3", json={"password": "Otra_Clave_99"}, headers=admin)
    ok = client.post("/auth/login", data={"username": "user1@test.example", "password": "Otra_Clave_99"})
    viejo = client.post("/auth/login", data={"username": "user1@test.example", "password": "Test_Password_1"})
    assert ok.status_code == 200
    assert viejo.status_code == 401


def test_tecnicos_reglas(client, admin):
    # El usuario 3 tiene rol "user": no puede tener perfil técnico
    assert client.post("/technicians", json={"user_id": 3}, headers=admin).status_code == 422
    # Usuario inexistente
    assert client.post("/technicians", json={"user_id": 99}, headers=admin).status_code == 422
    # El usuario 2 ya es técnico
    assert client.post("/technicians", json={"user_id": 2}, headers=admin).status_code == 409


def test_equipos_crud_y_referencias(client, tech):
    r = client.post("/computers", json={"hostname": "PC-01", "assigned_to": 3, "department_id": 1}, headers=tech)
    assert r.status_code == 201
    cid = r.json()["id"]

    assert client.post("/computers", json={"hostname": "PC-01"}, headers=tech).status_code == 409
    assert client.post("/computers", json={"hostname": "PC-02", "assigned_to": 99}, headers=tech).status_code == 422
    assert client.post("/computers", json={"hostname": "PC-03", "department_id": 99}, headers=tech).status_code == 422
    assert client.post("/computers", json={"hostname": "A"}, headers=tech).status_code == 422

    r = client.patch(f"/computers/{cid}", json={"assigned_to": 4}, headers=tech)
    assert r.status_code == 200 and r.json()["assigned_to"] == 4


def test_borrar_equipo_deja_el_ticket_sin_equipo(client, tech, user1):
    cid = client.post("/computers", json={"hostname": "PC-09"}, headers=tech).json()["id"]
    t = client.post(
        "/tickets",
        json={"title": "Equipo lento", "description": "Va muy lento", "priority_id": 1, "category_id": 1, "computer_id": cid},
        headers=user1,
    ).json()
    assert t["computer_id"] == cid
    assert client.delete(f"/computers/{cid}", headers=tech).status_code == 204
    assert client.get(f"/tickets/{t['id']}", headers=user1).json()["computer_id"] is None
