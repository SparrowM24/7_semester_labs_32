import os
from datetime import datetime, timezone
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ─── Раздел I, п. 3: строка подключения собирается из переменных окружения ───
DB_USER = os.environ["POSTGRES_USER"]
DB_PASSWORD = os.environ["POSTGRES_PASSWORD"]
DB_HOST = os.environ["POSTGRES_HOST"]
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ["POSTGRES_DB"]

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ─── Раздел I, п. 4: модель Visit ───
class Visit(db.Model):
    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    visit_time = db.Column(db.DateTime(timezone=True), nullable=False)
    client_ip = db.Column(db.String(45), nullable=False)


# ─── Раздел I, п. 5: создание таблицы при старте приложения ───
with app.app_context():
    db.create_all()


# ─── Раздел I, п. 6: маршрут GET /hello ───
@app.route("/hello", methods=["GET"])
def hello():
    current_time = datetime.now(timezone.utc)
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    db.session.add(Visit(visit_time=current_time, client_ip=client_ip))
    db.session.commit()

    return "Hello", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)