import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Шаг 3: Сборка строки подключения из переменных окружения
DB_USER = os.getenv("POSTGRES_USER", "app")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "visits_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Шаг 4: Описание модели Visit
class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    client_ip = db.Column(db.String(45), nullable=False)

# Шаг 5: Создание таблиц при старте приложения
with app.app_context():
    db.create_all()

# Шаг 6: Реализация маршрута GET /hello
@app.route('/hello', methods=['GET'])
def hello():
    # 1. Получаем текущее время
    current_time = datetime.utcnow()
    
    # 2. Получаем IP-адрес клиента (с учетом возможного проксирования в Docker)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # 3. Сохраняем запись в таблицу
    new_visit = Visit(visit_time=current_time, client_ip=client_ip)
    db.session.add(new_visit)
    db.session.commit()
    
    # 4. Возвращаем 200 OK с телом "Hello"
    return "Hello", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
