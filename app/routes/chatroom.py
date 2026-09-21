import secrets
from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from app.Access import current_user, is_logged_in
from app.extensions import db
from app.models import Chat, ChatMember, Message, User
from app.realtime import broadcast_chat, broadcast_user


chat_room = Blueprint('chat_room', __name__, url_prefix='/chat')

MAX_CODE_LEN = 64
MAX_CODES = 10


# ===================== Helpers =====================

def _parse_codes(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = raw.replace('،', ',').split(',')
    elif isinstance(raw, (list, tuple)):
        parts = []
        for item in raw:
            if isinstance(item, str) and ',' in item:
                parts.extend(item.replace('،', ',').split(','))
            else:
                parts.append(item)
    else:
        return []

    codes = []
    seen = set()
    for part in parts:
        code = str(part or '').strip()
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def _new_unique_code(prefix: str = 'zang') -> str:
    while True:
        code = f'{prefix}-{secrets.token_urlsafe(6)}'
        if not ChatMember.query.filter_by(access_code=code).first():
            return code


def _chat_kind(chat: Chat) -> str:
    if chat.kind:
        return chat.kind
    if chat.title and chat.title.startswith('#'):
        return 'channel'
    return 'group'


def _is_channel(chat: Chat) -> bool:
    return _chat_kind(chat) == 'channel'


def _user_chat(chat_id: int, user_id: int):
    return (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(Chat.id == chat_id, ChatMember.user_id == user_id)
        .first()
    )


def _user_chats(user_id: int):
    return (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(ChatMember.user_id == user_id)
        .order_by(Chat.updated_at.desc())
        .all()
    )


def _direct_title(chat: Chat, user_id: int) -> str:
    other = (
        ChatMember.query
        .filter(ChatMember.chat_id == chat.id, ChatMember.user_id != user_id)
        .first()
    )
    if other and other.member_user:
        return other.member_user.username
    return chat.title


def _chat_payload(
    chat: Chat,
    user_id: int,
    include_messages: bool = False,
    include_members: bool = False
) -> dict:
    data = chat.to_dict(
        include_messages=include_messages,
        include_members=include_members
    )
    kind = _chat_kind(chat)
    membership = ChatMember.query.filter_by(
        chat_id=chat.id,
        user_id=user_id
    ).first()
    is_owner = chat.user_id == user_id
    last_read = (membership.last_read_message_id or 0) if membership else 0

    unread_count = Message.query.filter(
        Message.chat_id == chat.id,
        Message.id > last_read,
        Message.user_id != user_id,
        Message.is_deleted.is_(False)
    ).count()

    data.update({
        'kind': kind,
        'title': _direct_title(chat, user_id) if kind == 'direct' else chat.title.lstrip('#'),
        'is_owner': is_owner,
        'is_admin': bool(membership and (membership.is_admin or membership.is_owner)),
        'can_post': (kind != 'channel') or is_owner or bool(membership and membership.is_admin),
        'unread_count': unread_count,
        'last_read_message_id': last_read
    })

    if membership and (is_owner or membership.is_admin):
        data['invite_code'] = membership.access_code

    if kind == 'direct':
        other = (
            ChatMember.query
            .filter(ChatMember.chat_id == chat.id, ChatMember.user_id != user_id)
            .first()
        )
        if other and other.member_user:
            data['peer'] = {
                'id': other.member_user.id,
                'username': other.member_user.username,
                'last_seen_at': (
                    other.member_user.last_seen_at.isoformat()
                    if other.member_user.last_seen_at else None
                )
            }

    return data


def _notify_chat_list(chat: Chat) -> None:
    for member in chat.members.all():
        broadcast_user(member.user_id, {
            'type': 'chat:list:update',
            'chat_id': chat.id
        })


# ===================== Chat Page =====================

@chat_room.route('/')
@is_logged_in
def chatroom():
    user = current_user()
    chats = _user_chats(user.id)
    return render_template(
        'chatroom/chatroom.html',
        user=user,
        chats=[_chat_payload(chat, user.id) for chat in chats]
    )


# ===================== Users / Direct Messages =====================

@chat_room.route('/api/users', methods=['GET'])
@is_logged_in
def search_users():
    user = current_user()
    query = (request.args.get('q') or '').strip()

    if len(query) < 2:
        return jsonify({'success': True, 'users': []})

    users = (
        User.query
        .filter(
            User.id != user.id,
            User.username.ilike(f'%{query[:50]}%')
        )
        .order_by(User.username.asc())
        .limit(20)
        .all()
    )

    return jsonify({
        'success': True,
        'users': [
            {
                'id': item.id,
                'username': item.username,
                'last_seen_at': item.last_seen_at.isoformat() if item.last_seen_at else None
            }
            for item in users
        ]
    })


@chat_room.route('/api/direct/<int:other_user_id>', methods=['POST'])
@is_logged_in
def start_direct_chat(other_user_id: int):
    user = current_user()

    if user.id == other_user_id:
        return jsonify({'success': False, 'error': 'نمی‌توانی با خودت گفتگوی مستقیم بسازی.'}), 400

    other = User.query.filter_by(id=other_user_id).first()
    if not other:
        return jsonify({'success': False, 'error': 'کاربر پیدا نشد.'}), 404

    candidates = (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(Chat.kind == 'direct', ChatMember.user_id == user.id)
        .all()
    )

    for chat in candidates:
        member_ids = {member.user_id for member in chat.members.all()}
        if member_ids == {user.id, other.id}:
            return jsonify({
                'success': True,
                'chat': _chat_payload(chat, user.id),
                'created': False
            })

    chat = Chat(
        title=f'{user.username} ↔ {other.username}',
        kind='direct',
        user_id=user.id
    )
    db.session.add(chat)
    db.session.flush()

    db.session.add_all([
        ChatMember(
            chat_id=chat.id,
            user_id=user.id,
            access_code=_new_unique_code('dm'),
            is_owner=True,
            is_admin=True
        ),
        ChatMember(
            chat_id=chat.id,
            user_id=other.id,
            access_code=_new_unique_code('dm'),
            is_owner=False,
            is_admin=False
        )
    ])
    db.session.commit()

    _notify_chat_list(chat)

    return jsonify({
        'success': True,
        'chat': _chat_payload(chat, user.id),
        'created': True
    }), 201


# ===================== List Chats =====================

@chat_room.route('/api/chats', methods=['GET'])
@is_logged_in
def list_chats():
    user = current_user()
    chats = _user_chats(user.id)
    return jsonify({
        'success': True,
        'chats': [_chat_payload(chat, user.id) for chat in chats]
    })


# ===================== Create Group =====================

@chat_room.route('/api/chats', methods=['POST'])
@is_logged_in
def create_chat():
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip() or 'گروه جدید'
    codes = _parse_codes(data.get('codes'))

    if len(title) > 120:
        return jsonify({'success': False, 'error': 'عنوان بیش از حد طولانی است.'}), 400

    if not codes:
        codes = [_new_unique_code('group')]

    if len(codes) > MAX_CODES:
        return jsonify({'success': False, 'error': f'حداکثر {MAX_CODES} شناسه مجاز است.'}), 400

    for code in codes:
        if len(code) > MAX_CODE_LEN:
            return jsonify({'success': False, 'error': 'شناسه بیش از حد طولانی است.'}), 400
        if ChatMember.query.filter_by(access_code=code).first():
            return jsonify({'success': False, 'error': f'شناسه «{code}» قبلاً استفاده شده است.'}), 409

    chat = Chat(
        title=title.lstrip('#'),
        kind='group',
        user_id=user.id
    )
    db.session.add(chat)
    db.session.flush()

    db.session.add(ChatMember(
        chat_id=chat.id,
        user_id=user.id,
        access_code=codes[0],
        is_owner=True,
        is_admin=True
    ))
    db.session.commit()

    return jsonify({
        'success': True,
        'chat': _chat_payload(chat, user.id),
        'codes': codes,
        'invite_code': codes[0]
    }), 201


# ===================== Create Channel =====================

@chat_room.route('/api/channels', methods=['POST'])
@is_logged_in
def create_channel():
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip().lstrip('#').strip()
    description = (data.get('description') or '').strip()[:280]
    requested_code = (data.get('code') or '').strip()

    if len(title) < 2 or len(title) > 60:
        return jsonify({'success': False, 'error': 'نام کانال باید بین ۲ تا ۶۰ کاراکتر باشد.'}), 400

    code = requested_code or _new_unique_code('channel')
    if len(code) > MAX_CODE_LEN:
        return jsonify({'success': False, 'error': 'کد عضویت بیش از حد طولانی است.'}), 400
    if ChatMember.query.filter_by(access_code=code).first():
        return jsonify({'success': False, 'error': 'این کد عضویت قبلاً استفاده شده است.'}), 409

    channel = Chat(
        title=title,
        kind='channel',
        description=description or None,
        user_id=user.id
    )
    db.session.add(channel)
    db.session.flush()

    db.session.add(ChatMember(
        chat_id=channel.id,
        user_id=user.id,
        access_code=code,
        is_owner=True,
        is_admin=True
    ))
    db.session.commit()

    return jsonify({
        'success': True,
        'chat': _chat_payload(channel, user.id),
        'invite_code': code
    }), 201


# ===================== Join Group / Channel =====================

@chat_room.route('/api/chats/join', methods=['POST'])
@is_logged_in
def join_chat():
    user = current_user()
    data = request.get_json(silent=True) or {}
    codes = _parse_codes(data.get('codes') or data.get('code'))

    if not codes:
        return jsonify({'success': False, 'error': 'شناسه را وارد کنید.'}), 400

    joined = []
    joined_ids = set()

    for code in codes:
        if len(code) > MAX_CODE_LEN:
            continue

        source_member = ChatMember.query.filter_by(access_code=code).first()
        if not source_member:
            continue

        chat = Chat.query.filter_by(id=source_member.chat_id).first()
        if not chat or chat.id in joined_ids or _chat_kind(chat) == 'direct':
            continue

        exists = ChatMember.query.filter_by(chat_id=chat.id, user_id=user.id).first()
        if not exists:
            db.session.add(ChatMember(
                chat_id=chat.id,
                user_id=user.id,
                access_code=code,
                is_owner=False,
                is_admin=False
            ))

        joined_ids.add(chat.id)
        joined.append(chat)

    if not joined:
        return jsonify({'success': False, 'error': 'گروه یا کانالی با این شناسه پیدا نشد.'}), 404

    db.session.commit()

    for chat in joined:
        _notify_chat_list(chat)

    return jsonify({
        'success': True,
        'chats': [_chat_payload(chat, user.id) for chat in joined]
    })


# ===================== Get Chat =====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['GET'])
@is_logged_in
def get_chat(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    return jsonify({
        'success': True,
        'chat': _chat_payload(
            chat,
            user.id,
            include_messages=True,
            include_members=True
        )
    })


# ===================== Rename / Description =====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['PATCH'])
@is_logged_in
def rename_chat(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    membership = ChatMember.query.filter_by(chat_id=chat.id, user_id=user.id).first()
    if _chat_kind(chat) in {'group', 'channel'} and not (
        chat.user_id == user.id or (membership and membership.is_admin)
    ):
        return jsonify({'success': False, 'error': 'فقط مدیر می‌تواند این بخش را تغییر دهد.'}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    description = data.get('description')

    if title:
        if len(title) > 120:
            return jsonify({'success': False, 'error': 'عنوان نامعتبر است.'}), 400
        chat.title = title.lstrip('#').strip()

    if description is not None:
        chat.description = str(description).strip()[:280] or None

    db.session.commit()
    payload = _chat_payload(chat, user.id)
    broadcast_chat(chat.id, {'type': 'chat:updated', 'chat': payload})
    _notify_chat_list(chat)

    return jsonify({'success': True, 'chat': payload})


# ===================== Leave / Delete Chat =====================

@chat_room.route('/api/chats/<int:chat_id>/leave', methods=['POST'])
@is_logged_in
def leave_chat(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)
    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    if chat.user_id == user.id:
        return jsonify({
            'success': False,
            'error': 'سازنده ابتدا باید گفتگو را حذف کند یا مالکیت را منتقل کند.'
        }), 400

    member = ChatMember.query.filter_by(chat_id=chat.id, user_id=user.id).first()
    if member:
        db.session.delete(member)
        db.session.commit()

    _notify_chat_list(chat)
    return jsonify({'success': True})


@chat_room.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@is_logged_in
def delete_chat(chat_id: int):
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({'success': False, 'error': 'اجازه حذف این گفتگو را ندارید.'}), 404

    member_ids = [member.user_id for member in chat.members.all()]
    db.session.delete(chat)
    db.session.commit()

    for member_id in member_ids:
        broadcast_user(member_id, {'type': 'chat:deleted', 'chat_id': chat_id})

    return jsonify({'success': True})


# ===================== Send / Read Messages =====================

@chat_room.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@is_logged_in
def send_message(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    membership = ChatMember.query.filter_by(chat_id=chat.id, user_id=user.id).first()
    if _is_channel(chat) and not (
        chat.user_id == user.id or (membership and membership.is_admin)
    ):
        return jsonify({'success': False, 'error': 'در کانال فقط مدیر می‌تواند پیام ارسال کند.'}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({'success': False, 'error': 'متن پیام خالی است.'}), 400
    if len(content) > 5000:
        return jsonify({'success': False, 'error': 'متن پیام بیش از حد طولانی است.'}), 400

    reply_to_id = data.get('reply_to_id')
    reply_message = None
    if reply_to_id:
        try:
            reply_to_id = int(reply_to_id)
        except (TypeError, ValueError):
            reply_to_id = None

        if reply_to_id:
            reply_message = Message.query.filter_by(
                id=reply_to_id,
                chat_id=chat.id
            ).first()
            if not reply_message:
                return jsonify({'success': False, 'error': 'پیام موردنظر برای پاسخ پیدا نشد.'}), 404

    message = Message(
        content=content,
        role='user',
        chat_id=chat.id,
        user_id=user.id,
        reply_to_id=reply_message.id if reply_message else None
    )
    db.session.add(message)
    chat.updated_at = datetime.utcnow()
    db.session.flush()

    if membership:
        membership.last_read_message_id = message.id

    db.session.commit()

    payload = message.to_dict()
    broadcast_chat(chat.id, {
        'type': 'message:new',
        'chat_id': chat.id,
        'message': payload
    })
    _notify_chat_list(chat)

    return jsonify({'success': True, 'message': payload}), 201


@chat_room.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@is_logged_in
def list_messages(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    after_id = request.args.get('after_id', default=0, type=int)
    query = chat.messages.order_by(Message.id.asc())

    if after_id and after_id > 0:
        query = query.filter(Message.id > after_id)

    messages = query.limit(500).all()
    latest_id = messages[-1].id if messages else after_id

    return jsonify({
        'success': True,
        'messages': [message.to_dict() for message in messages],
        'latest_id': latest_id,
        'chat': _chat_payload(chat, user.id)
    })


@chat_room.route('/api/chats/<int:chat_id>/read', methods=['POST'])
@is_logged_in
def mark_chat_read(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)
    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    data = request.get_json(silent=True) or {}
    try:
        message_id = int(data.get('message_id') or 0)
    except (TypeError, ValueError):
        message_id = 0

    latest = (
        Message.query
        .filter_by(chat_id=chat.id)
        .order_by(Message.id.desc())
        .first()
    )
    if not message_id and latest:
        message_id = latest.id

    member = ChatMember.query.filter_by(chat_id=chat.id, user_id=user.id).first()
    if member and message_id:
        member.last_read_message_id = max(member.last_read_message_id or 0, message_id)
        db.session.commit()

        broadcast_chat(chat.id, {
            'type': 'message:read',
            'chat_id': chat.id,
            'message_id': member.last_read_message_id,
            'user_id': user.id,
            'username': user.username
        })

    return jsonify({'success': True, 'message_id': member.last_read_message_id if member else 0})


# ===================== Edit / Delete Messages =====================

@chat_room.route('/api/messages/<int:message_id>', methods=['PATCH'])
@is_logged_in
def edit_message(message_id: int):
    user = current_user()
    message = Message.query.filter_by(id=message_id).first()

    if not message or message.user_id != user.id or message.is_deleted:
        return jsonify({'success': False, 'error': 'اجازه ویرایش این پیام را ندارید.'}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content or len(content) > 5000:
        return jsonify({'success': False, 'error': 'متن جدید نامعتبر است.'}), 400

    message.content = content
    message.edited_at = datetime.utcnow()
    message.chat.updated_at = datetime.utcnow()
    db.session.commit()

    payload = message.to_dict()
    broadcast_chat(message.chat_id, {
        'type': 'message:updated',
        'chat_id': message.chat_id,
        'message': payload
    })
    return jsonify({'success': True, 'message': payload})


@chat_room.route('/api/messages/<int:message_id>', methods=['DELETE'])
@is_logged_in
def delete_message(message_id: int):
    user = current_user()
    message = Message.query.filter_by(id=message_id).first()

    if not message:
        return jsonify({'success': False, 'error': 'پیام یافت نشد.'}), 404

    chat = message.chat
    membership = ChatMember.query.filter_by(chat_id=chat.id, user_id=user.id).first()
    can_moderate = bool(
        chat.user_id == user.id or (membership and membership.is_admin)
    )

    if message.user_id != user.id and not can_moderate:
        return jsonify({'success': False, 'error': 'اجازه حذف این پیام را ندارید.'}), 403

    message.content = ''
    message.is_deleted = True
    message.edited_at = datetime.utcnow()
    db.session.commit()

    payload = message.to_dict()
    broadcast_chat(message.chat_id, {
        'type': 'message:deleted',
        'chat_id': message.chat_id,
        'message': payload
    })
    return jsonify({'success': True, 'message': payload})


# ===================== Search Messages =====================

@chat_room.route('/api/chats/<int:chat_id>/search', methods=['GET'])
@is_logged_in
def search_messages(chat_id: int):
    user = current_user()
    chat = _user_chat(chat_id, user.id)
    if not chat:
        return jsonify({'success': False, 'error': 'گفتگو یافت نشد.'}), 404

    query = (request.args.get('q') or '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'messages': []})

    messages = (
        Message.query
        .filter(
            Message.chat_id == chat.id,
            Message.is_deleted.is_(False),
            Message.content.ilike(f'%{query[:100]}%')
        )
        .order_by(Message.id.desc())
        .limit(50)
        .all()
    )

    return jsonify({
        'success': True,
        'messages': [message.to_dict() for message in messages]
    })


# ===================== Logout =====================

@chat_room.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_register.login'))
