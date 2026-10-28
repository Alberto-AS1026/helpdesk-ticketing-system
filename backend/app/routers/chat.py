import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import ChatConversation, ChatMessage, ChatPresence, User
from app.schemas import (
    ChatContact,
    ChatMessageCreate,
    ChatMessageOut,
    ChatRead,
    ChatSync,
    ConversationCreate,
    ConversationOut,
    UnreadOut,
)
from app.realtime import manager, spawn
from app.security import decode_access_token

router = APIRouter(prefix="/chat", tags=["Chat"])
# El WebSocket va aparte: no lleva la dependencia OAuth2 del router (el
# navegador no puede mandar la cabecera Authorization en un WebSocket)
ws_router = APIRouter(prefix="/chat", tags=["Chat"])
security_log = logging.getLogger("helpdesk.security")

# La página de chat consulta cada 3 s y el resto de páginas cada 15 s:
# quien no ha dado señales en 35 s deja de estar "en línea".
ONLINE_WINDOW = timedelta(seconds=35)
# La presencia se escribe como mucho una vez cada 10 s por usuario
PRESENCE_THROTTLE = timedelta(seconds=10)
# El cliente avisa de que escribe cada 3 s; pasados 6 s sin aviso, se apaga
TYPING_WINDOW = timedelta(seconds=6)
# WebSocket: tiempo para autenticarse, silencio máximo (el cliente hace ping
# cada 25 s) y tamaño máximo de lo que manda el cliente
WS_AUTH_TIMEOUT = 10
WS_IDLE_TIMEOUT = 60
WS_MAX_MESSAGE = 4096
# Códigos de cierre propios (rango 4000-4999)
WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_TOO_MANY = 4429


# ---------- Funciones auxiliares ----------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def chat_user(db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> User:
    """Usuario autenticado; de paso registra su actividad para el "en línea"."""
    stmt = insert(ChatPresence).values(user_id=me.id, last_seen_at=func.now())
    db.execute(
        stmt.on_conflict_do_update(
            index_elements=[ChatPresence.user_id],
            set_={"last_seen_at": func.now()},
            where=ChatPresence.last_seen_at < func.now() - PRESENCE_THROTTLE,
        )
    )
    db.commit()
    return me


def can_chat(me: User, other: User) -> bool:
    """Un usuario normal solo habla con el personal técnico; el personal, con cualquiera."""
    if other.id == me.id or not other.is_active:
        return False
    return not (me.role == "user" and other.role == "user")


def my_side(conv: ChatConversation, me: User) -> str:
    return "low" if conv.user_low_id == me.id else "high"


def other_side(conv: ChatConversation, me: User) -> str:
    return "high" if conv.user_low_id == me.id else "low"


def other_of(conv: ChatConversation, me: User) -> User:
    return getattr(conv, "user_" + other_side(conv, me))


def get_conversation(db: Session, conversation_id: int, me: User) -> ChatConversation:
    """Si no participa en la conversación, responde 404 (no confirma que exista)."""
    conv = db.scalars(
        select(ChatConversation)
        .where(ChatConversation.id == conversation_id)
        .options(selectinload(ChatConversation.user_low), selectinload(ChatConversation.user_high))
    ).first()
    if conv is None or me.id not in (conv.user_low_id, conv.user_high_id):
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conv


def contact(user: User) -> ChatContact:
    return ChatContact(id=user.id, full_name=user.full_name, role=user.role)


def last_seen_map(db: Session, user_ids: list[int]) -> dict[int, datetime]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(ChatPresence.user_id, ChatPresence.last_seen_at).where(ChatPresence.user_id.in_(user_ids))
    ).all()
    return dict(rows)


def is_online(user_id: int, last_seen: datetime | None) -> bool:
    """En línea: con un WebSocket abierto o, sin él (plan B por polling), con actividad reciente."""
    if manager.is_online(user_id):
        return True
    if last_seen is None or manager.went_offline_after(user_id, last_seen):
        return False
    return now_utc() - last_seen < ONLINE_WINDOW


def participants(conv: ChatConversation) -> tuple[int, int]:
    return conv.user_low_id, conv.user_high_id


def set_typing(db: Session, conv: ChatConversation, me: User) -> None:
    """Guarda el "escribiendo…" (para el polling) y avisa al otro al instante."""
    setattr(conv, my_side(conv, me) + "_typing_at", now_utc())
    db.commit()
    manager.notify(
        [other_of(conv, me).id],
        {"type": "typing", "conversation_id": conv.id, "user_id": me.id},
    )


def unread_condition(me: User):
    """Mensajes de la otra persona posteriores al último leído por mí."""
    my_read = case(
        (ChatConversation.user_low_id == me.id, ChatConversation.low_last_read_id),
        else_=ChatConversation.high_last_read_id,
    )
    return and_(
        or_(ChatConversation.user_low_id == me.id, ChatConversation.user_high_id == me.id),
        ChatMessage.sender_id != me.id,
        ChatMessage.id > my_read,
    )


def conversation_out(
    conv: ChatConversation,
    me: User,
    last: ChatMessage | None,
    unread: int,
    seen: dict[int, datetime],
) -> ConversationOut:
    other = other_of(conv, me)
    other_read = getattr(conv, other_side(conv, me) + "_last_read_id")
    mine = last is not None and last.sender_id == me.id
    return ConversationOut(
        id=conv.id,
        other=contact(other),
        other_online=is_online(other.id, seen.get(other.id)),
        other_last_seen_at=seen.get(other.id),
        last_message=last.body if last else None,
        last_message_at=last.created_at if last else None,
        last_message_mine=mine,
        last_message_read=mine and other_read >= last.id,
        unread=unread,
    )


# ---------- Contactos y conversaciones ----------

@router.get("/contacts", response_model=list[ChatContact])
def list_contacts(db: Session = Depends(get_db), me: User = Depends(chat_user)):
    query = select(User).where(User.is_active.is_(True), User.id != me.id)
    if me.role == "user":
        query = query.where(User.role != "user")
    return [contact(u) for u in db.scalars(query.order_by(User.full_name)).all()]


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), me: User = Depends(chat_user)):
    convs = db.scalars(
        select(ChatConversation)
        .where(or_(ChatConversation.user_low_id == me.id, ChatConversation.user_high_id == me.id))
        .options(selectinload(ChatConversation.user_low), selectinload(ChatConversation.user_high))
    ).all()
    if not convs:
        return []
    ids = [c.id for c in convs]

    # Último mensaje de cada conversación
    last_ids = select(func.max(ChatMessage.id)).where(
        ChatMessage.conversation_id.in_(ids)
    ).group_by(ChatMessage.conversation_id)
    last = {
        m.conversation_id: m
        for m in db.scalars(select(ChatMessage).where(ChatMessage.id.in_(last_ids))).all()
    }

    # No leídos por conversación
    unread = dict(
        db.execute(
            select(ChatMessage.conversation_id, func.count(ChatMessage.id))
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(unread_condition(me))
            .group_by(ChatMessage.conversation_id)
        ).all()
    )

    seen = last_seen_map(db, [other_of(c, me).id for c in convs])
    result = [conversation_out(c, me, last.get(c.id), unread.get(c.id, 0), seen) for c in convs]
    # Las conversaciones con actividad más reciente, primero
    result.sort(key=lambda c: (c.last_message_at is not None, c.last_message_at), reverse=True)
    return result


@router.post("/conversations", response_model=ConversationOut)
def open_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    me: User = Depends(chat_user),
):
    """Devuelve la conversación con ese usuario, creándola si no existe."""
    other = db.get(User, data.user_id)
    if other is None or not can_chat(me, other):
        raise HTTPException(status_code=422, detail="No puedes abrir un chat con ese usuario")

    low, high = sorted((me.id, other.id))
    query = select(ChatConversation).where(
        ChatConversation.user_low_id == low, ChatConversation.user_high_id == high
    )
    if db.scalars(query).first() is None:
        db.add(ChatConversation(user_low_id=low, user_high_id=high))
        try:
            db.commit()
        except IntegrityError:
            # Otra petición la creó a la vez: se usa esa
            db.rollback()
    conv = get_conversation(db, db.scalars(query).one().id, me)
    last = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.id.desc())
        .limit(1)
    ).first()
    return conversation_out(conv, me, last, 0, last_seen_map(db, [other.id]))


@router.get("/unread", response_model=UnreadOut)
def total_unread(db: Session = Depends(get_db), me: User = Depends(chat_user)):
    count = db.scalar(
        select(func.count(ChatMessage.id))
        .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
        .where(unread_condition(me))
    )
    return UnreadOut(unread=count or 0)


# ---------- Mensajes ----------

def fetch_messages(db: Session, conversation_id: int, after_id: int, limit: int) -> list[ChatMessage]:
    """Sin after_id: los últimos mensajes. Con after_id: solo los nuevos."""
    query = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
    if after_id:
        return list(db.scalars(query.where(ChatMessage.id > after_id).order_by(ChatMessage.id).limit(limit)))
    latest = db.scalars(query.order_by(ChatMessage.id.desc()).limit(limit)).all()
    return list(reversed(latest))


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageOut])
def list_messages(
    conversation_id: int,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    me: User = Depends(chat_user),
):
    get_conversation(db, conversation_id, me)
    return fetch_messages(db, conversation_id, after_id, limit)


@router.get("/conversations/{conversation_id}/sync", response_model=ChatSync)
def sync_conversation(
    conversation_id: int,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    me: User = Depends(chat_user),
):
    """Una sola llamada por ciclo: mensajes nuevos, lectura, presencia y "escribiendo…"."""
    conv = get_conversation(db, conversation_id, me)
    other = other_of(conv, me)
    side = other_side(conv, me)
    typing_at = getattr(conv, side + "_typing_at")
    last_seen = last_seen_map(db, [other.id]).get(other.id)
    return ChatSync(
        messages=fetch_messages(db, conversation_id, after_id, limit),
        other_last_read_id=getattr(conv, side + "_last_read_id"),
        other_online=is_online(other.id, last_seen),
        other_last_seen_at=last_seen,
        other_typing=typing_at is not None and now_utc() - typing_at < TYPING_WINDOW,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    me: User = Depends(chat_user),
):
    conv = get_conversation(db, conversation_id, me)
    if not can_chat(me, other_of(conv, me)):
        raise HTTPException(status_code=409, detail="Ya no puedes escribir en esta conversación")
    body = data.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="El mensaje está vacío")
    message = ChatMessage(conversation_id=conv.id, sender_id=me.id, body=body)
    db.add(message)
    db.flush()
    side = my_side(conv, me)
    # Lo que uno mismo escribe cuenta como leído, y deja de estar "escribiendo"
    setattr(conv, side + "_last_read_id", message.id)
    setattr(conv, side + "_typing_at", None)
    db.commit()
    db.refresh(message)
    out = ChatMessageOut.model_validate(message)
    # A los dos: el destinatario y las otras pestañas de quien lo envía
    manager.notify(
        participants(conv),
        {"type": "message", "conversation_id": conv.id, "message": out.model_dump(mode="json")},
    )
    return out


@router.post("/conversations/{conversation_id}/typing", status_code=status.HTTP_204_NO_CONTENT)
def mark_typing(
    conversation_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(chat_user),
):
    set_typing(db, get_conversation(db, conversation_id, me), me)


@router.post("/conversations/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    conversation_id: int,
    data: ChatRead,
    db: Session = Depends(get_db),
    me: User = Depends(chat_user),
):
    conv = get_conversation(db, conversation_id, me)
    newest = db.scalar(
        select(func.max(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
    ) or 0
    field = my_side(conv, me) + "_last_read_id"
    # Nunca retrocede ni avanza más allá del último mensaje existente
    value = max(getattr(conv, field), min(data.last_read_id, newest))
    setattr(conv, field, value)
    db.commit()
    # El otro ve el doble check azul; mis otras pestañas actualizan el contador
    manager.notify(
        participants(conv),
        {"type": "read", "conversation_id": conv.id, "user_id": me.id, "last_read_id": value},
    )


# ---------- WebSocket: avisos en tiempo real ----------
#
# Protocolo (JSON):
#   cliente -> {"type": "auth", "token": "<JWT>"}       primer mensaje, en menos de 10 s
#   cliente -> {"type": "ping"}                          cada 25 s; responde {"type": "pong"}
#   cliente -> {"type": "typing", "conversation_id": N}
#   servidor -> ready | message | read | typing | presence
#
# El token va en el primer mensaje y no en la URL para que no quede en los
# logs de Nginx. Como no se usan cookies, otra web no puede abrir un socket
# en nombre del usuario sin conocer su token.

def ws_authenticate(token: str) -> tuple[User, datetime] | None:
    """Usuario del token y su caducidad, o None si no es válido."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        expires = datetime.fromtimestamp(payload["exp"], timezone.utc)
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        db.expunge(user)
        return user, expires


def ws_peers(user_id: int) -> list[int]:
    """Usuarios con los que tiene conversación: son quienes ven su presencia."""
    with SessionLocal() as db:
        rows = db.execute(
            select(ChatConversation.user_low_id, ChatConversation.user_high_id).where(
                or_(ChatConversation.user_low_id == user_id, ChatConversation.user_high_id == user_id)
            )
        ).all()
    return [low if high == user_id else high for low, high in rows]


def ws_touch_presence(user_id: int) -> datetime:
    with SessionLocal() as db:
        stmt = insert(ChatPresence).values(user_id=user_id, last_seen_at=func.now())
        db.execute(
            stmt.on_conflict_do_update(index_elements=[ChatPresence.user_id], set_={"last_seen_at": func.now()})
        )
        db.commit()
        return db.scalar(select(ChatPresence.last_seen_at).where(ChatPresence.user_id == user_id))


def ws_typing(user: User, conversation_id: int) -> None:
    with SessionLocal() as db:
        me = db.get(User, user.id)
        try:
            conv = get_conversation(db, conversation_id, me)
        except HTTPException:
            return  # no participa: se ignora sin dar pistas
        set_typing(db, conv, me)


async def ws_broadcast_presence(user_id: int, online: bool) -> None:
    last_seen = await run_in_threadpool(ws_touch_presence, user_id)
    if not online and last_seen:
        manager.mark_offline(user_id, last_seen)
    peers = await run_in_threadpool(ws_peers, user_id)
    manager.notify(
        peers,
        {
            "type": "presence",
            "user_id": user_id,
            "online": online,
            "last_seen_at": last_seen.isoformat() if last_seen else None,
        },
    )


@ws_router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    ip = ws.client.host if ws.client else "desconocida"

    # 1. Autenticación con el primer mensaje
    try:
        first = await asyncio.wait_for(ws.receive_text(), WS_AUTH_TIMEOUT)
        data = json.loads(first) if len(first) <= WS_MAX_MESSAGE else {}
        token = data.get("token") if data.get("type") == "auth" else None
    except WebSocketDisconnect:
        return
    except (asyncio.TimeoutError, ValueError, AttributeError):
        token = None
    auth = await run_in_threadpool(ws_authenticate, token) if isinstance(token, str) else None
    if auth is None:
        security_log.warning("WebSocket rechazado: token no válido ip=%s", ip)
        await ws.close(code=WS_CLOSE_UNAUTHORIZED)
        return
    user, expires = auth

    if not manager.connect(user.id, ws):
        await ws.close(code=WS_CLOSE_TOO_MANY)
        return
    try:
        await ws.send_json({"type": "ready", "user_id": user.id})
        await ws_broadcast_presence(user.id, online=True)

        # 2. Bucle: pings y "escribiendo…"
        while True:
            raw = await asyncio.wait_for(ws.receive_text(), WS_IDLE_TIMEOUT)
            if now_utc() >= expires:
                await ws.close(code=WS_CLOSE_UNAUTHORIZED)  # el JWT ha caducado
                break
            if len(raw) > WS_MAX_MESSAGE:
                continue
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
            elif msg.get("type") == "typing" and isinstance(msg.get("conversation_id"), int):
                await run_in_threadpool(ws_typing, user, msg["conversation_id"])
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass
    finally:
        # Al cerrar, la tarea del socket puede estar cancelándose: el aviso de
        # desconexión va en una tarea aparte para que llegue igualmente
        if manager.disconnect(user.id, ws):
            spawn(ws_broadcast_presence(user.id, online=False))
