import os
from flask import Flask, render_template
from flask_migrate import upgrade, stamp
from app.extensions import db, migrate, socketio
from app.request_limiter import rate_limit
from app.routes import Blue_prints
from config import Config


def create_app() -> Flask:
    """Create and configure the application."""

    app = Flask(
        __name__,
        template_folder="templats",
        static_folder="static"
    )

    app.config.from_object(Config)

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = Config.SECRET_KEY

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///zang.db"

    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, async_mode="threading")

    for blue_print in Blue_prints():
        app.register_blueprint(blue_print)

    # Register Socket.IO events after extensions and blueprints are ready.
    from app.realtime import register_socket_events
    register_socket_events(socketio)

    @app.errorhandler(404)
    def not_found(_):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(_):
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("errors/403.html"), 403

    @app.errorhandler(401)
    def unauthorized(_):
        return render_template("errors/401.html"), 401

    @app.context_processor
    def inject_user():
        from app.Access import current_user
        return {"current_user": current_user()}

    @app.before_request
    def before_request():
        if not rate_limit():
            return render_template("errors/429.html"), 429

    with app.app_context():
        _auto_update_database(app)

    return app


def _auto_update_database(app: Flask) -> None:
    """Run migrations or create database tables."""

    migrations_dir = os.path.join(app.root_path, "..", "migrations")

    if os.path.isdir(migrations_dir):
        try:
            upgrade()
            return
        except Exception:
            db.session.rollback()

            try:
                stamp()
                upgrade()
                return
            except Exception:
                pass

    db.create_all()
