def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_login_correcto_devuelve_token(client):
    r = login(client, "user1@test.example", "Test_Password_1")
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_contrasena_incorrecta(client):
    r = login(client, "user1@test.example", "incorrecta")
    assert r.status_code == 401
    assert r.json()["detail"] == "Email o contraseña incorrectos"


def test_login_email_inexistente_mismo_mensaje(client):
    r = login(client, "nadie@test.example", "Test_Password_1")
    assert r.status_code == 401
    assert r.json()["detail"] == "Email o contraseña incorrectos"


def test_login_usuario_desactivado(client, admin):
    r = client.patch("/users/3", json={"is_active": False}, headers=admin)
    assert r.status_code == 200
    assert login(client, "user1@test.example", "Test_Password_1").status_code == 401


def test_me_sin_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_con_token_no_expone_hash(client, user1):
    r = client.get("/auth/me", headers=user1)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "user1@test.example"
    assert "password_hash" not in body
    assert "password" not in body


def test_token_manipulado(client, user1):
    token = user1["Authorization"] + "x"
    assert client.get("/auth/me", headers={"Authorization": token}).status_code == 401


def test_token_basura(client):
    assert client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_token_de_usuario_desactivado_deja_de_valer(client, admin, user1):
    assert client.patch("/users/3", json={"is_active": False}, headers=admin).status_code == 200
    assert client.get("/auth/me", headers=user1).status_code == 401


def test_limite_de_intentos_bloquea_al_sexto(client):
    for _ in range(5):
        assert login(client, "user1@test.example", "mala").status_code == 401
    r = login(client, "user1@test.example", "Test_Password_1")
    assert r.status_code == 429
    assert "retry-after" in r.headers


def test_limite_no_afecta_a_otros_usuarios(client):
    for _ in range(5):
        login(client, "user1@test.example", "mala")
    assert login(client, "user2@test.example", "Test_Password_1").status_code == 200


def test_un_acierto_reinicia_el_contador(client):
    for _ in range(3):
        login(client, "user1@test.example", "mala")
    assert login(client, "user1@test.example", "Test_Password_1").status_code == 200
    for _ in range(3):
        assert login(client, "user1@test.example", "mala").status_code == 401
    assert login(client, "user1@test.example", "Test_Password_1").status_code == 200
