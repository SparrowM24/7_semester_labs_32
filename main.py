import os
from datetime import datetime
from flask import Flask, request, make_response
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Извлекаем готовую строку подключения из окружения (Пункт 3 задания)
DATABASE_URL = os.getenv("DATABASE_URL")

# Настройка движка SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Описание модели Visit (Пункт 4 задания)
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    visit_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    client_ip = Column(String, nullable=False)

app = Flask(__name__)

# Создание таблицы при старте приложения (Пункт 5 задания)
with app.app_context():
    Base.metadata.create_all(bind=engine)

# Реализация маршрута GET /hello (Пункт 6 задания)
@app.route('/hello', methods=['GET'])
def say_hello():
    current_time = datetime.utcnow()
    
    # Получаем IP-адрес клиента (с учетом прокси Codespaces)
    if request.headers.getlist("X-Forwarded-For"):
        client_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        client_ip = request.remote_addr or "127.0.0.1"

    # Сохраняем запись в таблицу Visit
    db = SessionLocal()
    try:
        new_visit = Visit(visit_time=current_time, client_ip=client_ip)
        db.add(new_visit)
        db.commit()
    except Exception as e:
        db.rollback()
        return make_response(f"Database error: {e}", 500)
    finally:
        db.close()

    return make_response("Hello", 200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
