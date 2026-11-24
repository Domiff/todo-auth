# ToDo Auth

A **FastAPI** authentication service for the todo system. Users register and log in with email and
password and get a **JWT** pair: the access token in the response body and the refresh token in an
`HttpOnly` cookie protected with a CSRF double submit.

## Features

- **Auth**: register, login, refresh and logout endpoints.
- **Tokens**: RS256 JWT (authx). Access lives 15 minutes, refresh 30 days.
- **Refresh rotation**: every refresh token works once. `/auth/refresh` burns it atomically
  (Redis `SET NX`), so two concurrent requests with the same token can't both get a new pair.
- **Logout**: revokes both tokens. Revoked tokens are kept in Redis by `jti` until they expire.
- **Admin panel**: sqladmin at `/admin`, available only to active superusers.
- **Messaging**: a RabbitMQ connection is opened on startup for publishing events.

## Tech stack

| Layer          | Technologies                                                    |
|----------------|-----------------------------------------------------------------|
| API            | FastAPI, Uvicorn                                                |
| Auth           | authx, PyJWT (RS256), pwdlib (Argon2)                           |
| Database       | PostgreSQL, SQLAlchemy 2 (asyncio, asyncpg), Alembic            |
| Token blocklist| Redis                                                           |
| Messaging      | RabbitMQ (aio-pika)                                             |
| Admin          | sqladmin                                                        |
| Tooling        | uv, Ruff                                                        |
| Infrastructure | Postgres, Redis and RabbitMQ live in [todo-infrastructure](#infrastructure) |

## Application structure

```text
.
├── backend/
│   ├── main.py                    # app = create_app()
│   ├── core/                      # settings, logging, app factory, error handlers
│   ├── auth/                      # models, repository, service, router, authx config
│   ├── admin/                     # sqladmin setup and admin login backend
│   └── infrastructures/           # postgresql, redis and rabbitmq clients
├── migrations/                    # Alembic migrations
├── templates/sqladmin/            # sqladmin template overrides (email login form)
├── keys/                          # RSA key pair for JWT (gitignored)
├── alembic.ini
├── Dockerfile
├── docker-compose.yml             # auth service only; infrastructure is in todo-infrastructure
├── pyproject.toml
└── uv.lock
```

## Requirements

- **Python 3.14+**
- **[uv](https://docs.astral.sh/uv/)**
- **Docker** / Docker Compose and a running [todo-infrastructure](#infrastructure) stack

## Configuration

Copy `.env_template` to `.env` at the repository root (it is gitignored):

```bash
cp .env_template .env
```

| Variable                                            | Purpose                                                                 |
|-----------------------------------------------------|-------------------------------------------------------------------------|
| `IS_DEBUG`                                          | Debug mode (`true` by default). Enables `/docs` and lets the admin session cookie go over HTTP. Keep it `false` in production |
| `ADMIN_SECRET_KEY`                                  | Secret for signing the admin session cookie                             |
| `CORS_ORIGINS`                                      | JSON list of frontend origins, e.g. `["http://localhost:5173"]`         |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | The service's own database and owner in `todo-pg` (`todo_auth`)          |
| `POSTGRES_HOST`, `POSTGRES_PORT`                    | `todo-pg` and `5432` in Docker; `127.0.0.1` when running on the host    |
| `DB_ECHO`                                           | Log SQL queries (`false` by default)                                    |
| `REDIS_USER`, `REDIS_PASSWORD`                      | The `todo-auth` ACL user from todo-infrastructure's `redis.acl` (keys `auth:*`) |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`              | `todo-redis`, `6379` and `0` in Docker; `127.0.0.1` on the host         |
| `RABBITMQ_USER`, `RABBITMQ_PASSWORD`                | Same credentials as in todo-infrastructure's `.env`                     |
| `RABBITMQ_HOST`, `RABBITMQ_PORT`                    | `todo-rabbitmq` and `5672` in Docker; `127.0.0.1` on the host           |

### JWT keys

Tokens are signed with RS256. Generate the key pair once into `keys/`:

```bash
mkdir -p keys
openssl genrsa -out keys/jwt-private.pem 2048
openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem
chmod 600 keys/jwt-private.pem
```

The private key stays in this service. Other services only need `jwt-public.pem` to verify access
tokens. The keys are never copied into the Docker image: compose mounts `./keys` read-only.

## Local development (without Docker)

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Start todo-infrastructure, create `.env` and set the hosts to `127.0.0.1`.

3. Apply migrations:
   ```bash
   uv run alembic upgrade head
   ```

4. Start the API:
   ```bash
   uv run fastapi dev --port 8010
   ```

The refresh cookie is set with the `Secure` flag, so a client opened over plain HTTP may not send it
back. Browsers allow it on `localhost`, but Insomnia, Postman and curl don't.

## Infrastructure

Postgres, Redis and RabbitMQ are not part of this repository. They run in the separate
**todo-infrastructure** stack, and this service connects to it over the external Docker network
**`todo-network`**.

Start order: **todo-infrastructure → todo-auth**. The app connects to RabbitMQ on startup and fails
to start if the broker is down.

## Docker Compose

1. Start todo-infrastructure. Check that `todo-pg` has the `todo_auth` database and Redis has
   the `todo-auth` ACL user (see its README).

2. Set the Docker hosts in `.env` (`todo-pg`, `todo-redis`, `todo-rabbitmq`), as in `.env_template`.

3. Generate the [JWT keys](#jwt-keys) if `keys/` is empty.

4. Build and start the service:
   ```bash
   docker compose up -d --build
   ```

5. Apply migrations:
   ```bash
   docker compose exec auth alembic upgrade head
   ```

| Service        | Container   | Port                 | Notes                                                    |
|----------------|-------------|----------------------|----------------------------------------------------------|
| Auth (Uvicorn) | `todo-auth` | 8010 (not published) | Reachable as `todo-auth:8010` from other services in `todo-network` |

### Reverse proxy

The port is not published to the host: the service is opened through Caddy from todo-infrastructure,
which sends `/auth/*` to `todo-auth:8010` and everything else to todo-api. Locally that is
`http://localhost:8080/auth/...`, in production the domain.

Uvicorn trusts the `X-Forwarded-*` headers from Caddy (`UVICORN_PROXY_HEADERS`,
`UVICORN_FORWARDED_ALLOW_IPS`), so the app sees the original `https` scheme and client IP.

Only `/auth/*` reaches this service through Caddy. `/admin` and `/docs` go to todo-api, so to open
the admin panel through the proxy set `ADMIN_BASE_URL=/auth/admin`.

## API overview

| Method | Path             | Request                                       | Response                                     |
|--------|------------------|-----------------------------------------------|----------------------------------------------|
| POST   | `/auth/register` | JSON `{"email", "password"}`                  | `201`, access token in the body, refresh cookie |
| POST   | `/auth/login`    | JSON `{"email", "password"}`                  | `200`, access token in the body, refresh cookie |
| POST   | `/auth/refresh`  | refresh cookie + `X-CSRF-TOKEN`               | `200`, a new pair; the old refresh is revoked |
| POST   | `/auth/logout`   | `Authorization` + refresh cookie + `X-CSRF-TOKEN` | `204`, both tokens revoked, cookies cleared |
| POST   | `/auth/verify`   | `Authorization`                                | `200`, current user |

Response body of register, login and refresh:

```json
{"access": "<access token>", "type": "bearer"}
```

Login and register also set two cookies:

- `refresh_token_cookie`: the refresh token (`HttpOnly`, `Secure`, `SameSite=Lax`, 30 days).
- `csrf_refresh_token`: the CSRF value. It is readable from JavaScript on purpose.

Headers for `/auth/refresh` and `/auth/logout`:

```
Authorization: Bearer <access>                      # logout only
Cookie: refresh_token_cookie=<refresh>              # sent by the browser automatically
X-CSRF-TOKEN: <value of the csrf_refresh_token cookie>
```

`X-CSRF-TOKEN` holds only the cookie value, without the `csrf_refresh_token=` prefix. Both cookies
change on every refresh, so read the value from the current cookie. Frontend requests need
`credentials: "include"`.

Examples go through Caddy (`localhost:8080`); with `fastapi dev` on the host use `localhost:8010`.

Example login:

```bash
curl -i -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'
```

Example logout (`-b` sends the cookie):

```bash
curl -i -X POST http://localhost:8080/auth/logout \
  -H "Authorization: Bearer <access>" \
  -H "X-CSRF-TOKEN: <csrf>" \
  -b "refresh_token_cookie=<refresh>"
```

### Errors

| Code  | Endpoint                 | When                                                                 |
|-------|--------------------------|----------------------------------------------------------------------|
| `409` | register                 | The email is already registered                                      |
| `422` | register, login          | The body is invalid: missing field or not an email                   |
| `401` | login                    | Wrong email or password, or the user is inactive (one message for all) |
| `401` | refresh, logout          | No refresh cookie or no `X-CSRF-TOKEN`, CSRF mismatch, token expired, revoked or already used, the user is inactive; logout also when `Authorization` is missing or the tokens belong to different users |

Two body formats, depending on where the error comes from:

```json
{"detail": "Invalid credentials"}
```

```json
{"message": "CSRF double submit does not match", "error_type": "CSRFError"}
```

The first is returned by the service (`Invalid credentials`, `Invalid token`, `Already Exists`),
the second by authx when it can't read or verify a token. A missing CSRF header is reported as
`MissingTokenError`.

Interactive docs (`IS_DEBUG=true` only): `/docs`.

## Admin panel

`/admin` lets only active superusers in. There is no command to create one yet: register through
the API, then set the flag in the database:

```sql
UPDATE users SET is_superuser = true WHERE email = 'admin@example.com';
```

## Development tooling

- **Ruff**: `uv run ruff check .` and `uv run ruff format .` (see `pyproject.toml`)
- **New migration**: `uv run alembic revision --autogenerate -m "<message>"` (the generated file is
  formatted with Ruff by a post-write hook)
