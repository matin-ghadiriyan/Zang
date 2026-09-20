from app import create_app
from config import setting_run
from commands import update_database_from_type_terms

app = create_app()

if __name__ == '__main__':
    if not update_database_from_type_terms(app):
        app.run(**setting_run)