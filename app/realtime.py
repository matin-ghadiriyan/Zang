import json
import threading
from datetime import datetime

from flask import session

from app.extensions import db, sock
from app.models import ChatMember, User


_lock = threading.RLock()
_connections = {}


def _send(ws, payload: dict) -> bool:
    try:
        ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False


def _connection_snapshot():
    with _lock:
        return list(_connections.values())


def _online_users_for_chat(chat_id: int) -> list[dict]:
    users = {}
    for item in _connection_snapshot():
        if chat_id not in item['rooms']:
            continue
        user = item.get('user')
        if user:
            users[user.id] = {
                'id': user.id,
                'username': user.username
            }
    return list(users.values())


def broadcast_chat(chat_id: int, payload: dict, exclude_connection=None) -> None:
    stale = []
    for item in _connection_snapshot():
        if chat_id not in item['rooms']:
            continue
        ws = item['ws']
        if exclude_connection is not None and ws is exclude_connection:
            continue
        if not _send(ws, payload):
            stale.append(id(ws))

    if stale:
        with _lock:
            for key in stale:
                _connections.pop(key, None)


def broadcast_user(user_id: int, payload: dict) -> None:
    for item in _connection_snapshot():
        user = item.get('user')
        if user and user.id == user_id:
            _send(item['ws'], payload)


def _broadcast_presence(chat_id: int) -> None:
    broadcast_chat(chat_id, {
        'type': 'presence:snapshot',
        'chat_id': chat_id,
        'users': _online_users_for_chat(chat_id)
    })


@sock.route('/ws')
def websocket(ws):
    user_id = session.get('user_id')
    if not session.get('logged_in') or not user_id:
        _send(ws, {'type': 'error', 'message': 'برای اتصال زنده باید وارد حساب شوید.'})
        return

    user = User.query.filter_by(id=user_id).first()
    if not user:
        _send(ws, {'type': 'error', 'message': 'کاربر یافت نشد.'})
        return

    key = id(ws)
    connection = {
        'ws': ws,
        'user': user,
        'rooms': set()
    }

    with _lock:
        _connections[key] = connection

    _send(ws, {
        'type': 'ready',
        'user': {
            'id': user.id,
            'username': user.username
        }
    })

    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break

            try:
                data = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                _send(ws, {'type': 'error', 'message': 'پیام WebSocket نامعتبر بود.'})
                continue

            event_type = data.get('type')

            if event_type == 'ping':
                _send(ws, {'type': 'pong'})
                continue

            chat_id = data.get('chat_id')
            try:
                chat_id = int(chat_id)
            except (TypeError, ValueError):
                chat_id = None

            if event_type == 'join':
                if not chat_id:
                    continue

                membership = ChatMember.query.filter_by(
                    chat_id=chat_id,
                    user_id=user.id
                ).first()

                if not membership:
                    _send(ws, {
                        'type': 'error',
                        'message': 'به این گفتگو دسترسی ندارید.'
                    })
                    continue

                with _lock:
                    connection['rooms'].add(chat_id)

                _send(ws, {'type': 'joined', 'chat_id': chat_id})
                _broadcast_presence(chat_id)
                continue

            if event_type == 'leave':
                if chat_id:
                    with _lock:
                        connection['rooms'].discard(chat_id)
                    _broadcast_presence(chat_id)
                continue

            if event_type == 'typing':
                if chat_id and chat_id in connection['rooms']:
                    broadcast_chat(chat_id, {
                        'type': 'typing',
                        'chat_id': chat_id,
                        'user_id': user.id,
                        'username': user.username,
                        'typing': bool(data.get('typing'))
                    }, exclude_connection=ws)
                continue

            if event_type == 'read':
                if not chat_id or chat_id not in connection['rooms']:
                    continue

                try:
                    message_id = int(data.get('message_id') or 0)
                except (TypeError, ValueError):
                    message_id = 0

                if not message_id:
                    continue

                membership = ChatMember.query.filter_by(
                    chat_id=chat_id,
                    user_id=user.id
                ).first()

                if membership:
                    current = membership.last_read_message_id or 0
                    if message_id > current:
                        membership.last_read_message_id = message_id
                        db.session.commit()

                    broadcast_chat(chat_id, {
                        'type': 'message:read',
                        'chat_id': chat_id,
                        'message_id': membership.last_read_message_id,
                        'user_id': user.id,
                        'username': user.username
                    })
                continue

    except Exception:
        pass
    finally:
        with _lock:
            rooms = set(connection['rooms'])
            _connections.pop(key, None)

        try:
            live_user = User.query.filter_by(id=user.id).first()
            if live_user:
                live_user.last_seen_at = datetime.utcnow()
                db.session.commit()
        except Exception:
            db.session.rollback()

        for chat_id in rooms:
            _broadcast_presence(chat_id)
