from app import create_app
from app.extensions import socketio
from config import setting_run
from commands import update_database_from_type_terms

app = create_app()

if __name__ == '__main__':
    if not update_database_from_type_terms(app):
        socketio.run(app, **setting_run)
