# VK AI Assistant

Интеллектуальный AI-помощник во ВКонтакте на Python: **VKBottle** + **Google GenAI SDK** + **Gemini через ProxyAPI.ru**, память в JSON, несколько диалогов и роли общения.

## Возможности

### Чат и AI
- Ответы модели **Gemini** через ProxyAPI (официальный Google GenAI SDK, endpoint `/v1beta`)
- `system` / `user` / `assistant` контекст, история активного диалога
- Централизованный `AIProvider` + `GeminiAIService` (модель меняется в `.env`)
- Обработка ошибок API, retry, fallback-текст пользователю
- Явный лог, если модель не поддерживается ProxyAPI (`Model not supported`)

### Память (JSON)
- Отдельный файл `users/<user_id>.json` на каждого пользователя
- Хранится: `user_id`, диалоги, активный диалог, настройки, история
- До **100** последних сообщений; при переполнении — авто-резюме старых
- У сообщения: `role`, `content`, `timestamp` (+ флаг резюме)

### Многодиалоговый режим
- Несколько независимых диалогов
- Создание, список, переключение, переименование, удаление
- При смене диалога меняются история и system prompt (роль)

### Режимы общения (5 ролей)
| Режим | Описание |
| --- | --- |
| Обычный помощник | Универсальные ответы |
| Программист | Код, архитектура, отладка |
| Преподаватель | Пошаговые объяснения |
| Бизнес-консультант | Стратегия, риски, следующие шаги |
| Дружелюбный собеседник | Неформальный тон |

Роль задаётся **на текущий диалог**.

### Интерфейс VK
Главное меню:
- Новый диалог
- Список диалогов
- Сменить режим
- Настройки
- Помощь

В списке диалогов: переключение, переименование, удаление.  
В настройках: выбор режима, инфо о модели, очистка истории.

### UX
- Статус «⏳ Бот думает...»
- Индикатор **«печатает…»** (`messages.setActivity`, с `group_id`, обновление каждые ~4 с)
- Markdown LLM → форматирование VK (`**жирный**`, `*курсив*`, ссылки) через `format_data`
- Ограничение длины сообщений, защита от пустых
- Ответы длиннее лимита VK режутся на части

### Отправка файлов
Если попросить файл, бот пришлёт **документ-вложение**:
- «сделай файл `notes.txt` с планом»
- «пришли скрипт `hello.py` файлом»

Поддерживаются текстовые расширения: `txt`, `md`, `py`, `js`, `ts`, `json`, `csv`, `html`, `css`, `sql`, `xml`, `yaml`, `yml`, `toml`, `ini`, `log`, `sh`, `bat`, `ps1`.

## Архитектура

```
VK message / callback
        │
        ▼
  bot/handlers  ──────────►  keyboards/
        │
        ▼
  services/chat_service
        │
   ┌────┼────────────┐
   ▼    ▼            ▼
dialog memory   document_service
service service        │
   │    │              ▼ (в handler)
   │    └──► AIProvider  DocMessagesUploader → VK
   │            │
   ▼            ▼
JsonUserStorage  ProxyAPI → Gemini
   │
   ▼
users/<id>.json
```

AI и VK не смешаны: генерация и разбор файлов — в `services/`, загрузка в VK — в хендлерах.

### Структура проекта

| Путь | Назначение |
| --- | --- |
| `bot.py` | Точка входа |
| `bot/` | Приложение, DI-контейнер, хендлеры сообщений и callback |
| `services/` | Диалоги, память, чат, подготовка файлов |
| `services/ai/` | Абстракция LLM + Gemini через ProxyAPI |
| `storage/` | Асинхронное JSON-хранилище |
| `models/` | Pydantic-сущности (`UserState`, `Dialog`, `ChatMessage`, `GeneratedFile`) |
| `keyboards/` | Клавиатуры и тексты меню (RU) |
| `config/` | Settings из `.env`, system prompts ролей |
| `utils/` | Логирование, Markdown→VK, парсинг файловых блоков |
| `users/` | JSON-состояния пользователей |
| `.env` / `.env.example` | Секреты и лимиты |
| `requirements.txt` | Зависимости |

## Быстрый старт

```powershell
cd "C:\Users\bkv73\Desktop\Вайбкодинг\Внедрение ИИ\VPf09"
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# заполните VK_API_TOKEN и PROXY_API_KEY
python bot.py
```

### Настройки сообщества VK
1. Сообщения сообщества включены
2. Long Poll API (или Bots Long Poll)
3. Права токена: сообщения, документы (для отправки файлов)

## Конфигурация (`.env`)

```env
VK_API_TOKEN=vk1.a.xxxxxxxx
PROXY_API_KEY=sk-xxxxxxxx

PROXY_GEMINI_BASE_URL=https://api.proxyapi.ru
PROXY_GEMINI_API_VERSION=v1beta
GEMINI_MODEL=gemini-3.5-flash

MAX_HISTORY_MESSAGES=100
MAX_USER_MESSAGE_LENGTH=3500
MAX_VK_MESSAGE_LENGTH=4000
AI_TIMEOUT_SECONDS=60
SUMMARY_BATCH_SIZE=40
LOG_LEVEL=INFO
```

- Модель для Gemini-формата — **без** префикса `google/` (например `gemini-3.5-flash`, `gemini-4-hydrogen`).
- Актуальный список: [proxyapi.ru/models/google](https://proxyapi.ru/models/google).
- Если в логе `Модель не поддерживается` — смените `GEMINI_MODEL`.

## Пример запроса к пользователю

1. Написать боту «Начать» → меню  
2. Выбрать режим «Программист»  
3. Спросить вопрос или: `сделай файл hello.py с примером print`  
4. Получить текст в чате + файл-вложение  

## Масштабирование

1. Заменить `JsonUserStorage` на Redis/S3/DB, сохранив интерфейс.
2. Добавить другой провайдер рядом с `GeminiAIService` через `create_ai_service`.
3. Перейти на Callback API и несколько воркеров.
4. Очередь (Arq/RQ) для долгих AI-запросов.
5. Rate limit по `user_id` в `ChatService`.

## Стек

- Python 3.10+
- VKBottle
- google-genai
- pydantic / pydantic-settings
- aiofiles, tenacity
