# ФинМетрика

**ФинМетрика** — MVP веб-приложения для управления личными финансами: учёт счетов, доходов, расходов, лимитов, целей, аналитика бюджета и AI-рекомендации на основе локальной модели Ollama.

## Что реализовано

- Регистрация и авторизация пользователей через JWT.
- Dashboard с балансом, доходами, расходами и профицитом.
- Учёт счетов, операций, категорий, лимитов и финансовых целей.
- Фильтрация операций по периодам: сегодня, неделя, месяц, все.
- Визуализация расходов: круговая диаграмма, прогресс-бары по категориям и лимитам.
- Виджет финансового состояния с оценкой 0–100.
- Профиль инвестора: возраст, стабильность дохода, уверенность в работе, терпимость к риску, опыт, горизонт инвестирования, финансовая подушка и предпочтительные активы.
- AI-финансовый помощник через Ollama `llama3.2:3b`.
- Backend-анализ финансов: профицит, доля накоплений, превышенные лимиты, риск-факторы, допустимые диапазоны распределения активов.
- React frontend с вкладками: Dashboard, Бюджет, AI, Профиль.
- Скрипт заполнения демо-данными.

## Стек

**Backend:** FastAPI, SQLModel, SQLAlchemy, Alembic, PostgreSQL, Redis, JWT, httpx  
**Frontend:** React, Vite, Axios, CSS  
**AI:** Ollama + `llama3.2:3b`  
**Инфраструктура:** Docker Compose

## Требования

На компьютере должны быть установлены:

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Git
- Ollama

Проверка:

```bash
python --version
node --version
npm --version
docker --version
```

## Установка проекта

```bash
git clone https://github.com/Sap-Artem/finmetrica-backend.git
cd finmetrica-backend
```

## Настройка backend

Создать виртуальное окружение:

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Файл `.env`

Создай файл `.env` в корне проекта:

```env
POSTGRES_USER=finmetrica_user
POSTGRES_PASSWORD=finmetrica_password
POSTGRES_DB=finmetrica_db
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

DATABASE_URL=postgresql+asyncpg://finmetrica_user:finmetrica_password@127.0.0.1:5432/finmetrica_db

REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=dev-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

## Запуск PostgreSQL и Redis

```bash
docker compose up -d
```

Проверка:

```bash
docker ps
```

Должны быть запущены контейнеры PostgreSQL и Redis.

## Миграции базы данных

```bash
alembic upgrade head
```

## Установка Ollama и модели

Установить Ollama: https://ollama.com

Загрузить модель:

```bash
ollama pull llama3.2:3b
```

Проверить, что Ollama работает:

```bash
ollama list
```

Также можно открыть в браузере:

```text
http://127.0.0.1:11434
```

Должно появиться сообщение:

```text
Ollama is running
```

Важно: модель Ollama не хранится в GitHub. Каждый разработчик должен скачать её отдельно командой `ollama pull llama3.2:3b`.

## Запуск backend

```bash
python -m uvicorn api_gateway.main:app --reload
```

Swagger будет доступен по адресу:

```text
http://127.0.0.1:8000/docs
```

## Запуск frontend

В отдельном терминале:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Открыть приложение:

```text
http://127.0.0.1:5173
```

## Демо-данные

После регистрации пользователя можно заполнить тестовые данные:

```bash
python scripts/seed_demo_data.py
```

Скрипт создаёт демонстрационные счета, доходы, расходы, лимиты, цели и профиль для тестового пользователя.

По умолчанию используется пользователь:

```text
username: testuser2
password: 12345678
```

Если база была очищена, сначала зарегистрируй пользователя через frontend или Swagger.

## Стандартный порядок запуска

Каждый раз после перезагрузки компьютера:

1. Запустить Docker Desktop.
2. Поднять PostgreSQL и Redis:

```bash
docker compose up -d
```

3. Запустить backend:

```bash
python -m uvicorn api_gateway.main:app --reload
```

4. Запустить frontend:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

5. Убедиться, что Ollama запущена:

```bash
ollama list
```

## Основные URL

```text
Frontend: http://127.0.0.1:5173
Backend API: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
Ollama: http://127.0.0.1:11434
```

## Примечания

- `.env`, `.venv`, `frontend/node_modules` и временные файлы не должны попадать в Git.
- Если AI-рекомендация не генерируется, проверь, что Ollama запущена и модель `llama3.2:3b` скачана.
- Если frontend не открывается по `localhost`, используй `http://127.0.0.1:5173`.
- Если порты заняты, проверь процессы через `netstat` или перезапусти Docker/Desktop терминалы.

## Статус проекта

Проект находится в состоянии MVP: базовая бизнес-логика, frontend, AI-рекомендации, финансовая аналитика и профиль инвестора реализованы. Для промышленного использования дополнительно потребуются деплой, безопасность production-уровня, резервное копирование, расширенные тесты и настройка CI/CD.
