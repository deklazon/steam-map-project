import os
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import pandas as pd

# --- Настройки ---
# Строка подключения к БД берется из переменной окружения, которую мы зададим в Render
DATABASE_URL = os.getenv("DATABASE_URL")
TABLE_NAME = 'games'

# --- Инициализация приложения и БД ---
app = FastAPI(
    title="Steam Games API",
    description="API для получения данных об играх из Steam (с использованием PostgreSQL).",
    version="1.0.0"
)

# Проверяем, установлена ли переменная окружения
if not DATABASE_URL:
    raise RuntimeError("Переменная окружения DATABASE_URL не установлена!")

# Создаем "движок" SQLAlchemy для подключения к БД
# pool_pre_ping=True - проверяет соединение перед каждым запросом, что полезно для долгоживущих приложений
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Создаем фабрику сессий для управления подключениями к БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Управление сессиями (Dependency Injection) ---
def get_db():
    """
    Эта функция-зависимость создает сессию БД для каждого запроса
    и гарантирует, что она будет закрыта после выполнения запроса.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Маршруты API (Endpoints) ---
@app.get("/api/v1/games")
def get_games(limit: int = None, offset: int = 0, db: Session = Depends(get_db)):
    """
    Возвращает список игр с пагинацией напрямую из базы данных.
    Если limit не указан, возвращает все игры.
    - **limit**: Количество записей для возврата.
    - **offset**: Смещение (количество записей для пропуска).
    """
    try:
        # Формируем безопасный SQL-запрос с параметрами
        # Использование text() и параметров защищает от SQL-инъекций
        if limit:
            query = text(f"SELECT * FROM {TABLE_NAME} LIMIT :limit OFFSET :offset")
            params = {'limit': limit, 'offset': offset}
        else:
            query = text(f"SELECT * FROM {TABLE_NAME} OFFSET :offset")
            params = {'offset': offset}
        
        # Выполняем запрос и передаем параметры
        # pd.read_sql - удобный способ сразу получить результат в виде DataFrame
        df = pd.read_sql(query, db.connection(), params=params)
        
        # Заменяем NaN на None, так как JSON не поддерживает NaN
        df = df.replace({pd.NA: None, float('nan'): None})

        # Конвертируем DataFrame в список словарей (JSON-совместимый формат)
        return df.to_dict(orient='records')
        
    except Exception as e:
        # В случае ошибки возвращаем информативное сообщение
        return {"error": f"Не удалось получить данные из базы данных: {str(e)}"}


@app.get("/")
def read_root():
    """
    Корневой маршрут, который предоставляет базовую информацию об API.
    """
    return {"message": "Добро пожаловать в Steam Games API (v1.0 - PostgreSQL). Используйте /docs для просмотра документации."}
