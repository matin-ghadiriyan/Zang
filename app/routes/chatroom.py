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
from app.models import Chat, ChatMember, Message


chat_room = Blueprint('chat_room', __name__, url_prefix='/chat')

MAX_CODE_LEN = 64
MAX_CODES = 10


#=====================Helpers=====================

def _parse_codes(raw) -> list[str]:
    '''تبدیل ورودی شناسه‌ها به لیست تمیز و یکتا'''
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

    codes: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part is None:
            continue
        code = str(part).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def _is_channel(chat: Chat) -> bool:
    '''کانال‌ها بدون تغییر دیتابیس با # در ابتدای عنوان مشخص می‌شوند.'''
    return bool(chat.title and chat.title.startswith('#'))


def _user_chat(chat_id: int, user_id: int):
    '''گفتگویی که کاربر عضو آن است'''
    return (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(Chat.id == chat_id, ChatMember.user_id == user_id)
        .first()
    )


def _user_chats(user_id: int):
    '''همه گفتگوهایی که کاربر عضو آن‌هاست'''
    return (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(ChatMember.user_id == user_id)
        .order_by(Chat.updated_at.desc())
        .all()
    )


def _chat_payload(
    chat: Chat,
    user_id: int,
    include_messages: bool = False
) -> dict:
    '''اطلاعات گفتگو همراه با وضعیت کانال و دسترسی کاربر'''
    data = chat.to_dict(include_messages=include_messages)
    is_channel = _is_channel(chat)
    is_owner = chat.user_id == user_id

    data.update({
        'kind': 'channel' if is_channel else 'chat',
        'is_owner': is_owner,
        'can_post': (not is_channel) or is_owner,
    })

    if is_channel and is_owner:
        owner_member = ChatMember.query.filter_by(
            chat_id=chat.id,
            user_id=user_id
        ).first()
        if owner_member:
            data['invite_code'] = owner_member.access_code

    return data


def _new_unique_code() -> str:
    '''ساخت کد عضویت کوتاه برای کانال'''
    while True:
        code = f'zang-{secrets.token_urlsafe(5)}'
        if not ChatMember.query.filter_by(access_code=code).first():
            return code


#=====================Chat Page=====================

@chat_room.route('/')
@is_logged_in
def chatroom():
    '''صفحه اصلی پیام‌رسان'''
    user = current_user()
    chats = _user_chats(user.id)
    return render_template(
        'chatroom/chatroom.html',
        user=user,
        chats=[_chat_payload(chat, user.id) for chat in chats]
    )


#=====================List Chats=====================

@chat_room.route('/api/chats', methods=['GET'])
@is_logged_in
def list_chats():
    '''دریافت لیست گفتگوها و کانال‌ها'''
    user = current_user()
    chats = _user_chats(user.id)
    return jsonify({
        'success': True,
        'chats': [_chat_payload(chat, user.id) for chat in chats]
    })


#=====================Create Chat=====================

@chat_room.route('/api/chats', methods=['POST'])
@is_logged_in
def create_chat():
    '''ایجاد گفتگوی جدید با شناسه‌های دسترسی'''
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip() or 'گفتگوی جدید'
    codes = _parse_codes(data.get('codes'))

    if len(title) > 120:
        return jsonify({
            'success': False,
            'error': 'عنوان گفتگو بیش از حد طولانی است.'
        }), 400

    if not codes:
        return jsonify({
            'success': False,
            'error': 'حداقل یک شناسه برای گفتگو لازم است.'
        }), 400

    if len(codes) > MAX_CODES:
        return jsonify({
            'success': False,
            'error': f'حداکثر {MAX_CODES} شناسه مجاز است.'
        }), 400

    for code in codes:
        if len(code) > MAX_CODE_LEN:
            return jsonify({
                'success': False,
                'error': f'طول هر شناسه حداکثر {MAX_CODE_LEN} کاراکتر است.'
            }), 400

    chat = Chat(title=title.lstrip('#'), user_id=user.id)
    db.session.add(chat)
    db.session.flush()

    db.session.add(ChatMember(
        chat_id=chat.id,
        user_id=user.id,
        access_code=codes[0],
        is_owner=True
    ))

    db.session.commit()

    return jsonify({
        'success': True,
        'chat': _chat_payload(chat, user.id),
        'codes': codes
    }), 201


#=====================Create Channel=====================

@chat_room.route('/api/channels', methods=['POST'])
@is_logged_in
def create_channel():
    '''ایجاد کانال ساده؛ فقط سازنده می‌تواند در آن پیام بفرستد'''
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip().lstrip('#').strip()
    requested_code = (data.get('code') or '').strip()

    if len(title) < 2 or len(title) > 60:
        return jsonify({
            'success': False,
            'error': 'نام کانال باید بین ۲ تا ۶۰ کاراکتر باشد.'
        }), 400

    if requested_code:
        if len(requested_code) > MAX_CODE_LEN:
            return jsonify({
                'success': False,
                'error': f'طول کد عضویت حداکثر {MAX_CODE_LEN} کاراکتر است.'
            }), 400
        if ChatMember.query.filter_by(access_code=requested_code).first():
            return jsonify({
                'success': False,
                'error': 'این کد عضویت قبلاً استفاده شده است.'
            }), 409
        code = requested_code
    else:
        code = _new_unique_code()

    channel = Chat(title=f'#{title}', user_id=user.id)
    db.session.add(channel)
    db.session.flush()

    db.session.add(ChatMember(
        chat_id=channel.id,
        user_id=user.id,
        access_code=code,
        is_owner=True
    ))
    db.session.commit()

    return jsonify({
        'success': True,
        'chat': _chat_payload(channel, user.id),
        'invite_code': code
    }), 201


#=====================Join Chat / Channel=====================

@chat_room.route('/api/chats/join', methods=['POST'])
@is_logged_in
def join_chat():
    '''ورود به گفتگو یا کانال با شناسه'''
    user = current_user()
    data = request.get_json(silent=True) or {}
    codes = _parse_codes(data.get('codes') or data.get('code'))

    if not codes:
        return jsonify({
            'success': False,
            'error': 'شناسه را وارد کنید.'
        }), 400

    for code in codes:
        if len(code) > MAX_CODE_LEN:
            return jsonify({
                'success': False,
                'error': f'طول هر شناسه حداکثر {MAX_CODE_LEN} کاراکتر است.'
            }), 400

    joined = []
    joined_ids: set[int] = set()

    for code in codes:
        member = ChatMember.query.filter_by(access_code=code).first()
        if not member:
            continue

        chat = Chat.query.filter_by(id=member.chat_id).first()
        if not chat or chat.id in joined_ids:
            continue

        exists = ChatMember.query.filter_by(
            chat_id=chat.id,
            user_id=user.id
        ).first()

        if not exists:
            db.session.add(ChatMember(
                chat_id=chat.id,
                user_id=user.id,
                access_code=code,
                is_owner=False
            ))

        joined_ids.add(chat.id)
        joined.append(chat)

    if not joined:
        return jsonify({
            'success': False,
            'error': 'هیچ گفتگو یا کانالی با این شناسه یافت نشد.'
        }), 404

    db.session.commit()

    return jsonify({
        'success': True,
        'chats': [_chat_payload(chat, user.id) for chat in joined]
    })


#=====================Get Chat=====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['GET'])
@is_logged_in
def get_chat(chat_id: int):
    '''دریافت یک گفتگو همراه پیام‌ها'''
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    return jsonify({
        'success': True,
        'chat': _chat_payload(chat, user.id, include_messages=True)
    })


#=====================Delete Chat=====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@is_logged_in
def delete_chat(chat_id: int):
    '''حذف گفتگو یا کانال؛ فقط سازنده'''
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد یا اجازه حذف آن را ندارید.'
        }), 404

    db.session.delete(chat)
    db.session.commit()

    return jsonify({'success': True})


#=====================Rename Chat=====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['PATCH'])
@is_logged_in
def rename_chat(chat_id: int):
    '''تغییر عنوان گفتگو یا کانال'''
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    is_channel = _is_channel(chat)
    if is_channel and chat.user_id != user.id:
        return jsonify({
            'success': False,
            'error': 'فقط مدیر کانال می‌تواند نام آن را تغییر دهد.'
        }), 403

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()

    if not title or len(title) > 120:
        return jsonify({
            'success': False,
            'error': 'عنوان نامعتبر است.'
        }), 400

    title = title.lstrip('#').strip()
    chat.title = f'#{title}' if is_channel else title
    db.session.commit()

    return jsonify({
        'success': True,
        'chat': _chat_payload(chat, user.id)
    })


#=====================Send Message=====================

@chat_room.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@is_logged_in
def send_message(chat_id: int):
    '''ارسال پیام در گفتگو؛ در کانال فقط مدیر مجاز است'''
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    if _is_channel(chat) and chat.user_id != user.id:
        return jsonify({
            'success': False,
            'error': 'در کانال فقط مدیر می‌تواند پیام ارسال کند.'
        }), 403

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({
            'success': False,
            'error': 'متن پیام خالی است.'
        }), 400

    if len(content) > 5000:
        return jsonify({
            'success': False,
            'error': 'متن پیام بیش از حد طولانی است.'
        }), 400

    message = Message(
        content=content,
        role='user',
        chat_id=chat.id,
        user_id=user.id
    )
    db.session.add(message)
    chat.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': message.to_dict()
    }), 201


#=====================List Messages=====================

@chat_room.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@is_logged_in
def list_messages(chat_id: int):
    '''دریافت پیام‌ها؛ after_id برای همگام‌سازی خودکار بدون رفرش'''
    user = current_user()
    chat = _user_chat(chat_id, user.id)

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    after_id = request.args.get('after_id', default=0, type=int)
    query = chat.messages.order_by(Message.id.asc())

    if after_id and after_id > 0:
        query = query.filter(Message.id > after_id)

    messages = query.all()
    latest_id = messages[-1].id if messages else after_id

    return jsonify({
        'success': True,
        'messages': [message.to_dict() for message in messages],
        'latest_id': latest_id,
        'chat': _chat_payload(chat, user.id)
    })


#=====================Delete Message=====================

@chat_room.route('/api/messages/<int:message_id>', methods=['DELETE'])
@is_logged_in
def delete_message(message_id: int):
    '''حذف پیام؛ فقط فرستنده همان پیام'''
    user = current_user()
    message = Message.query.filter_by(id=message_id).first()

    if not message or message.user_id != user.id:
        return jsonify({
            'success': False,
            'error': 'پیام یافت نشد.'
        }), 404

    db.session.delete(message)
    db.session.commit()

    return jsonify({'success': True})


#=====================Logout=====================

@chat_room.route('/logout')
def logout():
    '''خروج از حساب کاربری'''
    session.clear()
    return redirect(url_for('login_register.login'))
