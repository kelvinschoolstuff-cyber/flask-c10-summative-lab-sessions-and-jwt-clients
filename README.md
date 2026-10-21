# Personal Notes API

A Flask REST API for account registration, cookie-based session authentication, and private user-owned notes. It is designed to work with the included `client-with-sessions` frontend, which proxies requests to `http://localhost:5555`.

## Requirements

- Python 3.8 or newer
- Pipenv

## Install and configure

```bash
pipenv install --dev
pipenv run flask --app app db upgrade
```

The initial schema migration is included in the repository. For future model changes, generate a revision with `pipenv run flask --app app db migrate -m "describe the change"`, review it, and apply it with `pipenv run flask --app app db upgrade`.

Set a strong `SECRET_KEY` before deployment. The default is for local development only. Set `DATABASE_URL` to use a database other than the default SQLite database. For HTTPS deployments, set `COOKIE_SECURE=true`.

## Seed data

```bash
pipenv run python seed.py
```

This safely creates tables and adds one demo user and ten sample notes if the demo user does not already exist. Demo credentials: `demo` / `password123`. Do not use this account in a deployed environment.

## Run and test

```bash
pipenv run flask --app app run --host 0.0.0.0 --port 5555
pipenv run python -m pytest
```

Run the included session frontend in another terminal with `cd client-with-sessions && npm install && npm start`.

## API

All request and response bodies are JSON. Validation/authentication errors use `{"errors": ["message"]}`. Authenticated endpoints use the Flask session cookie set by signup or login. Unauthenticated resource requests return `401`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/signup` | Register and sign in. Body: `username`, `password`, `password_confirmation`. Returns `201` and `{ "id", "username" }`. |
| `POST` | `/login` | Sign in. Body: `username`, `password`. Returns `{ "id", "username" }`. |
| `GET` | `/check_session` | Return the current user, or `{}` when signed out. |
| `DELETE` | `/logout` | Clear the current session; returns `{}`. |
| `GET` | `/notes?page=1&per_page=10` | List only the current user's notes. `per_page` is capped at 100. Returns `{ "items", "page", "per_page", "total", "pages" }`. |
| `POST` | `/notes` | Create a note. Body: `title`, `content`; owner is taken from the session. Returns `201` and the note. |
| `PATCH` | `/notes/<id>` | Update the current user's note with `title` and/or `content`. |
| `DELETE` | `/notes/<id>` | Delete the current user's note. Returns `204`; inaccessible or missing notes return `404`. |

Notes include `id`, `title`, `content`, `created_at`, `updated_at`, and `user_id`. Notes are always looked up through the authenticated user's ID for update and deletion, and list queries are scoped to that ID.