# Агрегатор поиска авиаперелётов (ЛР №4, синхронная версия)
docker compose up --build -d          # БД, загрузка рейсов, 3 заглушки, сервис поиска
curl "localhost:8000/search?origin=OVB&destination=LED&date=2026-12-10"
pip install httpx && python loadtest/loadtest.py --mode closed --clients 10
python loadtest/loadtest.py --mode open --rate 5
docker compose exec search py-spy record --pid 1 -d 60 -f flamegraph -o /profiles/sync_no_idle.svg
docker compose exec search py-spy record --pid 1 -d 60 -f flamegraph --idle -o /profiles/sync_idle.svg
python analysis/estimate.py            # оценка времени ответа (раздел II)
# версии раздела IV:  APP_MODULE=app.main_v41:app docker compose up -d --force-recreate search
#                     APP_MODULE=app.main_v42:app docker compose up -d --force-recreate search
docker compose exec search py-spy dump --pid 1     # задача 4.1
