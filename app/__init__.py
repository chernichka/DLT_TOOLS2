import os
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{os.path.join(app.instance_path, 'cutters.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from app import models  # noqa: F401

    with app.app_context():
        db.create_all()

    from app.routes import register_routes

    register_routes(app)

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow}

    return app
