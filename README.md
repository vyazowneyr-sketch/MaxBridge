# MaxBridge MVP

MaxBridge is a production-like MVP bridge between a Max bot and a Telegram bot.
The core flow is unchanged: a Max user receives a public link, a Telegram user
opens it through a Telegram deep link, then messages are relayed both ways.

## Architecture

```text
HTTP/Webhooks -> api adapters -> application use cases -> domain entities
                                      |
                                      v
                         ports: repositories/gateways/rate limiter
                                      |
                                      v
                  infrastructure: SQLAlchemy, aiogram, MockMaxGateway
```

Dependency direction:

- `domain` has only entities, enums, and exceptions.
- `application` has async use cases and Protocol interfaces.
- `infrastructure` implements database repositories, UoW, gateways, and rate limiting.
- `api` parses FastAPI requests and delegates to use cases.

## Project Tree

```text
.
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 202606150001_initial.py
├── src/
│   └── maxbridge/
│       ├── api/
│       │   ├── dependencies.py
│       │   ├── errors.py
│       │   ├── routes.py
│       │   ├── schemas.py
│       │   └── webhook_adapters.py
│       ├── application/
│       │   ├── dto.py
│       │   ├── ports.py
│       │   ├── services.py
│       │   └── use_cases.py
│       ├── domain/
│       │   ├── entities.py
│       │   └── exceptions.py
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── db.py
│       │   ├── gateways.py
│       │   ├── models.py
│       │   ├── rate_limit.py
│       │   ├── repositories.py
│       │   └── unit_of_work.py
│       └── main.py
├── tests/
│   ├── fakes.py
│   └── test_use_cases.py
├── .env.example
├── .dockerignore
├── Dockerfile
├── alembic.ini
├── docker-compose.yml
└── pyproject.toml
```

## Key Decisions

- Database writes are wrapped in an application-level Unit of Work.
- Use cases depend on Protocol ports, not FastAPI, SQLAlchemy, or aiogram.
- The Telegram gateway uses aiogram `Bot`; Max uses `MockMaxGateway` because the real API is unknown.
- `public_id` is generated with `secrets` and internal messenger IDs are never exposed publicly.
- Message validation and rate limiting happen in use cases before persistence.
- MVP active conversation lookup uses the latest `active` conversation.
- Webhook adapters parse messenger payloads, handle expected domain errors with user-facing messages,
  and return `{"ok": true}` to avoid unnecessary messenger retries.
- `/start` parsing is strict: `/start` and Telegram `/start@BotName` are commands; `/startup` is not.
- Docker installs runtime dependencies only and runs the API process as a non-root user.

## API

- `GET /health` returns service health.
- `GET /u/{public_id}` redirects to `https://t.me/{telegram_bot_username}?start={public_id}`.
- `POST /api/internal/telegram/webhook` accepts standard Telegram updates.
- `POST /api/internal/max/webhook` accepts the MVP Max payload:

```json
{"user_id": "max-user-id", "text": "message text"}
```

## Local Run

```bash
# Optional: copy .env.example to .env and set real bot/public URL values.
docker compose up --build
```

The API listens on `http://localhost:8000`.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
black --check .
mypy src tests
```

## Migrations

```bash
alembic upgrade head
```

The initial migration creates `users`, `conversations`, and `messages` with the
required unique constraints and indexes.
