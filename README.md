# DeepAI local shim (with Docker)

Тонкая прослойка: снаружи обычный OpenAI API, внутри — запросы к `api2.deepai.org`
с вашим `Api-Key`. Работает и напрямую через Python, и в Docker.

Слушает `http://127.0.0.1:9100/v1`, наружу не выходит.

## Что нужно

- `Api-Key` вашего аккаунта DeepAI (строка-uuid)
- либо Python 3, либо Docker

Ключ выдаётся аккаунту DeepAI и используется только для ваших собственных запросов.
Таблицы аккаунтов, регистрация, пулы ключей — не входят в этот проект и не поддерживаются.

## Вариант 1: Docker

```bash
echo "DEEPAI_API_KEY=<ваш ключ>" > .env
docker compose up -d --build
```

Проверка:

```bash
curl -s http://127.0.0.1:9100/v1/models
```

Остановить: `docker compose down`.

Без compose:

```bash
docker build -t deepai-shim .
docker run -d --name deepai-shim -p 127.0.0.1:9100:9100 \
  -e DEEPAI_API_KEY=<ваш ключ> deepai-shim
```

## Вариант 2: Python (Windows / Linux / macOS)

Зависимостей нет, только стандартная библиотека.

```bash
set DEEPAI_API_KEY=<ваш ключ>          # Windows
export DEEPAI_API_KEY=<ваш ключ>       # Linux / macOS
python deepai-shim.py 9100
```

На Windows проще двойным кликом по `start.bat` — он один раз спросит ключ и запомнит его
в `deepai-key.txt` рядом с собой.

## Подключение

**OpenCode** (`opencode.json`):

```json
"provider": {
  "deepai-local": {
    "npm": "@ai-sdk/openai-compatible",
    "options": { "baseURL": "http://127.0.0.1:9100/v1", "apiKey": "sk-local" },
    "models": { "glm-5.3-flash": { "name": "GLM 5.3 Flash", "reasoning": true } }
  }
}
```

**Python:**

```python
from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:9100/v1", api_key="sk-local")
r = c.chat.completions.create(model="glm-5.3-flash",
                              messages=[{"role": "user", "content": "привет"}])
print(r.choices[0].message.content)
```

`apiKey` — любая непустая строка: шим её не проверяет, настоящий ключ подставляет сам.

## Что поддерживается

- список моделей в `GET /v1/models` (OpenAI-формат)
- стриминг SSE в реальном времени
- thinking: `reasoning` дублируется в `reasoning_content`
- параллельные запросы (поток на соединение)
- `stream: false`

## Переменные окружения

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `DEEPAI_API_KEY` | — | ваш ключ (обязательно) |
| `DEEPAI_SHIM_BIND` | `127.0.0.1` | адрес прослушивания; в Docker нужен `0.0.0.0` |

## Ограничения

- только один ключ, заданный в окружении; пула аккаунтов нет
- лимиты и квоты DeepAI — на их стороне, шим их не обходит
- логи (`deepai-shim.log`) содержат только модель, `stream` и тайминги, без заголовков

## Если что-то не так

| Симптом | Причина |
|---|---|
| `connection refused` | шим не запущен |
| `401` | ключ неверный или отозван |
| порт занят | запущен другой экземпляр |
| модель не находится | взять id из `GET /v1/models` |

## Файлы

| Файл | Что это |
|---|---|
| `deepai-shim.py` | сам шим, Python 3, без зависимостей |
| `start.bat` | запуск на Windows, спрашивает и запоминает ключ |
| `Dockerfile` / `docker-compose.yml` | запуск в контейнере |
