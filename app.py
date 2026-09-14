import os
from datetime import datetime
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Раздел I. Пункт 3: Сборка строки подключения из переменных окружения
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = os.environ.get("POSTGRES_HOST", "db")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB")

# Формируем строку строго по методичке с отключением SSL-проверок внутри Docker
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=disable"
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Раздел I. Пункт 4: Описание модели Visit
class Visit(db.Model):
    __tablename__ = 'visits'
    id = db.Column(db.Integer, primary_key=True)
    visit_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    client_ip = db.Column(db.String(45), nullable=False)

# Раздел I. Пункт 5: Настройка создания таблицы при старте приложения
with app.app_context():
    db.create_all()

# Раздел I. Пункт 6: Маршрут GET /hello
@app.route('/hello', methods=['GET'])
def hello():
    current_time = datetime.utcnow()
    client_ip = request.remote_addr
    
    new_visit = Visit(visit_time=current_time, client_ip=client_ip)
    db.session.add(new_visit)
    db.session.commit()
    
    return "Hello", 200
