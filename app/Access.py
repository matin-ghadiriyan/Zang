from functools import wraps

from flask import redirect, session, url_for

from app.models import User


def current_user():
    '''دریافت کاربر فعلی از سشن'''
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.filter_by(id=user_id).first()


def is_logged_in(function: callable) -> callable:
    '''دکوراتور بررسی ورود کاربر'''

    @wraps(function)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')

        if not session.get('logged_in') or not user_id:
            session.clear()
            return redirect(url_for('login_register.login'))

        if not User.query.filter_by(id=user_id).first():
            session.clear()
            return redirect(url_for('login_register.login'))

        return function(*args, **kwargs)

    return wrapper


def is_guest(function: callable) -> callable:
    '''دکوراتور برای صفحات ورود و ثبت‌نام'''

    @wraps(function)
    def wrapper(*args, **kwargs):
        if session.get('logged_in') and current_user():
            return redirect(url_for('chat_room.chatroom'))
        return function(*args, **kwargs)

    return wrapper
