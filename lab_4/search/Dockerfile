FROM python:3.12-slim
WORKDIR /app
COPY search/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY search/app /app/app
# один рабочий процесс; PID 1 = uvicorn, его профилирует py-spy
# APP_MODULE выбирает версию: app.main:app (синхронная), app.main_v41:app, app.main_v42:app
ENV APP_MODULE=app.main:app
CMD ["sh", "-c", "exec uvicorn $APP_MODULE --host 0.0.0.0 --port 8000 --workers 1"]
