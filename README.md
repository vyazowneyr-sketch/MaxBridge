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
|-- alembic/
|   |-- env.py
|   |-- script.py.mako
|   `-- versions/
|       `-- 202606150001_initial.py
|-- src/
|   `-- maxbridge/
|       |-- api/
|       |-- application/
|       |-- domain/
|       |-- infrastructure/
|       `-- main.py
|-- tests/
|-- .env.example
|-- .dockerignore
|-- Dockerfile
|-- alembic.ini
|-- docker-compose.yml
`-- pyproject.toml
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

## Docker Compose Configuration

For the bundled PostgreSQL service, do not set `DATABASE_URL` in `.env`.
Compose builds the internal URL itself and points the API to the service DNS name `postgres`.

Use these variables instead:

```env
APP_NAME=MaxBridge
ENVIRONMENT=production
POSTGRES_DB=maxbridge
POSTGRES_USER=maxbridge
POSTGRES_PASSWORD=change-me
PUBLIC_BASE_URL=https://maxbridge.app
TELEGRAM_BOT_USERNAME=MaxBridgeBot
TELEGRAM_BOT_TOKEN=000000:replace-me
MAX_MESSAGE_LENGTH=4000
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_MESSAGES=20
```

If an old `.env` contains `DATABASE_URL=...`, remove that line before deploying this compose file.

## Local Run

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`.

## Server Fix For DNS Error

If the API logs contain:

```text
socket.gaierror: [Errno -2] Name or service not known
```

then the API container cannot resolve the database hostname from `DATABASE_URL`.
With this compose file, redeploy with:

```bash
docker compose down
docker compose up --build -d
docker compose logs -f api
```

Check the final API environment:

```bash
docker compose exec api env | grep DATABASE_URL
```

Expected host inside the URL:

```text
@postgres:5432
```

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
