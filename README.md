# telegram-link-downloader

Телеграм-бот для скачивания ссылок с подключаемыми провайдерами. Сейчас реализован YouTube (shorts/watch/youtu.be).

## Архитектура

- `tg_bot` — aiogram v3, принимает сообщения, детектит провайдер и кладёт Job в RQ.
- `worker` — RQ worker, выполняет Job и отправляет результат пользователю.
- `shared` — общий код: router, providers, модели Job.

## Локальный запуск (без Docker)

1. Установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Запустите Redis:

```bash
docker run --rm -p 6379:6379 redis:7
```

3. Экспортируйте переменные окружения:

```bash
export BOT_TOKEN="<telegram_token>"
export REDIS_URL="redis://localhost:6379/0"
export RQ_QUEUE="downloads"
export DATA_DIR="/tmp/tgb-data"
```

4. Запустите воркер:

```bash
python -m worker.main
```

5. Запустите бота:

```bash
python -m tg_bot.main
```

## Docker Compose (опционально)

```yaml
version: "3.9"
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  bot:
    build: .
    command: python -m tg_bot.main
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      REDIS_URL: redis://redis:6379/0
      RQ_QUEUE: downloads
    depends_on:
      - redis
  worker:
    build: .
    command: python -m worker.main
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      REDIS_URL: redis://redis:6379/0
      RQ_QUEUE: downloads
      DATA_DIR: /data
    volumes:
      - ./data:/data
    depends_on:
      - redis
```

## Деплой в Kubernetes

1. Соберите образы (бот и воркер могут быть разными):

```bash
docker build -t registry.example.com/tgb-bot:latest -f Dockerfile.bot .
docker build -t registry.example.com/tgb-worker:latest -f Dockerfile.worker .
```

2. Задеплойте манифесты:

```bash
kubectl apply -f deploy/
```

3. Обновите `deploy/secret.yaml` с токеном бота.

## Как добавить нового провайдера

1. Создайте класс провайдера в `shared/providers/<provider>.py`.
2. Реализуйте методы `match`, `extract_url`, `normalize`, `build_job`.
3. Зарегистрируйте провайдера через `@register`.
4. Добавьте обработчик в `worker/handlers/<provider>.py` и подключите его в `worker/tasks.py`.

Пример заглушки для VK есть в `shared/providers/vk.py`.
