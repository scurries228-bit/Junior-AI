# Junior AI

Умный AI-ассистент с регистрацией, математикой, геометрией, диаграммами.

## Деплой на Render

### Шаг 1 — Залить на GitHub
1. Создай репозиторий на GitHub
2. Загрузи все файлы из этого ZIP

### Шаг 2 — Render
1. Зайди на [render.com](https://render.com)
2. New → Web Service → подключи GitHub репо
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`

### Шаг 3 — ENV переменные (в Render → Environment)
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxx    ← ОБЯЗАТЕЛЬНО
SECRET_KEY=любая-случайная-строка   ← ОБЯЗАТЕЛЬНО
DATABASE_URL=                        ← автоматически от Render Postgres
BRAVE_API_KEY=                       ← опционально (для поиска картинок)
```

### База данных
- Render → New → PostgreSQL → создай бесплатную базу
- Скопируй `Internal Database URL` в переменную `DATABASE_URL`

### Локальный запуск
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
# открой http://localhost:5000
```

## Возможности
- ✅ Регистрация и вход пользователей
- ✅ История чатов (сохраняется в БД)
- ✅ Математика: дроби, степени, корни, знаки
- ✅ Геометрия: SVG рисунки прямо в чате
- ✅ Диаграммы: bar, line, pie, doughnut
- ✅ Поиск картинок (с Brave API)
- ✅ Реакция на мат с юмором
- ✅ Тёмный дизайн с фиолетовым акцентом
