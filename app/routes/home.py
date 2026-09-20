from flask import Blueprint, redirect, render_template, session, url_for

home = Blueprint('home', __name__)


@home.route('/')
def index():
    '''صفحه اصلی سایت'''
    if session.get('logged_in'):
        return redirect(url_for('chat_room.chatroom'))
    return render_template('index.html')