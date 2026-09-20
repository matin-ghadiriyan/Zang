from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)
from sqlalchemy.exc import IntegrityError

from app.Access import is_guest
from app.extensions import db
from app.models import User


login_register = Blueprint('login_register', __name__)


#=====================Login=====================

@login_register.route('/login', methods=['GET', 'POST'])
@is_guest
def login():
    '''ورود کاربر'''

    if request.method == 'GET':
        return render_template('login_register/login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash('نام کاربری و رمز عبور الزامی است.')
        return render_template('login_register/login.html')

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        flash('نام کاربری یا رمز عبور نادرست است.')
        return render_template('login_register/login.html')

    # Clear old session data before creating a new authenticated session.
    session.clear()

    session['logged_in'] = True
    session['user_id'] = user.id

    return redirect(url_for('chat_room.chatroom'))


#=====================Register=====================

@login_register.route('/register', methods=['GET', 'POST'])
@is_guest
def register():
    '''ثبت‌نام کاربر'''

    if request.method == 'GET':
        return render_template('login_register/register.html')

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    #=====================Validation=====================

    if not username or not email or not password:
        flash('همه فیلدها الزامی هستند.')
        return render_template('login_register/register.html')

    if len(username) < 3 or len(username) > 50:
        flash('نام کاربری باید بین ۳ تا ۵۰ کاراکتر باشد.')
        return render_template('login_register/register.html')

    if len(email) > 120:
        flash('ایمیل بیش از حد طولانی است.')
        return render_template('login_register/register.html')

    if len(password) < 8:
        flash('رمز عبور باید حداقل ۸ کاراکتر باشد.')
        return render_template('login_register/register.html')

    #=====================Duplicate Check=====================

    if User.query.filter_by(username=username).first():
        flash('این نام کاربری قبلاً ثبت شده است.')
        return render_template('login_register/register.html')

    if User.query.filter_by(email=email).first():
        flash('این ایمیل قبلاً ثبت شده است.')
        return render_template('login_register/register.html')

    #=====================Create User=====================

    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash('نام کاربری یا ایمیل قبلاً ثبت شده است.')
        return render_template('login_register/register.html')

    #=====================Login User=====================

    session.clear()

    session['logged_in'] = True
    session['user_id'] = user.id

    return redirect(url_for('chat_room.chatroom'))