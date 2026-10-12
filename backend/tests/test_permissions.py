import pytest

# (método, ruta, cuerpo, código esperado para: sin token, user, tech, admin)
# En escrituras se usa un cuerpo inválido (422) cuando el rol SÍ tiene permiso,
# para no crear datos: lo que importa es distinguir 401/403 de "pasó el control".
CASES = [
    # Catálogos: leer todos, escribir solo admin
    ("GET", "/departments", None, (401, 200, 200, 200)),
    ("POST", "/departments", {}, (401, 403, 403, 422)),
    ("GET", "/categories", None, (401, 200, 200, 200)),
    ("POST", "/categories", {}, (401, 403, 403, 422)),
    ("GET", "/priorities", None, (401, 200, 200, 200)),
    ("POST", "/priorities", {}, (401, 403, 403, 422)),
    # Usuarios y técnicos: leer personal técnico, escribir solo admin
    ("GET", "/users", None, (401, 403, 200, 200)),
    ("POST", "/users", {}, (401, 403, 403, 422)),
    ("GET", "/technicians", None, (401, 403, 200, 200)),
    ("POST", "/technicians", {}, (401, 403, 403, 422)),
    # Equipos: leer todos, escribir personal técnico
    ("GET", "/computers", None, (401, 200, 200, 200)),
    ("POST", "/computers", {}, (401, 403, 422, 422)),
    # Estadísticas: personal técnico
    ("GET", "/stats", None, (401, 403, 200, 200)),
    # Tickets: todos los autenticados
    ("GET", "/tickets", None, (401, 200, 200, 200)),
]


@pytest.mark.parametrize("method,path,body,expected", CASES)
def test_matriz_de_permisos(client, user1, tech, admin, method, path, body, expected):
    actors = [{}, user1, tech, admin]
    for headers, code in zip(actors, expected):
        r = client.request(method, path, json=body, headers=headers)
        assert r.status_code == code, f"{method} {path} con {headers and 'rol' or 'sin token'}: {r.status_code} != {code}"


def test_usuario_no_puede_crearse_un_admin(client, user1):
    body = {"full_name": "Intruso", "email": "x@test.example", "password": "Secreto1234", "role": "admin"}
    assert client.post("/users", json=body, headers=user1).status_code == 403


def test_tecnico_no_puede_crearse_un_admin(client, tech):
    body = {"full_name": "Intruso", "email": "x@test.example", "password": "Secreto1234", "role": "admin"}
    assert client.post("/users", json=body, headers=tech).status_code == 403
