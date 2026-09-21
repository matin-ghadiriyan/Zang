from flask import (
    Blueprint,
    jsonify,
    render_template,
    request
)
from sqlalchemy.exc import IntegrityError

from app.Access import current_user, is_logged_in
from app.extensions import db
from app.models import User


account = Blueprint('account', __name__, url_prefix='/account')

THEMES = {'zang', 'light', 'dark'}


#=====================Account Page=====================

@account.route('/')
@is_logged_in
def panel():
    '''صفحه پنل کاربری'''
    user = current_user()
    return render_template('account/panel.html', user=user)


#=====================Get Profile=====================

@account.route('/api/profile', methods=['GET'])
@is_logged_in
def get_profile():
    '''دریافت اطلاعات پروفایل کاربر'''
    user = current_user()
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


#=====================Update Theme=====================

@account.route('/api/theme', methods=['PATCH'])
@is_logged_in
def update_theme():
    '''تغییر تم انتخابی کاربر'''
    user = current_user()
    data = request.get_json(silent=True) or {}
    theme = (data.get('theme') or '').strip().lower()

    if theme not in THEMES:
        return jsonify({
            'success': False,
            'error': 'تم انتخابی نامعتبر است.'
        }), 400

    user.theme = theme
    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


#=====================Update Profile=====================

@account.route('/api/profile', methods=['PATCH'])
@is_logged_in
def update_profile():
    '''ویرایش نام کاربری و ایمیل'''
    user = current_user()
    data = request.get_json(silent=True) or {}

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()

    if not username or not email:
        return jsonify({
            'success': False,
            'error': 'نام کاربری و ایمیل الزامی است.'
        }), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({
            'success': False,
            'error': 'نام کاربری باید بین ۳ تا ۵۰ کاراکتر باشد.'
        }), 400

    if len(email) > 120 or '@' not in email:
        return jsonify({
            'success': False,
            'error': 'ایمیل نامعتبر است.'
        }), 400

    if User.query.filter(User.username == username, User.id != user.id).first():
        return jsonify({
            'success': False,
            'error': 'این نام کاربری قبلاً ثبت شده است.'
        }), 409

    if User.query.filter(User.email == email, User.id != user.id).first():
        return jsonify({
            'success': False,
            'error': 'این ایمیل قبلاً ثبت شده است.'
        }), 409

    user.username = username
    user.email = email

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'نام کاربری یا ایمیل تکراری است.'
        }), 409

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


#=====================Change Password=====================

@account.route('/api/password', methods=['PATCH'])
@is_logged_in
def change_password():
    '''تغییر رمز عبور'''
    user = current_user()
    data = request.get_json(silent=True) or {}

    current = data.get('current_password') or ''
    new = data.get('new_password') or ''
    confirm = data.get('confirm_password') or ''

    if not current or not new or not confirm:
        return jsonify({
            'success': False,
            'error': 'همه فیلدهای رمز عبور الزامی است.'
        }), 400

    if not user.check_password(current):
        return jsonify({
            'success': False,
            'error': 'رمز عبور فعلی نادرست است.'
        }), 403

    if len(new) < 8:
        return jsonify({
            'success': False,
            'error': 'رمز عبور جدید باید حداقل ۸ کاراکتر باشد.'
        }), 400

    if new != confirm:
        return jsonify({
            'success': False,
            'error': 'تکرار رمز عبور مطابقت ندارد.'
        }), 400

    user.set_password(new)
    db.session.commit()

    return jsonify({'success': True})
