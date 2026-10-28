"""WebSocket del chat: autenticación y avisos en tiempo real.

Usuarios del conftest: 1 admin, 2 técnico, 3 usuario uno, 4 usuario dos.
Para comprobar que NO llega un aviso se manda un ping: si lo siguiente que
llega es el pong, no había nada pendiente.
"""
import time

import pytest
from starlette.websockets import WebSocketDisconnect

from app.realtime import manager


def token(headers):
    return headers["Authorization"].split(" ", 1)[1]


def connect(client, headers):
    ws = client.websocket_connect("/chat/ws")
    sock = ws.__enter__()
    sock.send_json({"type": "auth", "token": token(headers)})
    assert sock.receive_json()["type"] == "ready"
    return ws, sock


def next_event(sock, skip=("presence",)):
    """Siguiente aviso, ignorando los de presencia salvo que se pidan."""
    while True:
        event = sock.receive_json()
        if event["type"] not in skip:
            return event


def assert_nothing_pending(sock):
    sock.send_json({"type": "ping"})
    assert next_event(sock) == {"type": "pong"}


def open_chat(client, headers, user_id):
    return client.post("/chat/conversations", json={"user_id": user_id}, headers=headers).json()["id"]


@pytest.mark.parametrize("first", [
    {"type": "auth", "token": "no-es-un-jwt"},
    {"type": "hola"},
    {"token": None},
])
def test_ws_rechaza_sin_token_valido(client, first):
    with client.websocket_connect("/chat/ws") as sock:
        sock.send_json(first)
        with pytest.raises(WebSocketDisconnect) as exc:
            sock.receive_json()
    assert exc.value.code == 4401


def test_ws_rechaza_usuario_desactivado(client, admin, user1):
    client.patch("/users/3", json={"is_active": False}, headers=admin)
    with client.websocket_connect("/chat/ws") as sock:
        sock.send_json({"type": "auth", "token": token(user1)})
        with pytest.raises(WebSocketDisconnect) as exc:
            sock.receive_json()
    assert exc.value.code == 4401


def test_ws_ping_pong_y_desconexion(client, user1):
    ws, sock = connect(client, user1)
    assert_nothing_pending(sock)
    assert manager.is_online(3)
    ws.__exit__(None, None, None)
    # El servidor procesa el cierre de forma asíncrona
    deadline = time.monotonic() + 2
    while manager.is_online(3) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not manager.is_online(3)


def test_mensaje_llega_al_instante_al_destinatario(client, user1, tech):
    conv = open_chat(client, tech, 3)
    ws, sock = connect(client, user1)
    try:
        r = client.post(f"/chat/conversations/{conv}/messages", json={"body": "¿Me oyes?"}, headers=tech)
        event = next_event(sock)
        assert event["type"] == "message"
        assert event["conversation_id"] == conv
        assert event["message"]["body"] == "¿Me oyes?"
        assert event["message"]["id"] == r.json()["id"]
    finally:
        ws.__exit__(None, None, None)


def test_leido_avisa_al_remitente(client, user1, tech):
    conv = open_chat(client, tech, 3)
    msg = client.post(f"/chat/conversations/{conv}/messages", json={"body": "hola"}, headers=tech).json()
    ws, sock = connect(client, tech)
    try:
        client.post(f"/chat/conversations/{conv}/read", json={"last_read_id": msg["id"]}, headers=user1)
        event = next_event(sock)
        assert event == {"type": "read", "conversation_id": conv, "user_id": 3, "last_read_id": msg["id"]}
    finally:
        ws.__exit__(None, None, None)


def test_escribiendo_por_websocket(client, user1, tech):
    conv = open_chat(client, tech, 3)
    ws1, sock1 = connect(client, user1)
    ws2, sock2 = connect(client, tech)
    try:
        sock2.send_json({"type": "typing", "conversation_id": conv})
        assert next_event(sock1) == {"type": "typing", "conversation_id": conv, "user_id": 2}
        # También queda guardado para quien use el plan B por polling
        sync = client.get(f"/chat/conversations/{conv}/sync", headers=user1).json()
        assert sync["other_typing"] is True
    finally:
        ws1.__exit__(None, None, None)
        ws2.__exit__(None, None, None)


def test_presencia_en_tiempo_real(client, user1, tech):
    conv = open_chat(client, tech, 3)
    ws_t, sock_t = connect(client, tech)
    try:
        ws_u, _ = connect(client, user1)
        event = next_event(sock_t, skip=())
        assert event["type"] == "presence" and event["user_id"] == 3 and event["online"] is True
        assert client.get(f"/chat/conversations/{conv}/sync", headers=tech).json()["other_online"] is True

        ws_u.__exit__(None, None, None)
        event = next_event(sock_t, skip=())
        assert event["type"] == "presence" and event["online"] is False and event["last_seen_at"]
        # El REST coincide con el aviso (no sigue "en línea" por la ventana del polling)
        sync = client.get(f"/chat/conversations/{conv}/sync", headers=tech).json()
        assert sync["other_online"] is False
        assert client.get("/chat/conversations", headers=tech).json()[0]["other_online"] is False
    finally:
        ws_t.__exit__(None, None, None)


def test_un_tercero_no_recibe_nada(client, user1, user2, tech):
    conv = open_chat(client, tech, 3)
    ws, sock = connect(client, user2)
    try:
        client.post(f"/chat/conversations/{conv}/messages", json={"body": "privado"}, headers=tech)
        # typing a una conversación ajena: se ignora
        sock.send_json({"type": "typing", "conversation_id": conv})
        assert_nothing_pending(sock)
    finally:
        ws.__exit__(None, None, None)
