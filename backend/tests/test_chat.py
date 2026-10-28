"""Chat 1 a 1: quién puede hablar con quién, mensajes, polling y no leídos.

Usuarios del conftest: 1 admin, 2 técnico, 3 usuario uno, 4 usuario dos.
"""
import pytest


def open_chat(client, headers, user_id):
    return client.post("/chat/conversations", json={"user_id": user_id}, headers=headers)


def send(client, headers, conv_id, body):
    return client.post(f"/chat/conversations/{conv_id}/messages", json={"body": body}, headers=headers)


def unread(client, headers):
    r = client.get("/chat/unread", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["unread"]


def test_chat_requiere_login(client):
    assert client.get("/chat/conversations").status_code == 401


def test_usuario_solo_ve_contactos_del_personal(client, user1):
    r = client.get("/chat/contacts", headers=user1)
    assert r.status_code == 200
    roles = {c["role"] for c in r.json()}
    assert roles == {"admin", "technician"}
    assert all("email" not in c for c in r.json())


def test_personal_ve_a_todos_menos_a_si_mismo(client, tech):
    ids = {c["id"] for c in client.get("/chat/contacts", headers=tech).json()}
    assert ids == {1, 3, 4}


@pytest.mark.parametrize("target", [3, 4, 999])
def test_usuario_no_puede_abrir_chat_con_otro_usuario_ni_consigo(client, user1, target):
    assert open_chat(client, user1, target).status_code == 422


def test_abrir_chat_es_idempotente_y_simetrico(client, user1, tech):
    a = open_chat(client, user1, 2)
    b = open_chat(client, tech, 3)
    assert a.status_code == b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    assert a.json()["other"]["full_name"] == "Tecnico Uno"
    assert b.json()["other"]["full_name"] == "Usuario Uno"


def test_conversacion_completa_con_no_leidos(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]

    assert send(client, tech, conv, "¿Puedes reiniciar el equipo?").status_code == 201
    assert send(client, tech, conv, "Avísame cuando vuelva a arrancar").status_code == 201
    assert unread(client, user1) == 2
    assert unread(client, tech) == 0  # lo propio cuenta como leído

    listed = client.get("/chat/conversations", headers=user1).json()
    assert listed[0]["unread"] == 2
    assert listed[0]["last_message"] == "Avísame cuando vuelva a arrancar"

    msgs = client.get(f"/chat/conversations/{conv}/messages", headers=user1).json()
    assert [m["body"] for m in msgs] == ["¿Puedes reiniciar el equipo?", "Avísame cuando vuelva a arrancar"]

    r = client.post(f"/chat/conversations/{conv}/read", json={"last_read_id": msgs[-1]["id"]}, headers=user1)
    assert r.status_code == 204
    assert unread(client, user1) == 0

    reply = send(client, user1, conv, "Ya está, funciona").json()
    assert reply["sender_id"] == 3
    assert unread(client, tech) == 1


def test_polling_devuelve_solo_mensajes_nuevos(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    first = send(client, tech, conv, "uno").json()
    send(client, tech, conv, "dos")
    send(client, tech, conv, "tres")
    r = client.get(f"/chat/conversations/{conv}/messages?after_id={first['id']}", headers=user1)
    assert [m["body"] for m in r.json()] == ["dos", "tres"]


def test_marcar_leido_no_retrocede_ni_se_pasa(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    msg = send(client, tech, conv, "hola").json()
    client.post(f"/chat/conversations/{conv}/read", json={"last_read_id": 10_000}, headers=user1)
    send(client, tech, conv, "¿sigues ahí?")
    assert unread(client, user1) == 1  # el 10 000 se recortó al último existente
    client.post(f"/chat/conversations/{conv}/read", json={"last_read_id": msg["id"]}, headers=user1)
    assert unread(client, user1) == 1  # no retrocede


def test_un_tercero_no_puede_leer_ni_escribir(client, user1, user2, tech, admin):
    conv = open_chat(client, tech, 3).json()["id"]
    send(client, tech, conv, "privado")
    for headers in (user2, admin):
        assert client.get(f"/chat/conversations/{conv}/messages", headers=headers).status_code == 404
        assert send(client, headers, conv, "intruso").status_code == 404
        r = client.post(f"/chat/conversations/{conv}/read", json={"last_read_id": 1}, headers=headers)
        assert r.status_code == 404
    assert client.get("/chat/conversations", headers=user2).json() == []


@pytest.mark.parametrize("body", ["", "   ", "x" * 2001])
def test_mensaje_invalido(client, tech, body):
    conv = open_chat(client, tech, 3).json()["id"]
    assert send(client, tech, conv, body).status_code == 422


def test_no_se_escribe_a_un_usuario_desactivado(client, admin, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    send(client, tech, conv, "antes de la baja")
    assert client.patch("/users/3", json={"is_active": False}, headers=admin).status_code == 200
    assert send(client, tech, conv, "después").status_code == 409
    # El historial se sigue pudiendo leer
    assert len(client.get(f"/chat/conversations/{conv}/messages", headers=tech).json()) == 1
    assert 3 not in {c["id"] for c in client.get("/chat/contacts", headers=tech).json()}


def test_ticket_incluye_usuario_del_tecnico(client, user1, tech):
    t = client.post(
        "/tickets",
        json={"title": "Sin red", "description": "No hay conexión", "priority_id": 1, "category_id": 1},
        headers=user1,
    ).json()
    assert t["technician_user_id"] is None
    client.patch(f"/tickets/{t['id']}/assign", json={"technician_id": 1}, headers=tech)
    assert client.get(f"/tickets/{t['id']}", headers=user1).json()["technician_user_id"] == 2


# ---------- Estilo mensajería: lectura, "escribiendo…" y presencia ----------

def sync(client, headers, conv_id, after_id=0):
    r = client.get(f"/chat/conversations/{conv_id}/sync?after_id={after_id}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_doble_check_cuando_el_otro_lee(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    msg = send(client, tech, conv, "¿Me lees?").json()

    assert sync(client, tech, conv)["other_last_read_id"] < msg["id"]
    listed = client.get("/chat/conversations", headers=tech).json()[0]
    assert listed["last_message_mine"] is True and listed["last_message_read"] is False

    client.post(f"/chat/conversations/{conv}/read", json={"last_read_id": msg["id"]}, headers=user1)

    assert sync(client, tech, conv)["other_last_read_id"] == msg["id"]
    assert client.get("/chat/conversations", headers=tech).json()[0]["last_message_read"] is True


def test_escribiendo_se_ve_y_se_apaga_al_enviar(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    assert sync(client, user1, conv)["other_typing"] is False

    assert client.post(f"/chat/conversations/{conv}/typing", headers=tech).status_code == 204
    assert sync(client, user1, conv)["other_typing"] is True
    assert sync(client, tech, conv)["other_typing"] is False  # uno no se ve a sí mismo

    send(client, tech, conv, "listo")
    assert sync(client, user1, conv)["other_typing"] is False


def test_presencia_en_linea(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    # user1 no ha usado el chat todavía
    state = sync(client, tech, conv)
    assert state["other_online"] is False and state["other_last_seen_at"] is None

    unread(client, user1)  # cualquier llamada al chat cuenta como actividad
    state = sync(client, tech, conv)
    assert state["other_online"] is True and state["other_last_seen_at"] is not None
    assert client.get("/chat/conversations", headers=tech).json()[0]["other_online"] is True


def test_sync_devuelve_solo_lo_nuevo(client, user1, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    first = send(client, tech, conv, "uno").json()
    send(client, tech, conv, "dos")
    assert [m["body"] for m in sync(client, user1, conv)["messages"]] == ["uno", "dos"]
    assert [m["body"] for m in sync(client, user1, conv, first["id"])["messages"]] == ["dos"]


def test_sync_y_typing_de_terceros_dan_404(client, user2, tech):
    conv = open_chat(client, tech, 3).json()["id"]
    assert client.get(f"/chat/conversations/{conv}/sync", headers=user2).status_code == 404
    assert client.post(f"/chat/conversations/{conv}/typing", headers=user2).status_code == 404
