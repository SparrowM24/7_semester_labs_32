import os
from datetime import datetime

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

missing = [
    name
    for name, value in {
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_HOST": DB_HOST,
        "DB_NAME": DB_NAME,
    }.items()
    if not value
]

if missing:
    raise RuntimeError(
        f"Не заданы переменные окружения: {', '.join(missing)}"
    )

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Visit(db.Model):
    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    visited_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=False)

    def __repr__(self):
        return f"<Visit {self.id} {self.ip_address} {self.visited_at}>"


with app.app_context():
    db.create_all()


@app.get("/hello")
def hello():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    visit = Visit(
        visited_at=datetime.utcnow(),
        ip_address=ip or "unknown",
    )

    db.session.add(visit)
    db.session.commit()

    return "Hello", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

    