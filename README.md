# URL Shortener API (FastAPI)

Сервис сокращения ссылок (FastAPI)

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
- Если пригодится потом обновлять/удалять ссылку, при создании надо передать заголовок token: <token>, чтобы ссылка привязалась к пользователю

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

```bash
curl -X POST "https://link-shorter-tirh.onrender.com/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"12345"}'
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

```bash
curl -X POST "https://link-shorter-tirh.onrender.com/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"12345"}'
```



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

```bash
curl -X POST "https://link-shorter-tirh.onrender.com/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url":"https://example.com/very/long/path","custom_alias":"my-alias","expires_at":"2026-03-20 14:30"}'
```


custom_alias и expires_at опциональны.

Ответ:

```json
{
  "short_code": "my-alias",
  "short_url": "https://link-shorter-tirh.onrender.com/links/my-alias"
}
```


4) Переход по короткой ссылке

GET /links/{short_code}

Возвращает redirect (307) на оригинальный URL.

```bash
curl -i "https://link-shorter-tirh.onrender.com/links/my-aliass"
```

5) Статистика ссылки

```http
GET /links/{short_code}/stats
```

```bash
curl "https://link-shorter-tirh.onrender.com/links/my-alias/stats"
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

```http
GET /links/search?original_url=https://example.com/very/long/path
```

```bash
curl -G "https://link-shorter-tirh.onrender.com/links/search" \
  --data-urlencode "original_url=https://ru.wikipedia.org/wiki/Боуи,_Дэвид"
```


7) Обновление ссылки

```http
PUT /links/{short_code}
```

Заголовок: x-token: <token>

```json
{
  "original_url": "https://example.com/new/path"
}
```

```bash
curl -X PUT "https://link-shorter-tirh.onrender.com/links/my-alias" \
  -H "Content-Type: application/json" \
  -H "x-token: <token>" \
  -d '{"original_url":"https://ru.wikipedia.org/wiki/Боуи,_Дэвид"}'
```

8) Удаление ссылки

```http
DELETE /links/{short_code}
```

Заголовок: x-token: <token>

```bash
curl -X DELETE "https://link-shorter-tirh.onrender.com/links/my-alias" \
  -H "x-token: <token>"
```

9) Дополнительно: очистка неиспользуемых ссылок

```http
POST /admin/cleanup-unused?days=30
```

```bash
curl -X POST "https://link-shorter-tirh.onrender.com/admin/cleanup-unused?days=30"
```

10) Дополнительно: история истекших ссылок

```http
GET /admin/expired-history?limit=50
```

```bash
curl "https://link-shorter-tirh.onrender.com/admin/expired-history?limit=50"
```

## Тесты (ДЗ4)

```bash
pytest tests -q

#Покрытие:

coverage run -m pytest tests
coverage report -m
coverage html
```

HTML-отчет будет в htmlcov/index.html

## Нагрузочное тестирование вместе с Locust

Файл locustfile.py

```bash
locust -f locustfile.py --host https://link-shorter-tirh.onrender.com
```

Дальше открыть UI Locust: `http://localhost:8089'
