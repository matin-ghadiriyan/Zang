from collections import defaultdict
from datetime import datetime

from flask import request
from flask_socketio import emit, join_room, leave_room

from app.Access import current_user
from app.extensions import db
from app.models import Chat, ChatMember, Message


_registered = False
_sid_state = {}
_online_by_chat = defaultdict(lambda: defaultdict(int))


def _room(chat_id: int) -> str:
    return f"chat:{chat_id}"


def _member_chat(chat_id: int, user_id: int):
    return (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(Chat.id == chat_id, ChatMember.user_id == user_id)
        .first()
    )


def _is_channel(chat: Chat) -> bool:
    return bool(chat.title and chat.title.startswith('#'))


def _presence_payload(chat_id: int) -> dict:
    users = _online_by_chat.get(chat_id, {})
    return {
        'chat_id': chat_id,
        'online_count': sum(1 for count in users.values() if count > 0),
    }


def _leave_chat(socketio, sid: str, chat_id: int, user_id: int) -> None:
    leave_room(_room(chat_id), sid=sid)

    counts = _online_by_chat.get(chat_id)
    if counts and counts.get(user_id, 0) > 0:
        counts[user_id] -= 1
        if counts[user_id] <= 0:
            counts.pop(user_id, None)
        if not counts:
            _online_by_chat.pop(chat_id, None)

    socketio.emit('presence:update', _presence_payload(chat_id), to=_room(chat_id))


def register_socket_events(socketio) -> None:
    global _registered
    if _registered:
        return
    _registered = True

    def on_connect():
        user = current_user()
        if not user:
            return False

        _sid_state[request.sid] = {
            'user_id': user.id,
            'username': user.username,
            'chats': set(),
        }

        emit('zang:ready', {
            'ok': True,
            'user_id': user.id,
            'username': user.username,
            'version': '0.3.0',
        })

    def on_disconnect():
        state = _sid_state.pop(request.sid, None)
        if not state:
            return

        for chat_id in list(state['chats']):
            _leave_chat(socketio, request.sid, chat_id, state['user_id'])

    def on_join_chat(data):
        user = current_user()
        if not user:
            return {'ok': False, 'error': 'ابتدا وارد حساب شوید.'}

        try:
            chat_id = int((data or {}).get('chat_id'))
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'شناسه گفتگو نامعتبر است.'}

        chat = _member_chat(chat_id, user.id)
        if not chat:
            return {'ok': False, 'error': 'به این گفتگو دسترسی ندارید.'}

        state = _sid_state.setdefault(request.sid, {
            'user_id': user.id,
            'username': user.username,
            'chats': set(),
        })

        if chat_id not in state['chats']:
            join_room(_room(chat_id))
            state['chats'].add(chat_id)
            _online_by_chat[chat_id][user.id] += 1

        socketio.emit('presence:update', _presence_payload(chat_id), to=_room(chat_id))
        return {'ok': True, 'chat_id': chat_id}

    def on_leave_chat(data):
        state = _sid_state.get(request.sid)
        if not state:
            return {'ok': True}

        try:
            chat_id = int((data or {}).get('chat_id'))
        except (TypeError, ValueError):
            return {'ok': False}

        if chat_id in state['chats']:
            state['chats'].remove(chat_id)
            _leave_chat(socketio, request.sid, chat_id, state['user_id'])

        return {'ok': True}

    def on_typing(data):
        user = current_user()
        if not user:
            return

        try:
            chat_id = int((data or {}).get('chat_id'))
        except (TypeError, ValueError):
            return

        if not _member_chat(chat_id, user.id):
            return

        emit('typing:update', {
            'chat_id': chat_id,
            'username': user.username,
            'typing': bool((data or {}).get('typing', True)),
        }, to=_room(chat_id), include_self=False)

    def on_send_message(data):
        user = current_user()
        if not user:
            return {'ok': False, 'error': 'ابتدا وارد حساب شوید.'}

        try:
            chat_id = int((data or {}).get('chat_id'))
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'شناسه گفتگو نامعتبر است.'}

        content = str((data or {}).get('content') or '').strip()
        if not content:
            return {'ok': False, 'error': 'پیام خالی است.'}
        if len(content) > 5000:
            return {'ok': False, 'error': 'پیام بیش از حد طولانی است.'}

        chat = _member_chat(chat_id, user.id)
        if not chat:
            return {'ok': False, 'error': 'به این گفتگو دسترسی ندارید.'}

        if _is_channel(chat) and chat.user_id != user.id:
            return {'ok': False, 'error': 'در کانال فقط مدیر می‌تواند پیام منتشر کند.'}

        message = Message(
            content=content,
            role='user',
            chat_id=chat.id,
            user_id=user.id,
        )
        db.session.add(message)
        chat.updated_at = datetime.utcnow()
        db.session.commit()

        payload = {
            'chat_id': chat.id,
            'message': message.to_dict(),
        }
        socketio.emit('message:new', payload, to=_room(chat.id))
        return {'ok': True, **payload}

    def on_edit_message(data):
        user = current_user()
        if not user:
            return {'ok': False, 'error': 'ابتدا وارد حساب شوید.'}

        try:
            message_id = int((data or {}).get('message_id'))
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'شناسه پیام نامعتبر است.'}

        content = str((data or {}).get('content') or '').strip()
        if not content:
            return {'ok': False, 'error': 'متن پیام نمی‌تواند خالی باشد.'}
        if len(content) > 5000:
            return {'ok': False, 'error': 'پیام بیش از حد طولانی است.'}

        message = Message.query.filter_by(id=message_id).first()
        if not message or message.user_id != user.id:
            return {'ok': False, 'error': 'فقط پیام خودت را می‌توانی ویرایش کنی.'}

        if not _member_chat(message.chat_id, user.id):
            return {'ok': False, 'error': 'به این گفتگو دسترسی ندارید.'}

        message.content = content
        db.session.commit()

        payload = {
            'chat_id': message.chat_id,
            'message': message.to_dict(),
        }
        socketio.emit('message:updated', payload, to=_room(message.chat_id))
        return {'ok': True, **payload}

    def on_delete_message(data):
        user = current_user()
        if not user:
            return {'ok': False, 'error': 'ابتدا وارد حساب شوید.'}

        try:
            message_id = int((data or {}).get('message_id'))
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'شناسه پیام نامعتبر است.'}

        message = Message.query.filter_by(id=message_id).first()
        if not message or message.user_id != user.id:
            return {'ok': False, 'error': 'فقط پیام خودت را می‌توانی حذف کنی.'}

        chat_id = message.chat_id
        if not _member_chat(chat_id, user.id):
            return {'ok': False, 'error': 'به این گفتگو دسترسی ندارید.'}

        db.session.delete(message)
        db.session.commit()

        payload = {'chat_id': chat_id, 'message_id': message_id}
        socketio.emit('message:deleted', payload, to=_room(chat_id))
        return {'ok': True, **payload}

    socketio.on_event('connect', on_connect)
    socketio.on_event('disconnect', on_disconnect)
    socketio.on_event('chat:join', on_join_chat)
    socketio.on_event('chat:leave', on_leave_chat)
    socketio.on_event('typing', on_typing)
    socketio.on_event('message:send', on_send_message)
    socketio.on_event('message:edit', on_edit_message)
    socketio.on_event('message:delete', on_delete_message)
