from datetime import datetime
import secrets

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.Access import current_user, is_logged_in
from app.extensions import db
from app.models import Chat, ChatMember, User


people = Blueprint('people', __name__, url_prefix='/people')


def _find_direct_chat(user_id: int, other_user_id: int):
    '''پیدا کردن گفتگوی دو نفره موجود بین دو کاربر'''
    chats = (
        Chat.query
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .filter(ChatMember.user_id == user_id)
        .all()
    )

    for chat in chats:
        member_ids = {member.user_id for member in chat.members.all()}
        if member_ids == {user_id, other_user_id}:
            return chat
    return None


@people.route('/')
@is_logged_in
def people_page():
    '''جستجوی کاربران برای شروع گفتگوی مستقیم'''
    user = current_user()
    query = request.args.get('q', '').strip()
    users = []

    if query:
        users = (
            User.query
            .filter(
                User.id != user.id,
                User.username.ilike(f'%{query}%')
            )
            .order_by(User.username.asc())
            .limit(20)
            .all()
        )

    return render_template(
        'people.html',
        user=user,
        users=users,
        query=query
    )


@people.route('/start/<int:user_id>', methods=['POST'])
@is_logged_in
def start_direct_chat(user_id: int):
    '''ساخت یا باز کردن گفتگوی مستقیم دو نفره'''
    user = current_user()

    if user.id == user_id:
        abort(400)

    other_user = User.query.filter_by(id=user_id).first_or_404()
    chat = _find_direct_chat(user.id, other_user.id)

    if chat is None:
        chat = Chat(
            title=f'{user.username} ↔ {other_user.username}',
            user_id=user.id
        )
        db.session.add(chat)
        db.session.flush()

        db.session.add_all([
            ChatMember(
                chat_id=chat.id,
                user_id=user.id,
                access_code=secrets.token_urlsafe(24),
                is_owner=True
            ),
            ChatMember(
                chat_id=chat.id,
                user_id=other_user.id,
                access_code=secrets.token_urlsafe(24),
                is_owner=False
            )
        ])

    chat.updated_at = datetime.utcnow()
    db.session.commit()

    return redirect(url_for('chat_room.chatroom'))
