import os
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from starlette.responses import StreamingResponse
import json

# --- Настройки ---
DATABASE_URL = os.getenv("DATABASE_URL")
TABLE_NAME = 'games'

# --- Инициализация приложения и БД ---
app = FastAPI(
    title="Steam Games API",
    description="API для получения данных об играх из Steam (с использованием PostgreSQL и потоковой передачи).",
    version="2.0.0"
)

if not DATABASE_URL:
    raise RuntimeError("Переменная окружения DATABASE_URL не установлена!")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Потоковый генератор ---
async def stream_games_from_db(db: Session, limit: int, offset: int):
    """
    Асинхронный генератор, который получает данные из БД порциями и отдает их
    в виде JSON-строк. Это позволяет избежать загрузки всего результата в память.
    """
    if limit:
        query = text(f"SELECT * FROM {TABLE_NAME} LIMIT :limit OFFSET :offset")
        params = {'limit': limit, 'offset': offset}
    else:
        query = text(f"SELECT * FROM {TABLE_NAME} OFFSET :offset")
        params = {'offset': offset}

    # Используем with для гарантии закрытия соединения
    with engine.connect() as connection:
        # Выполняем запрос с потоковой передачей результатов
        result = connection.execute(query, params)
        
        # Начинаем формирование JSON-массива
        yield '['
        
        first = True
        for row in result:
            # Преобразуем каждую строку в словарь
            row_dict = dict(row._mapping)
            
            # Заменяем Python-специфичные значения на JSON-совместимые
            for key, value in row_dict.items():
                if value is None or (isinstance(value, float) and (value != value or value == float('inf') or value == float('-inf'))):
                    row_dict[key] = None

            if not first:
                yield ','
            
            yield json.dumps(row_dict)
            first = False
        
        # Завершаем JSON-массив
        yield ']'

# --- Маршруты API (Endpoints) ---
@app.get("/api/v1/games")
async def get_games_stream(limit: int = None, offset: int = 0, db: Session = Depends(get_db)):
    """
    Возвращает список игр в виде потокового JSON-ответа (streaming response).
    Это позволяет обрабатывать большие объемы данных с минимальным использованием памяти.
    """
    return StreamingResponse(
        stream_games_from_db(db, limit, offset),
        media_type="application/json"
    )

@app.get("/")
def read_root():
    """
    Корневой маршрут, который предоставляет базовую информацию об API.
    """
    return {"message": "Добро пожаловать в Steam Games API (v2.0 - PostgreSQL Streaming). Используйте /docs для просмотра документации."}
