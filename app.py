from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
import os
import json
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "junior-ai-secret-2024")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    messages_count = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), default="Новый чат")
    messages = db.Column(db.Text, default="[]")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


with app.app_context():
    db.create_all()


SYSTEM_PROMPT = """Ты — Junior AI, молодой и умный ИИ-ассистент. Ты общаешься живо, как реальный человек.

МАТЕМАТИКА:
- Решаешь примеры с дробными чертами (используй формат: числитель/знаменатель или красиво показывай), квадратами (x²), кубами (x³), корнями (√), знаками ±, ≤, ≥, ≠, ∞ и т.д.
- Показывай КАЖДЫЙ шаг решения
- Используй правильные математические обозначения
- Проверяй знаки (+, -, ×, ÷) очень внимательно

ГЕОМЕТРИЯ И ВИЗУАЛИЗАЦИЯ:
- Рисуй геометрические фигуры используя SVG в HTML тегах внутри ответа
- Создавай диаграммы используя Chart.js разметку в JSON формате
- Добавляй цвет в рисунки
- Формат SVG рисунка: <SVG_FIGURE>...svg код...</SVG_FIGURE>
- Формат диаграммы: <CHART_DATA>{"type":"bar","labels":[...],"datasets":[...],"title":"..."}</CHART_DATA>

ПОИСК КАРТИНОК:
- Когда нужна картинка, возвращай: <IMAGE_SEARCH>запрос для поиска</IMAGE_SEARCH>

ОБЪЯСНЕНИЯ:
- Объясняй популярно и по делу — без воды
- Используй примеры из реальной жизни
- Структурируй через списки и заголовки когда нужно

МАТ:
- Если пользователь матерится — реагируй с юмором и характером, но продолжай выполнять задачу
- Не обижайся, не читай мораль — ты живой персонаж

СТИЛЬ:
- Живой, дружелюбный тон
- Можешь шутить уместно
- Не говори "как языковая модель" — ты просто Junior AI
- Отвечай на том языке на котором пишет пользователь"""


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.json
        user = User.query.filter_by(email=data["email"]).first()
        if user and user.check_password(data["password"]):
            session["user_id"] = user.id
            session["username"] = user.username
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Неверный email или пароль"})
    return render_template("auth.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"ok": False, "error": "Email уже занят"})
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"ok": False, "error": "Имя пользователя уже занято"})
    user = User(username=data["username"], email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"error": "Не авторизован"}), 401

    data = request.json
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")

    import httpx
client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client())

    formatted = [{"role": m["role"], "content": m["content"]} for m in messages]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=4096,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + formatted,
    )

    reply = response.choices[0].message.content

    user = User.query.get(session["user_id"])
    user.messages_count += 1
    db.session.commit()

    if conversation_id:
        conv = Conversation.query.get(conversation_id)
        if conv and conv.user_id == session["user_id"]:
            msgs = json.loads(conv.messages)
            msgs.append({"role": "assistant", "content": reply})
            conv.messages = json.dumps(msgs, ensure_ascii=False)
            if len(msgs) == 2:
                user_msg = messages[0]["content"][:50] if messages else "Чат"
                conv.title = user_msg
            db.session.commit()

    return jsonify({"reply": reply})


@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    if "user_id" not in session:
        return jsonify([])
    convs = (
        Conversation.query.filter_by(user_id=session["user_id"])
        .order_by(Conversation.created_at.desc())
        .limit(30)
        .all()
    )
    return jsonify(
        [{"id": c.id, "title": c.title, "created_at": str(c.created_at)} for c in convs]
    )


@app.route("/api/conversations", methods=["POST"])
def new_conversation():
    if "user_id" not in session:
        return jsonify({"error": "Не авторизован"}), 401
    conv = Conversation(user_id=session["user_id"])
    db.session.add(conv)
    db.session.commit()
    return jsonify({"id": conv.id, "title": conv.title})


@app.route("/api/conversations/<int:cid>", methods=["GET"])
def get_conversation(cid):
    if "user_id" not in session:
        return jsonify({"error": "Не авторизован"}), 401
    conv = Conversation.query.filter_by(id=cid, user_id=session["user_id"]).first()
    if not conv:
        return jsonify({"error": "Не найдено"}), 404
    return jsonify({"id": conv.id, "title": conv.title, "messages": json.loads(conv.messages)})


@app.route("/api/conversations/<int:cid>/message", methods=["POST"])
def add_message(cid):
    if "user_id" not in session:
        return jsonify({"error": "Не авторизован"}), 401
    conv = Conversation.query.filter_by(id=cid, user_id=session["user_id"]).first()
    if not conv:
        return jsonify({"error": "Не найдено"}), 404
    data = request.json
    msgs = json.loads(conv.messages)
    msgs.append({"role": data["role"], "content": data["content"]})
    conv.messages = json.dumps(msgs, ensure_ascii=False)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/user")
def get_user():
    if "user_id" not in session:
        return jsonify({"error": "Не авторизован"}), 401
    user = User.query.get(session["user_id"])
    return jsonify({"username": user.username, "email": user.email, "messages_count": user.messages_count})


@app.route("/api/images")
def image_search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"images": []})

    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if brave_key:
        try:
            r = requests.get(
                "https://api.search.brave.com/res/v1/images/search",
                params={"q": q, "count": 4},
                headers={"Accept": "application/json", "X-Subscription-Token": brave_key},
                timeout=5
            )
            data = r.json()
            images = [item["thumbnail"]["src"] for item in data.get("results", [])[:4]]
            return jsonify({"images": images})
        except Exception:
            pass

    return jsonify({"images": []})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
