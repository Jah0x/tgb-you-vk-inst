# telegram-link-downloader

Телеграм-бот для скачивания ссылок с подключаемыми провайдерами. Сейчас реализованы YouTube (shorts/watch/youtu.be), Instagram Reels и VK (vk.com/vk.ru).

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
export INSTAGRAM_COOKIES_PATH="/tmp/instagram-cookies.txt"
export VK_COOKIES_PATH="/tmp/vk-cookies.txt"
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
      INSTAGRAM_COOKIES_PATH: /data/instagram-cookies.txt
      VK_COOKIES_PATH: /data/vk-cookies.txt
    volumes:
      - ./data:/data
      - ./secrets/instagram-cookies.txt:/data/instagram-cookies.txt:ro
      - ./secrets/vk-cookies.txt:/data/vk-cookies.txt:ro
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

VK-провайдер работает через `yt-dlp`, поэтому поддерживает видео/клипы по прямым ссылкам.

## Instagram Reels: cookies

Для приватных аккаунтов или частых ошибок доступа Instagram может потребоваться авторизация через cookies.

1. Войдите в Instagram в браузере.
2. Экспортируйте cookies в формате Netscape.
   - Например, расширением "Get cookies.txt" (Chrome) или "cookies.txt" (Firefox).
3. Сохраните файл, например в `./secrets/instagram-cookies.txt`.
4. Укажите путь до файла через переменную окружения:

```bash
export INSTAGRAM_COOKIES_PATH="/abs/path/to/instagram-cookies.txt"
```

5. В Docker убедитесь, что файл примонтирован внутрь контейнера (пример выше в Compose).

Если переменная `INSTAGRAM_COOKIES_PATH` не задана, загрузка Reels будет пытаться работать без cookies.

## VK: cookies

Для приватных видео или ограничений VK можно использовать cookies.

1. Войдите в VK в браузере.
2. Экспортируйте cookies в формате Netscape.
3. Сохраните файл, например в `./secrets/vk-cookies.txt`.
4. Укажите путь до файла через переменную окружения:

```bash
export VK_COOKIES_PATH="/abs/path/to/vk-cookies.txt"
```

5. В Docker убедитесь, что файл примонтирован внутрь контейнера (пример выше в Compose).

Если переменная `VK_COOKIES_PATH` не задана, загрузка будет пытаться работать без cookies.
