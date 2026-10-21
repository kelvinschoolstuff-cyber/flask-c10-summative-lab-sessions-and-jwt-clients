import pytest

from app import create_app
from extensions import db
from models import Note, User


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "BCRYPT_LOG_ROUNDS": 4,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def signup(client, username):
    return client.post(
        "/signup",
        json={
            "username": username,
            "password": "correct-horse-1",
            "password_confirmation": "correct-horse-1",
        },
    )


def test_session_auth_and_validation(client):
    response = signup(client, "alice")
    assert response.status_code == 201
    assert response.json == {"id": 1, "username": "alice"}
    assert client.get("/check_session").json == response.json

    client.delete("/logout")
    assert client.get("/check_session").json == {}
    assert client.post("/login", json={"username": "alice", "password": "bad"}).status_code == 401
    assert client.post(
        "/signup",
        json={"username": "bob", "password": "short", "password_confirmation": "short"},
    ).status_code == 422
    long_password = "x" * 73
    assert client.post(
        "/signup",
        json={
            "username": "charlie",
            "password": long_password,
            "password_confirmation": long_password,
        },
    ).status_code == 422


def test_notes_crud_pagination_and_user_isolation(app, client):
    assert client.get("/notes").status_code == 401
    signup(client, "alice")
    created = client.post("/notes", json={"title": "First", "content": "Private note"})
    assert created.status_code == 201
    note_id = created.json["id"]
    assert created.json["user_id"] == 1
    assert client.get("/notes?page=1&per_page=1").json["total"] == 1

    client.delete("/logout")
    signup(client, "bob")
    assert client.get("/notes").json["total"] == 0
    assert client.patch(f"/notes/{note_id}", json={"title": "Stolen"}).status_code == 404
    assert client.delete(f"/notes/{note_id}").status_code == 404

    client.delete("/logout")
    client.post("/login", json={"username": "alice", "password": "correct-horse-1"})
    assert client.patch(f"/notes/{note_id}", json={"title": "Updated"}).json["title"] == "Updated"
    assert client.delete(f"/notes/{note_id}").status_code == 204
    with app.app_context():
        assert db.session.query(Note).count() == 0
        assert db.session.query(User).count() == 2