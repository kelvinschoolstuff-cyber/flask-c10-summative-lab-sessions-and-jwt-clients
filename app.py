import os
from functools import wraps

from flask import Flask, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from extensions import bcrypt, db, migrate
from models import Note, User


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///app.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        BCRYPT_LOG_ROUNDS=12,
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    def json_error(message, status):
        return jsonify(errors=[message]), status

    def authenticated(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return json_error("Authentication required.", 401)
            return view(*args, **kwargs)

        return wrapped

    def get_payload():
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    @app.post("/signup")
    def signup():
        payload = get_payload()
        username = payload.get("username")
        password = payload.get("password")
        confirmation = payload.get("password_confirmation")
        if not isinstance(username, str) or not username.strip():
            return json_error("Username is required.", 422)
        username = username.strip()
        if len(username) > 80:
            return json_error("Username must be 80 characters or fewer.", 422)
        if not isinstance(password, str) or len(password) < 8:
            return json_error("Password must be at least 8 characters.", 422)
        if len(password.encode("utf-8")) > 72:
            return json_error("Password must be no more than 72 UTF-8 bytes.", 422)
        if password != confirmation:
            return json_error("Password confirmation does not match.", 422)
        if User.query.filter_by(username=username).first():
            return json_error("Username is already taken.", 409)

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return json_error("Username is already taken.", 409)
        session.clear()
        session["user_id"] = user.id
        return jsonify(user.to_dict()), 201

    @app.post("/login")
    def login():
        payload = get_payload()
        username = payload.get("username")
        password = payload.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return json_error("Username and password are required.", 422)
        user = User.query.filter_by(username=username.strip()).first()
        if user is None or not user.check_password(password):
            return json_error("Invalid username or password.", 401)
        session.clear()
        session["user_id"] = user.id
        return jsonify(user.to_dict())

    @app.get("/check_session")
    def check_session():
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is None:
            session.clear()
            return jsonify({})
        return jsonify(user.to_dict())

    @app.delete("/logout")
    def logout():
        session.clear()
        return jsonify({})

    @app.get("/notes")
    @authenticated
    def list_notes():
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 10))
        except (TypeError, ValueError):
            return json_error("page and per_page must be integers.", 400)
        if page < 1 or per_page < 1 or per_page > 100:
            return json_error("page must be positive and per_page must be between 1 and 100.", 400)

        pagination = (
            Note.query.filter_by(user_id=session["user_id"])
            .order_by(Note.created_at.desc(), Note.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
        return jsonify(
            items=[note.to_dict() for note in pagination.items],
            page=pagination.page,
            per_page=pagination.per_page,
            total=pagination.total,
            pages=pagination.pages,
        )

    @app.post("/notes")
    @authenticated
    def create_note():
        payload = get_payload()
        title = payload.get("title")
        content = payload.get("content")
        if not isinstance(title, str) or not title.strip():
            return json_error("Title is required.", 422)
        if len(title.strip()) > 160:
            return json_error("Title must be 160 characters or fewer.", 422)
        if not isinstance(content, str) or not content.strip():
            return json_error("Content is required.", 422)
        note = Note(title=title.strip(), content=content.strip(), user_id=session["user_id"])
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201

    @app.patch("/notes/<int:note_id>")
    @authenticated
    def update_note(note_id):
        note = Note.query.filter_by(id=note_id, user_id=session["user_id"]).first()
        if note is None:
            return json_error("Note not found.", 404)
        payload = get_payload()
        if not payload or set(payload) - {"title", "content"}:
            return json_error("Provide title and/or content to update.", 422)
        if "title" in payload:
            title = payload["title"]
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
                return json_error("Title must be between 1 and 160 characters.", 422)
            note.title = title.strip()
        if "content" in payload:
            content = payload["content"]
            if not isinstance(content, str) or not content.strip():
                return json_error("Content is required.", 422)
            note.content = content.strip()
        db.session.commit()
        return jsonify(note.to_dict())

    @app.delete("/notes/<int:note_id>")
    @authenticated
    def delete_note(note_id):
        note = Note.query.filter_by(id=note_id, user_id=session["user_id"]).first()
        if note is None:
            return json_error("Note not found.", 404)
        db.session.delete(note)
        db.session.commit()
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5555)), debug=os.environ.get("FLASK_DEBUG") == "1")