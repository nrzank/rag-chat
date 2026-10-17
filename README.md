# RAG Chat

Чат-бот с поиском по собственным документам. Загружаешь PDF, DOCX или TXT —
система разбивает их на фрагменты, строит эмбеддинги, кладёт в векторную базу.
Дальше задаёшь вопрос на естественном языке и получаешь ответ потоком,
со ссылками на фрагменты, из которых он собран.

Пет-проект. Цель — собрать production-подобный RAG-сервис целиком:
от загрузки файла до стриминга ответа, со слоистой архитектурой,
миграциями, типизированными ошибками и тестами.

## Возможности

- Загрузка и парсинг PDF, DOCX, TXT
- Нарезка текста на фрагменты с перекрытием
- Генерация эмбеддингов пакетами (OpenAI)
- Векторный поиск через Qdrant с фильтром по документам
- Ответы LLM потоком через Server-Sent Events
- История диалогов с сохранением источников каждого ответа
- Идемпотентная переиндексация: повторная обработка не плодит дубли

## Стек

| Слой | Технологии |
|---|---|
| API | FastAPI, Pydantic v2, sse-starlette |
| Данные | PostgreSQL 17, SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Вектора | Qdrant |
| LLM | OpenAI SDK — gpt-4o-mini, text-embedding-3-small |
| Парсинг | pypdf, python-docx |
| Инструменты | uv, ruff, pytest, Hypothesis, Docker Compose |

## Быстрый старт

Нужен Docker и [uv](https://docs.astral.sh/uv/).

1. Создай `.env` в корне и в `backend/`:

```bash
cp .env.example backend/.env
```

Пропиши в `backend/.env` свой `OPENAI_API_KEY`. Для Docker Compose нужен ещё
`.env` в корне с той же переменной.

2. Подними инфраструктуру:

```bash
docker compose up -d db qdrant
```

3. Накати миграции:

```bash
cd backend && uv run alembic upgrade head
```

4. Запусти API:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8001
```

Swagger — http://localhost:8001/docs

Либо всё в контейнерах:

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

## API

| Метод | Путь | Что делает |
|---|---|---|
| `POST` | `/api/v1/documents/` | Загрузить файл |
| `POST` | `/api/v1/documents/{id}/process` | Распарсить, нарезать, проиндексировать |
| `GET` | `/api/v1/documents/` | Список документов |
| `GET` | `/api/v1/documents/{id}` | Документ по id |
| `DELETE` | `/api/v1/documents/{id}` | Удалить документ, фрагменты и вектора |
| `POST` | `/api/v1/conversations/` | Создать диалог |
| `GET` | `/api/v1/conversations/` | Список диалогов |
| `GET` | `/api/v1/conversations/{id}` | Диалог с историей сообщений |
| `DELETE` | `/api/v1/conversations/{id}` | Удалить диалог |
| `POST` | `/api/v1/conversations/{id}/ask` | Задать вопрос, ответ потоком (SSE) |

### Поток ответа

`POST /conversations/{id}/ask` возвращает SSE-поток из трёх типов событий:

```
event: sources
data: {"sources": [{"document_id": 1, "chunk_index": 4, "score": 0.82}]}

event: token
data: {"text": "Согласно "}

event: done
data: {"message_id": 17}
```

Источники приходят до первого токена — интерфейс показывает, по каким
документам строится ответ, пока модель ещё генерирует. При ошибке приходит
событие `error` с телом `{code, message, params}`.

### Ошибки

Единый формат на все эндпоинты:

```json
{"code": "document_not_found", "message": "Document not found", "params": {"document_id": 999}}
```

`code` стабилен и предназначен для клиента, `params` — структурированные
данные для подстановки в локализованное сообщение.

## Архитектура

Слои и направление зависимостей описаны в [AGENTS.md](AGENTS.md).
Предметная область и инварианты — в [docs/CONTEXT.md](docs/CONTEXT.md).
Текущее состояние работ — в [docs/STATUS.md](docs/STATUS.md).

```
backend/
├── api/              # HTTP: роутеры, зависимости, обработчики ошибок
│   └── v1/
├── app/              # Домен и бизнес-логика
│   ├── base/         # Типизированные исключения
│   ├── chat/         # Диалоги, RAG-поиск, стриминг
│   └── documents/    # Загрузка, парсинг, чанкинг, индексация
├── core/             # Инфраструктура: конфиг, БД, Qdrant, OpenAI
├── migrations/       # Alembic
└── tests/
```

Каждый домен в `app/` устроен одинаково:

| Файл | Назначение |
|---|---|
| `models.py` | Доменные сущности — dataclass, без зависимостей от фреймворков |
| `db_models.py` | ORM-модели SQLAlchemy |
| `repository.py` | Протоколы хранилищ |
| `repository_impl.py` | Реализация протоколов на SQLAlchemy |
| `ports.py` | Протоколы внешних сервисов (эмбеддер, вектора, LLM) |
| `service.py` | Сценарии использования |
| `schemas.py` | Pydantic DTO для API |

## Разработка

```bash
cd backend
uv run ruff check .      # линтер
uv run ruff format .     # форматтер
uv run pytest -q         # тесты
```

Новая миграция:

```bash
cd backend && uv run alembic revision --autogenerate -m "описание"
```

## Тесты

Юнит-тестов на детали реализации нет намеренно. Есть два вида:

- **Property-based** (Hypothesis) на чанкер — проверяют свойства для любых
  входных данных. Так был найден вечный цикл при `chunk_overlap >= chunk_size`.
- **Функциональные** на сервисы — полный сценарий через фейковые реализации
  протоколов, без базы, Qdrant и сети.
