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
from app.models import Chat, Message


chat_room = Blueprint('chat_room', __name__, url_prefix='/chat')


#=====================Chat Page=====================

@chat_room.route('/')
@is_logged_in
def chatroom():
    '''صفحه اصلی پیام‌رسان'''
    user = current_user()
    chats = user.chats.order_by(Chat.updated_at.desc()).all()
    return render_template(
        'chatroom/chatroom.html',
        user=user,
        chats=[chat.to_dict() for chat in chats]
    )


#=====================List Chats=====================

@chat_room.route('/api/chats', methods=['GET'])
@is_logged_in
def list_chats():
    '''دریافت لیست گفتگوها'''
    user = current_user()
    chats = user.chats.order_by(Chat.updated_at.desc()).all()
    return jsonify({
        'success': True,
        'chats': [chat.to_dict() for chat in chats]
    })


#=====================Create Chat=====================

@chat_room.route('/api/chats', methods=['POST'])
@is_logged_in
def create_chat():
    '''ایجاد گفتگوی جدید'''
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip() or 'گفتگوی جدید'

    if len(title) > 120:
        return jsonify({
            'success': False,
            'error': 'عنوان گفتگو بیش از حد طولانی است.'
        }), 400

    chat = Chat(title=title, user_id=user.id)
    db.session.add(chat)
    db.session.commit()

    return jsonify({'success': True, 'chat': chat.to_dict()}), 201


#=====================Get Chat=====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['GET'])
@is_logged_in
def get_chat(chat_id: int):
    '''دریافت یک گفتگو همراه پیام‌ها'''
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    return jsonify({'success': True, 'chat': chat.to_dict(include_messages=True)})


#=====================Delete Chat=====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@is_logged_in
def delete_chat(chat_id: int):
    '''حذف گفتگو'''
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    db.session.delete(chat)
    db.session.commit()

    return jsonify({'success': True})


#=====================Rename Chat=====================

@chat_room.route('/api/chats/<int:chat_id>', methods=['PATCH'])
@is_logged_in
def rename_chat(chat_id: int):
    '''تغییر عنوان گفتگو'''
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()

    if not title or len(title) > 120:
        return jsonify({
            'success': False,
            'error': 'عنوان نامعتبر است.'
        }), 400

    chat.title = title
    db.session.commit()

    return jsonify({'success': True, 'chat': chat.to_dict()})


#=====================Send Message=====================

@chat_room.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@is_logged_in
def send_message(chat_id: int):
    '''ارسال پیام در گفتگو'''
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

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

    message = Message(content=content, role='user', chat_id=chat.id)
    db.session.add(message)
    chat.updated_at = message.created_at or chat.updated_at
    db.session.commit()

    return jsonify({'success': True, 'message': message.to_dict()}), 201


#=====================List Messages=====================

@chat_room.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@is_logged_in
def list_messages(chat_id: int):
    '''دریافت پیام‌های یک گفتگو'''
    user = current_user()
    chat = Chat.query.filter_by(id=chat_id, user_id=user.id).first()

    if not chat:
        return jsonify({
            'success': False,
            'error': 'گفتگو یافت نشد.'
        }), 404

    messages = chat.messages.order_by(Message.created_at).all()

    return jsonify({
        'success': True,
        'messages': [message.to_dict() for message in messages]
    })


#=====================Delete Message=====================

@chat_room.route('/api/messages/<int:message_id>', methods=['DELETE'])
@is_logged_in
def delete_message(message_id: int):
    '''حذف پیام'''
    user = current_user()
    message = Message.query.filter_by(id=message_id).first()

    if not message or message.chat.user_id != user.id:
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
