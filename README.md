# URL Shortener API (FastAPI)

Сервис сокращения ссылок(FastAPI)

## Стек

- FastAPI
- PostgreSQL
- Redis
- Docker / Docker Compose

## Запуск

Через Docker Compose

```bash
cd link_shorter_online
docker compose up --build
```

## Аутентификация

- Регистрация и логин открыты.
- Для изменения/удаления ссылки нужен заголовок x-token.
- GET и POST /links/shorten доступны всем.

## Формат даты для TTL

Поле expires_at передается в формате:
```
YYYY-MM-DD HH:MM
```
Пример: 2026-03-20 14:30

## API

1) Регистрация

```http
POST /register
```

```json
{
  "username": "alice",
  "password": "12345"
}
```

2) Логин

```http
POST /login
```

```json
{
  "username": "alice",
  "password": "12345"
}
```


Ответ:

```json
{
  "token": "uuid-token"
}
```


3) Создание короткой ссылки

```http
POST /links/shorten
```

```json
{
  "original_url": "https://example.com/very/long/path",
  "custom_alias": "my-alias",
  "expires_at": "2026-03-20 14:30"
}
```


custom_alias и expires_at опциональны.

Ответ:

```json
{
  "short_code": "my-alias",
  "short_url": "http://localhost:8000/links/my-alias"
}
```


4) Переход по короткой ссылке

GET /links/{short_code}

Возвращает redirect (307) на оригинальный URL.

5) Статистика ссылки

```http
GET /links/{short_code}/stats
```

Ответ:

```json
{
  "short_code": "my-alias",
  "original_url": "https://example.com/very/long/path",
  "created_at": "2026-03-18 10:00:00",
  "clicks": 3,
  "last_used_at": "2026-03-18 11:20:00"
}
```


6) Поиск по оригинальному URL

GET /links/search?original_url=https://example.com/very/long/path

7) Обновление ссылки

PUT /links/{short_code}

Заголовок: x-token: <token>

```json
{
  "original_url": "https://example.com/new/path"
}
```


8) Удаление ссылки

DELETE /links/{short_code}

Заголовок: x-token: <token>

9) Дополнительно: очистка неиспользуемых ссылок

```http
POST /admin/cleanup-unused?days=30
```

10) Дополнительно: история истекших ссылок

```http
GET /links/expired-history?limit=50
```
